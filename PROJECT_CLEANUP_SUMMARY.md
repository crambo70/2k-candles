# Project Cleanup Summary - December 19, 2025

## Overview

Comprehensive cleanup and documentation of the 1,500 Candles DMX Fire Controller project, with focus on cross-platform compatibility and critical ENTTEC USB Pro setup issues.

## Critical Issues Resolved

### 1. macOS Serial Port Hanging Issue ⚠️ CRITICAL

**Problem:** Application would hang indefinitely when opening serial port on macOS.

**Root Cause:** Using `/dev/tty.usbserial-*` instead of `/dev/cu.usbserial-*`

**Impact:** Made the application completely unusable on macOS until process was force-killed.

**Solution:**
- Updated all scripts to use `/dev/cu.usbserial-EN437698`
- Added validation in `config.py` to detect and warn about this issue
- Documented extensively in all setup guides

**Why this happens:**
- `/dev/tty.*` devices are "dial-in" devices that wait for carrier detect (DCD signal)
- `/dev/cu.*` devices are "call-out" devices for outgoing connections
- ENTTEC DMX USB Pro doesn't assert DCD, so tty devices wait forever
- This is a macOS-specific behavior that doesn't exist on Windows/Linux

### 2. Serial Port Conflicts

**Problem:** "Device disconnected or multiple access on port" errors causing crashes.

**Root Cause:** Multiple Python processes (including background test scripts) competing for the same serial port.

**Solution:**
- Added try-except handling for SerialException in poll() method
- Created diagnostic utilities to detect port conflicts
- Documented how to find and kill competing processes

### 3. Incorrect WLED IP Address

**Problem:** sACN output going to wrong IP address (192.168.4.189 instead of 192.168.4.74).

**Root Cause:** Hardcoded IP addresses throughout codebase.

**Solution:**
- Created centralized `config.py` configuration file
- Updated all scripts to use config values
- Added IP validation to detect invalid addresses

## New Files Created

### 1. **README.md** - Comprehensive Getting Started Guide
- Platform-specific setup instructions (macOS, Windows, Linux)
- Hardware requirements
- Quick start procedure
- DMX channel mapping
- Troubleshooting section
- Color palette examples
- Performance monitoring guide

### 2. **ENTTEC_SETUP_GUIDE.md** - Platform-Specific Troubleshooting
- Critical macOS cu vs tty explanation
- Windows COM port setup
- Linux permissions and dialout group
- Common issues and solutions
- ENTTEC protocol basics
- Best practices for serial communication
- Performance considerations
- Testing procedures

### 3. **QUICKSTART.md** - 5-Minute Setup Guide
- Step-by-step instructions for first-time users
- Minimal steps to get running quickly
- Troubleshooting for common issues
- Command reference

### 4. **config.py** - Centralized Configuration
- Platform-specific serial port settings
- WLED network configuration
- LED strip parameters
- Performance tuning options
- Auto-detection helpers
- Configuration validation
- `suggest_serial_port()` - Auto-detects correct port for platform
- `validate_config()` - Checks for common configuration errors
- `print_config()` - Displays current settings

### 5. **find_enttec.py** - Cross-Platform Device Finder
- Automatically finds ENTTEC devices on macOS, Windows, Linux
- Tests serial ports for accessibility
- Recommends correct port to use
- Platform-specific guidance
- Detects macOS tty vs cu issue
- Shows device descriptions on Windows

### 6. **PROJECT_CLEANUP_SUMMARY.md** - This Document
- Documents all changes made
- Explains critical issues resolved
- Provides upgrade guide

## Updated Files

### 1. **dmx_fire_controller.py** - Main Controller
- Added `import config` for centralized configuration
- Added configuration validation on startup
- Added `--config` flag to show configuration
- Improved error handling for serial port issues
- Updated to use config values instead of hardcoded settings

**New Features:**
```bash
python3 dmx_fire_controller.py --config  # Show configuration
python3 dmx_fire_controller.py --debug   # Show DMX values
```

### 2. **test_dmx_input.py** - DMX Testing Utility
- Added config import
- Falls back to defaults if config not found
- Shows serial port being tested

### 3. **ARCHITECTURE.txt** - Technical Documentation
- Added "PLATFORM-SPECIFIC CONFIGURATION" section
- Documented macOS cu vs tty issue
- Added Windows and Linux serial port formats
- Included common issues and solutions
- Updated all IP addresses to 192.168.4.74

### 4. **All fire-effects/ Scripts**
- Updated WLED IP from 192.168.4.189 to 192.168.4.74
- Files updated:
  - `test_1024.py`
  - `fire_flicker.py`
  - `fire_smooth.py`
  - `fire_multi.py`
  - `show_control.py`

### 5. **README_DMX_FIRE.md**
- Updated WLED IP address
- Added references to new documentation

## Platform Compatibility Matrix

| Platform | Serial Port Format | Example | Tested |
|----------|-------------------|---------|--------|
| macOS | `/dev/cu.usbserial-*` | `/dev/cu.usbserial-EN437698` | ✅ Yes |
| Windows | `COMx` | `COM3` | 📋 Documented |
| Linux | `/dev/ttyUSB*` | `/dev/ttyUSB0` | 📋 Documented |

## Configuration Migration Guide

### Before (Hardcoded)
```python
# In dmx_fire_controller.py
controller = DMXFireController(
    dmx_serial_port='/dev/cu.usbserial-EN437698',
    output_ip='192.168.4.74',
    total_pixels=1500,
    # ...
)
```

### After (Config File)
```python
# In config.py
DMX_SERIAL_PORT = '/dev/cu.usbserial-EN437698'
WLED_IP = '192.168.4.74'
TOTAL_PIXELS = 1500

# In dmx_fire_controller.py
import config

controller = DMXFireController(
    dmx_serial_port=config.DMX_SERIAL_PORT,
    output_ip=config.WLED_IP,
    total_pixels=config.TOTAL_PIXELS,
    # ...
)
```

**Benefits:**
- Single place to update settings
- Validation on startup
- Platform-specific defaults
- Auto-detection helpers

## Key Learnings Documented

### 1. ENTTEC USB Pro on macOS
- **MUST** use `/dev/cu.*` not `/dev/tty.*`
- Using wrong device causes indefinite hang
- No error message - just hangs on `serial.Serial()` call
- This is macOS-specific behavior

### 2. Serial Port Conflicts
- Only one process can access serial port at a time
- Use `lsof` to find competing processes
- Add error handling for SerialException
- Physical reset (unplug/replug) often resolves issues

### 3. ENTTEC Protocol
- Label 8 enables "always-send" mode
- Label 5 contains received DMX packets
- Buffer can hold multiple packets - drain for low latency
- Status byte indicates errors (overrun, queue overflow)

### 4. Cross-Platform Serial Port Detection
- macOS: glob `/dev/cu.usbserial-*`
- Windows: Use `serial.tools.list_ports`
- Linux: glob `/dev/ttyUSB*`
- Always validate port exists before opening

## Testing Recommendations

### 1. Find Device
```bash
python3 find_enttec.py
```
Should show working serial ports.

### 2. Validate Configuration
```bash
python3 config.py
```
Should show no configuration issues.

### 3. Test DMX Input
```bash
python3 test_dmx_input.py
```
Move faders - values should change.

### 4. Run Controller
```bash
python3 dmx_fire_controller.py --debug
```
Should show DMX values and sACN output.

## File Organization

```
1.5k-candles/
├── README.md                     # Main getting started guide
├── QUICKSTART.md                 # 5-minute setup
├── ENTTEC_SETUP_GUIDE.md        # Platform-specific troubleshooting
├── ARCHITECTURE.txt              # Technical architecture
├── PROJECT_CLEANUP_SUMMARY.md   # This file
├── README_DMX_FIRE.md           # Original notes
├── CLAUDE.md                     # Claude Code instructions
├── CLAUDE_LIGHTS_REFERENCE.md   # Claude Lights reference
│
├── config.py                     # ⭐ Configuration (edit this)
├── dmx_fire_controller.py       # ⭐ Main controller (run this)
├── test_dmx_input.py            # DMX input tester
├── find_enttec.py               # Device finder utility
├── test_serial_basic.py         # Basic serial test
├── test_serial_noflow.py        # Serial test w/o flow control
│
└── fire-effects/                 # Reference implementations
    ├── fire_flicker.py
    ├── fire_smooth.py
    ├── fire_multi.py
    ├── show_control.py
    └── test_1024.py
```

**⭐ Files to use:**
- **config.py** - Edit your settings here
- **dmx_fire_controller.py** - Run this for production
- **find_enttec.py** - Run first to find your device

## Next Steps for Users

1. **Run device finder:**
   ```bash
   python3 find_enttec.py
   ```

2. **Edit config.py** with your settings:
   - Update `DMX_SERIAL_PORT` from finder
   - Update `WLED_IP` to your WLED device

3. **Validate configuration:**
   ```bash
   python3 config.py
   ```

4. **Test DMX input:**
   ```bash
   python3 test_dmx_input.py
   ```

5. **Run fire controller:**
   ```bash
   python3 dmx_fire_controller.py
   ```

## Documentation Quality

All documentation now includes:
- ✅ Platform-specific instructions (macOS, Windows, Linux)
- ✅ Common issues and solutions
- ✅ Step-by-step procedures
- ✅ Command examples
- ✅ Expected output examples
- ✅ Troubleshooting guides
- ✅ Quick reference sections

## Future Improvements

Potential enhancements for future development:
- [ ] Windows installer/executable
- [ ] GUI configuration tool
- [ ] WLED auto-discovery
- [ ] Multiple WLED output support
- [ ] DMX universe auto-detection
- [ ] Web-based monitoring dashboard
- [ ] Preset save/recall system

## Success Criteria

✅ **All critical issues resolved:**
- macOS serial port hanging
- Serial port conflicts
- Incorrect WLED IP
- Cross-platform compatibility

✅ **Complete documentation:**
- Getting started guide
- Platform-specific setup
- Troubleshooting guide
- Quick start guide

✅ **Developer-friendly:**
- Centralized configuration
- Auto-detection utilities
- Validation and error checking
- Clear file organization

✅ **Production-ready:**
- Error handling
- Configuration validation
- Platform detection
- Diagnostic tools

---

**Cleanup completed:** December 19, 2025
**Platform tested:** macOS (Sonoma)
**Status:** Production ready ✅
