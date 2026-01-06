# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

**DMX Fire Controller** - A professional DMX-controlled fire effects system that controls 1,700 individually-animated LED candles across two WLED controllers using multicast sACN.

## Architecture

- **Language**: Python 3
- **Hardware**: ENTTEC DMX USB Pro, 2× WLED controllers, 1,700 WS2812B LEDs
- **Protocol**: DMX512 input, sACN (E1.31) output via multicast
- **Performance**: 60 FPS rendering, 3-10ms latency

## Key Files

- `dmx_fire_controller.py` - Main integrated controller
- `config.py` - Centralized configuration (USER EDITABLE)
- `color_finder.py` - RGB color calibration utility
- `find_enttec.py` - ENTTEC device discovery tool
- `test_dmx_input.py` - DMX input testing utility

## Documentation

- `README.md` - Main project documentation
- `QUICKSTART.md` - 5-minute setup guide
- `DUAL_WLED_SETUP.md` - Multi-WLED configuration guide
- `ARCHITECTURE.txt` - Technical architecture details
- `ENTTEC_SETUP_GUIDE.md` - Platform-specific ENTTEC setup

## Current Configuration

### DMX Channel Mapping
- **Channel 1**: Flicker Speed (color transition speed)
- **Channel 2**: Color Shift (Yellow ← → Red)
- **Channel 3**: Sporadic Flicker (wind gust effect)
- **Channel 6**: Master Intensity (global brightness control)
- **Channels 7-19**: Individual bank intensities (13 banks)

### Bank Structure
- **Banks 1-7**: 125 LEDs each (875 total) → WLED ONE
- **Gap**: 145 pixels unused (universe boundary alignment)
- **Banks 8-10**: 125 LEDs each → WLED TWO
- **Banks 11-13**: 150 LEDs each → WLED TWO
- **Total**: 1,700 actual LEDs

### Fire Effect Parameters
- **Base Color**: RGB(255, 127, 15) - custom orange-red
- **Frame Rate**: 60 FPS
- **Special Effects**: White-hot flashes (100-250ms), blue flame flashes
- **Color Control**: Yellow ← → Red shift via Channel 2
- **Wind Effect**: Sporadic brightness drops via Channel 3

## Running the System

```bash
# Run the main controller
python3 dmx_fire_controller.py

# Run with debug output (shows DMX values)
python3 dmx_fire_controller.py --debug

# Show current configuration
python3 dmx_fire_controller.py --config

# Find ENTTEC device
python3 find_enttec.py

# Calibrate colors
python3 color_finder.py
```

## Development Notes

### Making Changes
- **NEVER** hardcode IP addresses - use `config.py`
- Bank sizes are hardcoded in `dmx_fire_controller.py` for alignment
- The 145-pixel gap is intentional for universe boundary alignment
- Multicast is enabled by default (`USE_MULTICAST = True` in config)

### Key Constraints
- Universe boundaries at 170 LEDs (512 channels ÷ 3)
- WLED ONE must end before universe 7 (pixel 1020)
- WLED TWO must start at universe 7 or later
- Frame timing critical - avoid blocking operations

### Platform-Specific Issues
- **macOS**: MUST use `/dev/cu.usbserial-*` not `/dev/tty.usbserial-*`
- **Windows**: Use Device Manager to find COM port
- **Linux**: User must be in `dialout` group

## Testing

```bash
# Test DMX input
python3 test_dmx_input.py

# Test serial port
python3 test_serial_basic.py

# Validate configuration
python3 config.py
```

## Dependencies

```bash
pip3 install pyserial sacn
```

## WSL2 USB Setup (ENTTEC DMX USB Pro)

WSL2 doesn't have native USB access. Use `usbipd-win` to pass the ENTTEC device through.

### One-time Setup (PowerShell as Administrator)
```powershell
# Install usbipd-win
winget install usbipd
```

### Each Session (PowerShell as Administrator)
```powershell
# List USB devices to find ENTTEC (look for "USB Serial Converter" or VID 0403:6001)
usbipd list

# Bind and attach (replace 1-3 with your actual BUSID)
usbipd bind --busid 1-3
usbipd attach --wsl --busid 1-3
```

### Each Session (WSL2)
```bash
# Fix permissions (required after each attach)
sudo chmod 666 /dev/ttyUSB0

# Or add user to dialout group (persistent, requires WSL restart)
sudo usermod -a -G dialout $USER
```

### Verify Connection
```bash
ls -la /dev/ttyUSB*
python3 find_enttec.py
```

**Note:** The device may appear as `/dev/ttyUSB0` or `/dev/ttyUSB1` - update `config.py` accordingly.

## WSL2 Networking Limitation

**Multicast does NOT work in WSL2.** WSL2 uses NAT networking which doesn't forward multicast traffic to the physical network.

**Solution:** Use dual unicast mode instead:
```python
# In config.py
USE_MULTICAST = False
WLED_IP = '192.168.1.2'      # WLED ONE
WLED_IP_TWO = '192.168.1.3'  # WLED TWO
```

The controller will send universes 1-6 to WLED ONE and universes 7-11 to WLED TWO.

## Critical: Single Instance Only

**WARNING:** Only ONE instance of `dmx_fire_controller.py` should run at a time!

Multiple instances will send conflicting sACN data to WLED boxes, causing erratic flickering that appears random and is difficult to diagnose.

Before starting the controller, always check for and kill existing instances:
```bash
# Check for running instances
ps aux | grep dmx_fire_controller | grep -v grep

# Kill all instances
pkill -f dmx_fire_controller.py
```

When using Claude Code to start/stop the controller, background processes may persist even after "killing" them. Always verify with `ps aux` that no instances remain.

## Common Tasks

### Changing Bank Sizes
Edit `dmx_fire_controller.py` around line 502:
```python
bank_sizes = [125] * 7  # WLED ONE banks
bank_sizes += [125] * 3 + [150] * 3  # WLED TWO banks
```

### Adjusting Base Color
Edit the base color in `dmx_fire_controller.py` `_generate_fire_color()` method, or use `color_finder.py` to find new RGB values.

### Switching to Unicast
Edit `config.py`:
```python
USE_MULTICAST = False
WLED_IP = '192.168.4.220'  # Your WLED's IP
```

## Reference Code

The `fire-effects/` directory contains reference implementations and test scripts from earlier development iterations. These are kept for reference but are not part of the main system.
