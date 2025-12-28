# Claude Lights Integration Reference

## Quick Setup

1. **Ensure the claude-lights server is running:**
   ```bash
   cd /Users/cmoredock/DEV/claude-lights/status-lights
   ./start-server.sh
   ```

2. **The hooks are configured in `.claude/settings.local.json`** (see below)

3. **That's it!** Lights will automatically respond to Claude's actions.

## Hook Configuration

The following hooks configuration should be added to `.claude/settings.local.json`:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/Users/cmoredock/DEV/claude-lights/status-lights/send-state.sh thinking",
            "timeout": 2000
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Read",
        "hooks": [
          {
            "type": "command",
            "command": "/Users/cmoredock/DEV/claude-lights/status-lights/send-state.sh reading",
            "timeout": 1000
          }
        ]
      },
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "/Users/cmoredock/DEV/claude-lights/status-lights/send-state.sh writing",
            "timeout": 1000
          }
        ]
      },
      {
        "matcher": "AskUserQuestion",
        "hooks": [
          {
            "type": "command",
            "command": "/Users/cmoredock/DEV/claude-lights/status-lights/send-state.sh awaiting-input",
            "timeout": 1000
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "/Users/cmoredock/DEV/claude-lights/status-lights/send-state.sh awaiting-input",
            "timeout": 1000
          }
        ]
      },
      {
        "matcher": "WebFetch|WebSearch",
        "hooks": [
          {
            "type": "command",
            "command": "/Users/cmoredock/DEV/claude-lights/status-lights/send-state.sh awaiting-input",
            "timeout": 1000
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "/Users/cmoredock/DEV/claude-lights/status-lights/send-state.sh success",
            "timeout": 1000
          }
        ]
      },
      {
        "matcher": "^(?!AskUserQuestion|WebFetch|WebSearch|Bash).*",
        "hooks": [
          {
            "type": "command",
            "command": "/Users/cmoredock/DEV/claude-lights/status-lights/send-state.sh idle",
            "timeout": 1000
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/Users/cmoredock/DEV/claude-lights/status-lights/send-state.sh idle",
            "timeout": 2000
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/Users/cmoredock/DEV/claude-lights/status-lights/send-state.sh idle",
            "timeout": 2000
          }
        ]
      }
    ],
    "SubagentStop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/Users/cmoredock/DEV/claude-lights/status-lights/send-state.sh awaiting-input",
            "timeout": 2000
          }
        ]
      }
    ],
    "Notification": [
      {
        "matcher": "permission_prompt",
        "hooks": [
          {
            "type": "command",
            "command": "/Users/cmoredock/DEV/claude-lights/status-lights/send-state.sh awaiting-input",
            "timeout": 2000
          }
        ]
      }
    ]
  }
}
```

## Light States

| Event | State | Light Effect |
|-------|-------|--------------|
| You submit a message | `thinking` | Pulsing blue |
| Claude reads files | `reading` | Soft cyan |
| Claude edits/writes files | `writing` | Solid green |
| Edit/write completes | `success` | Bright green (brief) |
| Claude waits for input/permission | `awaiting-input` | Pulsing red |
| Session starts/ends | `idle` | Dim warm white |

## Testing

```bash
# Check if server is running
cd /Users/cmoredock/DEV/claude-lights/status-lights
./status.sh

# Test manually
./send-state.sh thinking
./send-state.sh reading
./send-state.sh awaiting-input
```

## Merging Hooks with Existing Settings

If you already have settings in `.claude/settings.local.json`, merge the `hooks` section with your existing configuration. The hooks section should be a top-level key alongside other settings like `permissions` and `enableAllProjectMcpServers`.
