# Project Current State

**Last Updated:** January 2026
**Status:** Production Ready

## Summary

Professional DMX fire controller for 1,700 individually-animated LED candles across 13 banks, split between two WLED controllers using multicast sACN.

## System Configuration

### Hardware
- **Total LEDs**: 1,700 (875 + 825)
- **WLED Controllers**: 2 (multicast sACN)
- **DMX Interface**: ENTTEC DMX USB Pro
- **LED Type**: WS2812B RGB

### Banks
- **Banks 1-7**: 125 LEDs each → WLED ONE (875 total)
- **Banks 8-10**: 125 LEDs each → WLED TWO
- **Banks 11-13**: 150 LEDs each → WLED TWO (825 total)
- **Gap**: 145 pixels (875-1019) unused for universe alignment

### DMX Channel Mapping
- **Ch 1**: Flicker Speed (0=slow, 255=fast)
- **Ch 2**: Color Shift Yellow ← → Red (0=yellow, 127=base, 255=red)
- **Ch 3**: Wind Gust Effect (0=calm, 255=stormy)
- **Ch 6**: Master Intensity (global brightness)
- **Ch 7-19**: Individual bank intensities (13 banks)

### Network Configuration
- **Mode**: Multicast sACN
- **WLED ONE**: Universes 1-6, Start Universe 1, 875 LEDs
- **WLED TWO**: Universes 7-11, Start Universe 7, 825 LEDs
- **Protocol**: E1.31 (sACN) multicast

### Fire Effect
- **Base Color**: RGB(255, 127, 15) - warm orange-red
- **Frame Rate**: 60 FPS
- **Special Effects**:
  - White-hot flashes (1%, 100-250ms)
  - Blue flame flashes (0.33%, 100-250ms)
  - Wind gusts (controlled by Ch 3)

## Recent Major Changes

### Channel Reorganization
- Moved control channels from 4-6 to 1-3
- Added Master Intensity on Channel 6
- Expanded from 3 banks to 13 banks (Ch 7-19)

### Dual WLED with Multicast
- Added multicast sACN support
- Split banks across two WLED boxes
- Implemented 145-pixel gap for universe alignment
- WLED TWO starts at universe 7 (pixel 1020)

### Color System Updates
- Custom base color: RGB(255, 127, 15)
- Removed blue component control (was Ch 6)
- Added wind gust/sporadic flicker effect (Ch 3)
- Shortened white flashes to 100-250ms

### Performance
- 102,000 LED updates/second (1,700 × 60 FPS)
- 3-10ms latency (typical)
- 50-60 FPS sustained
- ~20% CPU usage

## File Structure

### Main Application
- `dmx_fire_controller.py` - Main controller (production)
- `config.py` - User configuration
- `color_finder.py` - RGB calibration utility

### Utilities
- `find_enttec.py` - ENTTEC device discovery
- `test_dmx_input.py` - DMX input testing
- `test_serial_*.py` - Serial port diagnostics

### Documentation
- `README.md` - Main documentation (UPDATED)
- `CLAUDE.md` - Development guide (UPDATED)
- `ARCHITECTURE.txt` - Technical details (UPDATED)
- `DUAL_WLED_SETUP.md` - Multi-WLED guide (UPDATED)
- `QUICKSTART.md` - Quick setup guide
- `ENTTEC_SETUP_GUIDE.md` - Platform-specific setup

### Reference Code
- `fire-effects/` - Earlier development iterations (reference only)

## Configuration Files

### config.py Settings
```python
# Serial Port (platform-specific)
DMX_SERIAL_PORT = '/dev/cu.usbserial-EN437698'  # macOS: /dev/cu.*, NOT /dev/tty.*

# Network Mode
USE_MULTICAST = True  # Multicast for dual-WLED setup

# LED Configuration
TOTAL_PIXELS = 1845  # Includes 145-pixel gap
PIXEL_SPACING = 1    # Every pixel has fire effect

# sACN Settings
WLED_UNIVERSE_START = 1
SACN_PORT = 5568
```

## WLED Box Settings

### WLED ONE
- **LED Count**: 875
- **Start Universe**: 1
- **Universe Count**: 6
- **Multicast**: Enabled
- **Covers**: Banks 1-7

### WLED TWO
- **LED Count**: 825
- **Start Universe**: 7
- **Universe Count**: 5
- **Multicast**: Enabled
- **Covers**: Banks 8-13

## Known Issues & Solutions

### Universe Boundary Alignment
- **Issue**: Banks can't span universe boundaries
- **Solution**: 145-pixel gap between WLED boxes
- **Critical**: WLED TWO MUST start at universe 7

### macOS Serial Port
- **Issue**: Using /dev/tty.* causes hang
- **Solution**: MUST use /dev/cu.* instead
- **Status**: Documented in all guides

### Bank 7 Split
- **Issue**: Bank 7 (pixels 750-874) spans universe boundary
- **Solution**: All of Bank 7 goes to WLED ONE (ends at pixel 874)
- **Status**: Resolved

## Performance Metrics

- **Frame Rate**: 50-60 FPS (60 FPS target)
- **DMX Packet Rate**: 200-250 packets/second
- **Latency**: 3-10ms typical, up to 80ms acceptable
- **CPU Usage**: ~20% single core
- **Network Traffic**: 660 sACN packets/second (11 universes × 60 FPS)

## Testing Status

- ✅ DMX Input: Working
- ✅ Fire Effects: Working (all 1,700 LEDs)
- ✅ Multicast sACN: Working
- ✅ Dual WLED: Working
- ✅ Master Intensity: Working
- ✅ Wind Gust Effect: Working
- ✅ Color Calibration: Working (RGB 255, 127, 15)
- ✅ Cross-platform: macOS tested

## Dependencies

```bash
pip3 install pyserial sacn
```

## Quick Commands

```bash
# Run controller
python3 dmx_fire_controller.py

# Debug mode
python3 dmx_fire_controller.py --debug

# Find ENTTEC device
python3 find_enttec.py

# Calibrate colors
python3 color_finder.py

# Test DMX input
python3 test_dmx_input.py

# Show configuration
python3 dmx_fire_controller.py --config
python3 config.py
```

## Next Steps / Future Improvements

Possible future enhancements:
- Add more bank size configurations
- Implement cue/scene system
- Add remote control web interface
- Support for Art-Net in addition to sACN
- Implement effect presets accessible via DMX
- Add configurable base colors per bank

## Support

See documentation:
- `README.md` - Full documentation
- `DUAL_WLED_SETUP.md` - Multicast setup guide
- `ARCHITECTURE.txt` - Technical details
- `ENTTEC_SETUP_GUIDE.md` - Troubleshooting

---

**Project**: DMX Fire Controller
**Version**: Production (Jan 2026)
**License**: Personal and commercial use
