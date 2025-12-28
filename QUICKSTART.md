# Quick Start Guide - 1,500 Candles Fire Controller

Get your DMX-controlled fire effects running in 5 minutes!

## Step 1: Install Dependencies

```bash
pip3 install pyserial sacn
```

## Step 2: Find Your ENTTEC Device

```bash
python3 find_enttec.py
```

This will show you all available serial ports and recommend the correct one to use.

**Expected output:**
```
✅ Found 1 serial port(s):

✅ 1. /dev/cu.usbserial-EN437698
      Type: cu (call-out)
      ✅ Correct for macOS

🧪 Testing recommended ports...
   Testing: /dev/cu.usbserial-EN437698
   ✅ Port opened successfully

✅ 1 working port(s) found:
   /dev/cu.usbserial-EN437698

📝 To use in your config.py:
   DMX_SERIAL_PORT = '/dev/cu.usbserial-EN437698'
```

## Step 3: Configure Settings

Edit `config.py`:

```python
# Update these two settings:
DMX_SERIAL_PORT = '/dev/cu.usbserial-EN437698'  # From Step 2
WLED_IP = '192.168.4.74'  # Your WLED IP address
```

**Find your WLED IP:**
- Check your router's DHCP list, or
- Look at the WLED device display (if it has one), or
- Use a network scanner app

**Verify configuration:**
```bash
python3 config.py
```

## Step 4: Test DMX Input

```bash
python3 test_dmx_input.py
```

**Move faders** on your DMX console - you should see values changing:

```
Packets:   1234 | Ch 1-8: 255   0 128  64   0   0   0   0 | Ch 9-16:   0   0   0   0   0   0   0   0
```

If values don't change:
- Check XLR cable is connected (DMX Out → ENTTEC In)
- Verify console is outputting on Universe 1
- Ensure faders are raised

**Press Ctrl+C** to stop the test.

## Step 5: Configure WLED

1. Open WLED web interface: `http://[WLED-IP]`
2. Go to **Settings → Sync Interfaces**
3. Configure:
   - ✅ Enable **E1.31 (sACN)**
   - Set **Start Universe** to `1`
   - ❌ Disable **Multicast** (use Unicast)
   - Set **DMX Start Address** to `1`
4. **Save** settings

**Test WLED connection:**
```bash
ping [WLED-IP]
curl http://[WLED-IP]/json/info
```

## Step 6: Run the Fire Controller!

```bash
python3 dmx_fire_controller.py
```

Or with debug output to see DMX values:
```bash
python3 dmx_fire_controller.py --debug
```

**Expected output:**
```
🔥 DMX Fire Controller - Low Latency Edition
======================================================================

📡 DMX Input:
   Port: /dev/cu.usbserial-EN437698
   Universe: 1 (logical)
   Channels: 1-3 (Banks), 4 (Flicker), 5 (Yellow→Red), 6 (Blue)
   ✓ ENTTEC DMX USB Pro ready

🔥 Flame Banks:
   Bank 1: 500 flames (pixels    0- 499, every 1st)
   Bank 2: 500 flames (pixels  500- 999, every 1st)
   Bank 3: 500 flames (pixels 1000-1499, every 1st)

📤 sACN Output:
   Destination: 192.168.4.74
   Universes: 1-9 (9 total)
   Total LEDs: 1500
   ✓ sACN sender ready

======================================================================

🎭 Starting main control loop (target: 60 FPS)
   Press Ctrl+C to stop

🔥  52.3 FPS | DMX:245.2 pkt/s | Latency:  5.8ms | B1:100% B2: 99% B3:100% | Flicker:100% | Y→R: 29% | Blue: 21%
```

## Step 7: Control from Your DMX Console

Set up 6 channels on Universe 1:

| Channel | Function | Recommended Start |
|---------|----------|-------------------|
| 1 | Bank 1 Intensity | 255 (full) |
| 2 | Bank 2 Intensity | 255 (full) |
| 3 | Bank 3 Intensity | 255 (full) |
| 4 | Flicker Speed | 127 (medium) |
| 5 | Color Shift (Yellow→Red) | 0 (yellow) |
| 6 | Blue Component | 0 (no blue) |

**Bring up channels 1-3** to see fire effects appear!

## Troubleshooting

### No LEDs lighting up?

1. **Check DMX input is working:**
   ```bash
   python3 test_dmx_input.py
   ```
   Move faders - values should change.

2. **Check WLED is reachable:**
   ```bash
   ping [WLED-IP]
   ```

3. **Verify WLED sACN settings:**
   - E1.31 enabled?
   - Universe = 1?
   - Unicast mode (not multicast)?

4. **Check channels 1-3 have values > 0**

### Application hangs on startup? (macOS)

You're using `/dev/tty.*` instead of `/dev/cu.*`!

1. Kill the process: `pkill -9 python3`
2. Update `config.py` to use `/dev/cu.usbserial-*`
3. Restart

### "Multiple access on port" error?

Another process is using the serial port.

```bash
# Find and kill competing processes
lsof /dev/cu.usbserial-EN437698
kill -9 <PID>
```

## Color Palette Examples

Try these settings:

**Classic Candle:**
- Ch 1-3: 255, Ch 4: 127, Ch 5: 0, Ch 6: 0

**White-Hot Flame:**
- Ch 1-3: 255, Ch 4: 255, Ch 5: 0, Ch 6: 255

**Deep Red Ember:**
- Ch 1-3: 128, Ch 4: 64, Ch 5: 255, Ch 6: 0

**Energetic White Fire:**
- Ch 1-3: 255, Ch 4: 255, Ch 5: 50, Ch 6: 127

## Next Steps

- **Full Documentation:** See `README.md`
- **Troubleshooting Guide:** See `ENTTEC_SETUP_GUIDE.md`
- **Technical Details:** See `ARCHITECTURE.txt`

## Command Reference

```bash
# Find ENTTEC device
python3 find_enttec.py

# Check configuration
python3 config.py

# Test DMX input
python3 test_dmx_input.py

# Run fire controller
python3 dmx_fire_controller.py

# Run with debug output
python3 dmx_fire_controller.py --debug

# Show configuration
python3 dmx_fire_controller.py --config
```

---

🔥 **Enjoy your fire effects!** 🔥
