# DMX Fire Controller - 1,700 Candle System

Professional DMX-controlled fire effects for dual WLED LED strips. Control 1,700 individually-animated candle flames across 13 banks from any DMX lighting console.

## Overview

This system bridges professional DMX lighting control with dual WLED LED controllers via multicast sACN, creating realistic candle fire effects with advanced color and intensity control.

**Signal Flow:**
```
DMX Console → ENTTEC DMX USB Pro → Fire Controller → sACN Multicast → 2× WLED → 1,700 LEDs
```

## Features

- 🔥 **1,700 Individual Flames** - Each LED is independently animated at 60 FPS
- 🎚️ **13 Independent Banks** - Channels 7-19 for precise zone control
- 🎛️ **Master Intensity** - Channel 6 controls all banks simultaneously
- 🎨 **Custom Base Color** - RGB(255, 127, 15) warm orange-red
- 🌪️ **Wind Gust Effect** - Sporadic flickering simulates air movement
- 📊 **Advanced Color Control** - Yellow ← → Red shift with flicker speed
- ⚡ **Ultra-Low Latency** - 3-10ms from console to LEDs
- 🔌 **Multicast sACN** - Dual WLED boxes from single stream

## Hardware Requirements

- **ENTTEC DMX USB Pro** - DMX512 interface
- **2× WLED Controllers** - ESP32/ESP8266 running WLED firmware
- **LED Strips** - WS2812B or compatible:
  - WLED ONE: 875 LEDs (7 banks × 125)
  - WLED TWO: 825 LEDs (3 banks × 125 + 3 banks × 150)
- **DMX Console** - Any DMX512 lighting console
- **Computer** - macOS, Windows, or Linux (Python 3.9+)

## Quick Start

### 1. Install Dependencies

```bash
pip3 install pyserial sacn
```

### 2. Find Your ENTTEC Device

```bash
python3 find_enttec.py
```

### 3. Configure Settings

Edit `config.py`:
```python
# ENTTEC Serial Port (from find_enttec.py)
# macOS: '/dev/cu.usbserial-XXXXXXXX'  (MUST use cu not tty!)
# Windows: 'COM3'
# Linux: '/dev/ttyUSB0'
DMX_SERIAL_PORT = '/dev/cu.usbserial-EN437698'

# Network Mode
USE_MULTICAST = True  # True for dual-WLED setup

# WLED Settings (multicast mode)
WLED_UNIVERSE_START = 1

# LED Configuration
TOTAL_PIXELS = 1845  # Includes 145-pixel gap for universe alignment
```

### 4. Configure WLED Boxes

See [DUAL_WLED_SETUP.md](DUAL_WLED_SETUP.md) for complete multicast configuration.

**Quick Settings:**

**WLED ONE:**
- LED Count: `875`
- Start Universe: `1`
- Enable Multicast: ✓

**WLED TWO:**
- LED Count: `825`
- Start Universe: `7`
- Enable Multicast: ✓

### 5. Test Your Setup

```bash
# Test DMX input
python3 test_dmx_input.py

# Calibrate base color (optional)
python3 color_finder.py
```

### 6. Run the Fire Controller

```bash
# Normal mode
python3 dmx_fire_controller.py

# Debug mode (shows DMX values)
python3 dmx_fire_controller.py --debug

# Show configuration
python3 dmx_fire_controller.py --config
```

## DMX Channel Mapping

### Control Channels (Global)
| Channel | Function | Range | Description |
|---------|----------|-------|-------------|
| 1 | Flicker Speed | 0-255 | Color transition speed (0=slow, 255=fast) |
| 2 | Color Shift | 0-255 | Yellow ← → Red (0=yellow, 127=base, 255=red) |
| 3 | Wind Gust | 0-255 | Sporadic flicker intensity (0=calm, 255=windy) |
| 6 | Master Intensity | 0-255 | Global brightness for all 13 banks |

### Bank Channels (Individual)
| Channel | Bank | LEDs | WLED Box | Pixel Range |
|---------|------|------|----------|-------------|
| 7 | 1 | 125 | ONE | 0-124 |
| 8 | 2 | 125 | ONE | 125-249 |
| 9 | 3 | 125 | ONE | 250-374 |
| 10 | 4 | 125 | ONE | 375-499 |
| 11 | 5 | 125 | ONE | 500-624 |
| 12 | 6 | 125 | ONE | 625-749 |
| 13 | 7 | 125 | ONE | 750-874 |
| 14 | 8 | 125 | TWO | 1020-1144 |
| 15 | 9 | 125 | TWO | 1145-1269 |
| 16 | 10 | 125 | TWO | 1270-1394 |
| 17 | 11 | 150 | TWO | 1395-1544 |
| 18 | 12 | 150 | TWO | 1545-1694 |
| 19 | 13 | 150 | TWO | 1695-1844 |

**Note:** Pixels 875-1019 are unused (145-pixel gap for universe alignment).

### Recommended Starting Values
- **Master (Ch 6):** 255 (full)
- **All Banks (Ch 7-19):** 255 (full)
- **Flicker Speed (Ch 1):** 127 (medium)
- **Color Shift (Ch 2):** 127 (base orange-red)
- **Wind Gust (Ch 3):** 50 (gentle)

## Fire Effect Details

### Base Color
- **RGB(255, 127, 15)** - Warm orange-red candle color
- Use `color_finder.py` to calibrate on actual hardware

### Color Variation
- Each pixel randomly varies around the base color
- **Green component** shifts based on Channel 2:
  - Low values (0-100): Yellower flames
  - Medium (100-150): Base orange-red
  - High values (150-255): Redder flames

### Special Effects
- **White-hot flashes:** 1% chance, 100-250ms duration
- **Blue flame flashes:** 0.33% chance, 100-250ms duration
- **Wind gusts:** Random intensity drops controlled by Channel 3

### Animation
- **60 FPS rendering** for smooth transitions
- **Independent RNG** per pixel for natural variation
- **Smooth color transitions** with easing curves
- **Waxing/waning intensity** using sine waves

## Platform-Specific Notes

### macOS ⚠️ CRITICAL
MUST use `/dev/cu.usbserial-*` NOT `/dev/tty.usbserial-*`

Using `tty` instead of `cu` will cause the program to hang!

```bash
# Correct
DMX_SERIAL_PORT = '/dev/cu.usbserial-EN437698'

# WRONG - will hang!
DMX_SERIAL_PORT = '/dev/tty.usbserial-EN437698'
```

### Windows
- Find COM port in Device Manager → Ports (COM & LPT)
- Example: `DMX_SERIAL_PORT = 'COM3'`

### Linux
- User must be in `dialout` group:
  ```bash
  sudo usermod -a -G dialout $USER
  # Log out and back in
  ```
- Find device: `ls -la /dev/ttyUSB*`
- Example: `DMX_SERIAL_PORT = '/dev/ttyUSB0'`

## Performance

- **Frame Rate:** 50-60 FPS sustained
- **DMX Rate:** 200-250 packets/second (typical)
- **Latency:** 3-10ms (typical), up to 80ms (acceptable)
- **CPU Usage:** ~20% single core
- **LED Updates:** 102,000 updates/second (1,700 × 60 FPS)

## Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - 5-minute setup guide
- **[DUAL_WLED_SETUP.md](DUAL_WLED_SETUP.md)** - Complete dual-WLED configuration
- **[ARCHITECTURE.txt](ARCHITECTURE.txt)** - Technical architecture details
- **[ENTTEC_SETUP_GUIDE.md](ENTTEC_SETUP_GUIDE.md)** - Platform-specific troubleshooting

## Utilities

### Color Finder
Find the perfect base color for your candles:
```bash
python3 color_finder.py
```
Channels 1-3 directly control RGB. Note the values you like and update `dmx_fire_controller.py`.

### ENTTEC Finder
Discover and test your ENTTEC device:
```bash
python3 find_enttec.py
```

### DMX Input Tester
Verify DMX input is working:
```bash
python3 test_dmx_input.py
```

## Troubleshooting

### No DMX input
- Run `find_enttec.py` to locate device
- Check serial port setting in `config.py`
- macOS: Verify using `/dev/cu.*` not `/dev/tty.*`
- Linux: Check `dialout` group membership

### Only some banks work
- Verify WLED universe settings:
  - WLED ONE: Start Universe **1**
  - WLED TWO: Start Universe **7** (not 6!)
- Check multicast is enabled on both WLED boxes
- Ensure both boxes are on same network/subnet

### No output to LEDs
- Verify WLED IP address (if unicast mode)
- Check multicast is enabled (if multicast mode)
- Test WLED with built-in effects
- Verify network connectivity

### Poor performance
- Reduce pixel count or use every other pixel
- Check CPU usage - close other applications
- Verify network isn't saturated
- Use wired Ethernet instead of Wi-Fi

## License

This project is provided as-is for personal and commercial use.

## Credits

Built with:
- [pyserial](https://github.com/pyserial/pyserial) - Serial port communication
- [sacn](https://github.com/Hundman/sacn) - sACN protocol implementation
- [WLED](https://github.com/Aircoookie/WLED) - LED control firmware
