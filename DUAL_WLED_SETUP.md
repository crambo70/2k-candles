# Dual WLED Setup Guide

This guide explains how to configure two WLED controllers to work together using multicast sACN.

## Overview

- **Total LEDs**: 1,700 actual pixels (1,845 with gap)
- **Total Banks**: 13 (controlled via DMX channels 7-19)
  - Banks 1-7: 125 LEDs each (WLED ONE)
  - Banks 8-10: 125 LEDs each (WLED TWO)
  - Banks 11-13: 150 LEDs each (WLED TWO)
- **WLED ONE**: Banks 1-7 (875 pixels, universes 1-6)
- **GAP**: 145 pixels unused (between universes 6 and 7)
- **WLED TWO**: Banks 8-13 (825 pixels, universes 7-11)

## How Multicast Works

With multicast enabled, the fire controller sends sACN data to the network multicast group. Both WLED boxes listen to this multicast stream and each picks up only their configured universe range.

## Configuration Steps

### Step 1: Configure config.py

Edit `config.py` and set:

```python
# Enable multicast mode
USE_MULTICAST = True

# Total LEDs across both WLED boxes (includes 145-pixel gap)
TOTAL_PIXELS = 1845

# Starting universe
WLED_UNIVERSE_START = 1
```

### Step 2: Configure WLED Box ONE

1. Connect to WLED ONE's web interface
2. Go to **Settings** → **LED Preferences**
3. Set **LED Count** to `875` (Banks 1-7)
4. Go to **Settings** → **Sync Interfaces**
5. Enable **E1.31 (sACN)**
6. Set **Start Universe** to `1`
7. Set **Universe Count** to `6`
8. **Enable Multicast** checkbox
9. Click **Save**

**Note:** Covers banks 1-7 (125 LEDs each = 875 total).

### Step 3: Configure WLED Box TWO

1. Connect to WLED TWO's web interface
2. Go to **Settings** → **LED Preferences**
3. Set **LED Count** to `825` (Banks 8-13)
4. Go to **Settings** → **Sync Interfaces**
5. Enable **E1.31 (sACN)**
6. Set **Start Universe** to `7`
7. Set **Universe Count** to `5`
8. **Enable Multicast** checkbox
9. Click **Save**

**Note:** Starts at universe 7. There's a 145-pixel gap between WLED ONE and TWO.

## Universe Distribution

The controller maps banks with a gap between WLED boxes:

### WLED BOX ONE
- **Banks**: 1-7 (125 LEDs each)
- **Universes**: 1-6
- **Pixels**: 0-874 (875 pixels total)
- **Configuration**: Start Universe 1, 6 universes

### GAP (Unused)
- **Pixels**: 875-1019 (145 pixels)
- No WLED box receives this data

### WLED BOX TWO
- **Banks**: 8-13
  - Banks 8-10: 125 LEDs each
  - Banks 11-13: 150 LEDs each
- **Universes**: 7-11
- **Pixels**: 1020-1844 (825 pixels total)
- **Configuration**: Start Universe 7, 5 universes

## DMX Channel Mapping

### Control Channels (Global)
- **Channel 1**: Flicker Speed
- **Channel 2**: Color Shift (Yellow ← → Red)
- **Channel 3**: Sporadic Flicker / Wind Gust
- **Channel 6**: Master Intensity (affects all 13 banks)

### Bank Channels (Individual)
- **Channel 7**: Bank 1 Intensity → WLED ONE
- **Channel 8**: Bank 2 Intensity → WLED ONE
- **Channel 9**: Bank 3 Intensity → WLED ONE
- **Channel 10**: Bank 4 Intensity → WLED ONE
- **Channel 11**: Bank 5 Intensity → WLED ONE
- **Channel 12**: Bank 6 Intensity → WLED ONE
- **Channel 13**: Bank 7 Intensity → WLED ONE
- **Channel 14**: Bank 8 Intensity → WLED TWO
- **Channel 15**: Bank 9 Intensity → WLED TWO
- **Channel 16**: Bank 10 Intensity → WLED TWO
- **Channel 17**: Bank 11 Intensity → WLED TWO
- **Channel 18**: Bank 12 Intensity → WLED TWO
- **Channel 19**: Bank 13 Intensity → WLED TWO

**Note**: The final intensity of each bank is calculated as: `Bank Intensity × Master Intensity`

For example:
- Master at 100%, Bank 1 at 50% = 50% effective intensity
- Master at 50%, Bank 1 at 100% = 50% effective intensity
- Master at 50%, Bank 1 at 50% = 25% effective intensity

## Troubleshooting

### Both WLED boxes show the same pattern
- Check that each WLED has a different **Start Universe** setting
- WLED ONE should start at universe 1
- WLED TWO should start at universe 6

### One WLED box is not responding
- Verify multicast is enabled on both boxes
- Check that universe ranges don't overlap
- Ensure both boxes are on the same network/subnet
- Check universe count matches the needed universes

### Patterns are offset or incorrect
- Verify LED counts:
  - WLED ONE: 875 LEDs (Banks 1-7)
  - WLED TWO: 825 LEDs (Banks 8-13)
- Check Start Universe settings:
  - WLED ONE: Start Universe 1
  - WLED TWO: Start Universe 7 (not 6!)
- Ensure RGB order is correct (typically GRB for WS2812B)

### Banks 8-13 aren't working
- Make sure WLED TWO starts at universe **7**, not 6
- There's intentionally a 145-pixel gap between the boxes

## Switching to Unicast Mode

If you want to use unicast instead (single WLED or specific IP):

Edit `config.py`:
```python
USE_MULTICAST = False
WLED_IP = '192.168.4.220'  # Your WLED's IP address
```

Then configure your WLED:
- Disable multicast
- Set start universe to 1
- Set LED count to 1701

## Testing

1. Run the controller:
   ```bash
   python3 dmx_fire_controller.py
   ```

2. Check the startup output:
   ```
   📤 sACN Output:
      Mode: MULTICAST
      Total Universes: 1-11 (11 total)
      WLED ONE: Universes 1-5 (Banks 1-6, ~786 flames)
      WLED TWO: Universes 6-11 (Banks 7-13, ~915 flames)
   ```

3. Use your DMX console to test individual banks (channels 7-19)
4. Verify banks 1-6 control WLED ONE
5. Verify banks 7-13 control WLED TWO

## Network Requirements

- Both WLED boxes must be on the same network/subnet
- Multicast must be enabled on your network (most home networks support this)
- If using VLANs, ensure multicast routing is configured
- Firewall must allow UDP port 5568 (sACN)
