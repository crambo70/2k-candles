# 1,500 Candles - DMX Fire Effect Controller

Professional DMX-controlled fire effects for WLED LED strips. Control 1,500 individually-animated candle flames from any DMX lighting console.

![System Architecture](docs/architecture-overview.png)

## Overview

This system bridges professional DMX lighting control with WLED LED controllers, creating realistic candle fire effects with advanced color and intensity control.

**Signal Flow:**
```
DMX Console → ENTTEC DMX USB Pro → Computer (Fire Controller) → sACN Network → WLED → LEDs
```

## Features

- 🔥 **1,500 Individual Flames** - Each LED is independently animated
- 🎚️ **DMX Control** - Standard lighting console interface
- 🎨 **Advanced Color Control** - Yellow to red gradient, blue component, flicker speed
- ⚡ **Low Latency** - 3-10ms typical latency from console to LEDs
- 📊 **60 FPS Rendering** - Smooth, realistic fire animation
- 🎭 **3 Flame Banks** - Independent intensity control for different zones

## Hardware Requirements

- **ENTTEC DMX USB Pro** - DMX512 interface
- **WLED Controller** - ESP32/ESP8266 running WLED firmware
- **LED Strip** - WS2812B or compatible (1,500 pixels)
- **DMX Console** - Any DMX512 lighting console
- **Computer** - macOS, Windows, or Linux (Python 3.9+)

## Quick Start

### 1. Install Dependencies

```bash
pip3 install pyserial sacn
```

### 2. Configure Settings

Edit `config.py`:
```python
# ENTTEC Serial Port
# macOS: '/dev/cu.usbserial-EN437698'
# Windows: 'COM3'
# Linux: '/dev/ttyUSB0'
DMX_SERIAL_PORT = '/dev/cu.usbserial-EN437698'

# WLED Network Settings
WLED_IP = '192.168.4.74'
WLED_UNIVERSE_START = 1

# LED Configuration
TOTAL_PIXELS = 1500
PIXEL_SPACING = 1  # Every pixel gets fire (1500 flames)
```

### 3. Test ENTTEC Connection

```bash
python3 test_dmx_input.py
```

Move faders on your DMX console - you should see values changing in real-time.

### 4. Run the Fire Controller

```bash
# Normal mode
python3 dmx_fire_controller.py

# Debug mode (shows DMX values)
python3 dmx_fire_controller.py --debug
```

### 5. Configure Your DMX Console

Set up 6 channels on Universe 1:

| Channel | Function | Range | Description |
|---------|----------|-------|-------------|
| 1 | Bank 1 Intensity | 0-255 | Pixels 0-499 |
| 2 | Bank 2 Intensity | 0-255 | Pixels 500-999 |
| 3 | Bank 3 Intensity | 0-255 | Pixels 1000-1499 |
| 4 | Flicker Speed | 0-255 | 0=slow, 127=normal, 255=fast |
| 5 | Color Shift | 0-255 | 0=yellow, 255=deep red |
| 6 | Blue Component | 0-255 | 0=none, 255=white-hot |

**Recommended Starting Values:**
- Channels 1-3: 255 (all banks full)
- Channel 4: 127 (medium flicker)
- Channel 5: 0 (yellow flames)
- Channel 6: 0 (no blue)

## Platform-Specific Setup

### macOS ⚠️ CRITICAL

**ALWAYS use `/dev/cu.usbserial-*` NOT `/dev/tty.usbserial-*`**

Using `tty` instead of `cu` will cause the application to hang indefinitely!

Find your device:
```bash
ls -la /dev/cu.usbserial-*
```

### Windows

1. Open Device Manager (Win + X → Device Manager)
2. Expand "Ports (COM & LPT)"
3. Find "ENTTEC DMX USB PRO" and note the COM number
4. Use `COM3`, `COM4`, etc. in config

### Linux

Find your device:
```bash
ls -la /dev/ttyUSB*
```

Add yourself to the dialout group:
```bash
sudo usermod -a -G dialout $USER
```
Log out and back in for changes to take effect.

## WLED Configuration

Your WLED device must be configured for sACN (E1.31) input:

1. Open WLED web interface (http://[WLED-IP])
2. Go to **Settings → Sync Interfaces**
3. Enable **E1.31 (sACN)**
4. Set **Start Universe** to `1`
5. Disable **Multicast** (use Unicast mode)
6. Set **DMX Start Address** to `1` (if using DMX mode)
7. Save settings

## System Architecture

### Fire Effect Algorithm

Each pixel uses `SmoothFirePixel` with:
- **Smooth color transitions** - Interpolated between flame colors
- **Waxing/waning intensity** - Sine wave brightness modulation
- **Algorithmic colors** - Based on real candle physics
- **Rare special colors** - White-hot and blue flame flashes (1% chance)

### Color Generation

**Base Palette:**
- Red: Always high (90-100%)
- Green: Normal distribution (30-80%) - determines yellow vs red-orange
- Blue: Random base (30-100), scaled by blue control channel

**DMX Control Modifiers:**
- **Channel 4 (Flicker):** Modulates transition speed (0.5x to 2x)
- **Channel 5 (Color Shift):** Reduces green component (yellow → red)
- **Channel 6 (Blue):** Adds blue for white-hot appearance

### Performance Optimizations

- **Buffer draining:** Reads up to 10 DMX packets per frame
- **Hysteresis filtering:** Ignores changes < 2% (reduces noise)
- **Smooth interpolation:** 30% ramp per frame
- **Pre-allocated buffers:** No memory allocation in render loop
- **Single-threaded:** No context switching overhead

**Typical Performance:**
- FPS: 50-60 sustained
- DMX Rate: 200-400 packets/second
- Latency: 3-10ms (normal), up to 80ms (acceptable)
- CPU Usage: 18-20% single core

### Network Protocol

**sACN (E1.31) Output:**
- 9 universes for 1,500 RGB LEDs (170 LEDs per universe)
- Unicast transmission (not multicast)
- Universe 1-9 (starting at configured universe)
- Port 5568 (standard sACN port)

## Troubleshooting

### Application Hangs on Startup (macOS)

**Cause:** Using `/dev/tty.*` instead of `/dev/cu.*`

**Solution:**
1. Kill process: `pkill -9 python3`
2. Update config to use `/dev/cu.usbserial-*`
3. Restart application

### "Multiple access on port" Error

**Cause:** Another process is using the serial port

**Solution:**
```bash
# Find processes using the port
lsof /dev/cu.usbserial-EN437698

# Kill competing processes
kill -9 <PID>
```

### No DMX Data Received

**Checklist:**
- [ ] DMX console is powered on and outputting
- [ ] XLR cable connected (DMX Out → ENTTEC In)
- [ ] Console faders are raised (values > 0)
- [ ] Correct DMX universe selected on console
- [ ] Cable is DMX-rated (not audio XLR)

**Test:** Run `python3 test_dmx_input.py` and move faders

### LEDs Not Responding

**Checklist:**
- [ ] WLED is powered on and reachable (ping test)
- [ ] sACN is enabled in WLED settings
- [ ] WLED universe matches controller output universe
- [ ] Network connection is working
- [ ] DMX channels 1-3 have values > 0

**Test WLED connection:**
```bash
ping 192.168.4.74
curl http://192.168.4.74/json/info
```

### See Full Troubleshooting Guide

For complete troubleshooting, platform-specific issues, and ENTTEC protocol details:
- **[ENTTEC Setup & Troubleshooting Guide](ENTTEC_SETUP_GUIDE.md)**

## Project Files

### Main Files
- **`dmx_fire_controller.py`** - Main integrated controller (USE THIS)
- **`config.py`** - Configuration settings
- **`test_dmx_input.py`** - DMX input testing utility

### Documentation
- **`README.md`** - This file (getting started)
- **`ENTTEC_SETUP_GUIDE.md`** - ENTTEC troubleshooting & platform guides
- **`ARCHITECTURE.txt`** - Detailed technical architecture
- **`README_DMX_FIRE.md`** - Original DMX fire controller notes

### Reference Implementations (fire-effects/)
- `fire_flicker.py` - Simple single-pixel fire
- `fire_multi.py` - Multi-pixel independent animation
- `fire_smooth.py` - Smooth transitions reference
- `show_control.py` - sACN-based show control (original)
- `test_1024.py` - WLED test script

## Color Palette Examples

### Classic Candle
- Ch 5 (Color Shift): 0 (yellow)
- Ch 6 (Blue): 0 (no blue)
- **Result:** Pure yellow-orange flame

### White-Hot Flame
- Ch 5 (Color Shift): 0 (yellow)
- Ch 6 (Blue): 255 (maximum)
- **Result:** Bright white with yellow tint (gas flame)

### Deep Red Ember
- Ch 5 (Color Shift): 255 (red)
- Ch 6 (Blue): 0 (no blue)
- **Result:** Deep red-orange (smoldering coals)

### Intense White Fire
- Ch 5 (Color Shift): 0 (yellow)
- Ch 6 (Blue): 127 (moderate)
- Ch 4 (Flicker): 255 (fast)
- **Result:** Energetic white-yellow flame

## Performance Monitoring

The controller displays real-time status every 5 seconds:

```
🔥  52.3 FPS | DMX:245.2 pkt/s | Latency:  5.8ms | B1:100% B2: 99% B3:100% | Flicker:100% | Y→R: 29% | Blue: 21%
```

**Status Indicators:**
- **FPS:** Rendering frame rate (target: 60)
- **DMX:** Incoming DMX packet rate
- **Latency:** Time since last DMX packet (lower is better)
- **B1-B3:** Active flame banks with intensity
- **Flicker:** Flicker speed control value
- **Y→R:** Yellow to red color shift value
- **Blue:** Blue component value

## Development

### Running Tests
```bash
# Serial port basic test
python3 test_serial_noflow.py

# DMX input test (shows real-time values)
python3 test_dmx_input.py

# Full system test with debug output
python3 dmx_fire_controller.py --debug
```

### Adding New Effects

Extend the `SmoothFirePixel` class in `dmx_fire_controller.py`:

```python
class SmoothFirePixel:
    def _generate_fire_color(self) -> tuple:
        # Your custom color generation logic
        return (red, green, blue)

    def update(self, current_time: float) -> tuple:
        # Your custom animation logic
        return (r, g, b)
```

## Credits

- **Fire Algorithm:** Based on real candle physics
- **DMX Interface:** ENTTEC DMX USB Pro
- **LED Control:** WLED firmware
- **Protocol:** sACN (E1.31) streaming

## License

This project is provided as-is for educational and production use.

## Support

For issues and questions:
1. Check **[ENTTEC_SETUP_GUIDE.md](ENTTEC_SETUP_GUIDE.md)** for platform-specific help
2. Review **ARCHITECTURE.txt** for technical details
3. Run test scripts to isolate problems
4. Check GitHub issues

---

**Last Updated:** 2025-12-19
**Tested On:** macOS (Sonoma), Windows 10/11, Ubuntu 22.04
**Python:** 3.9+
