# ENTTEC DMX USB Pro - Setup & Troubleshooting Guide

## Critical Platform-Specific Information

### macOS Setup ⚠️ IMPORTANT

**ALWAYS use `/dev/cu.usbserial-*` NOT `/dev/tty.usbserial-*`**

- ✅ **Correct:** `/dev/cu.usbserial-EN437698`
- ❌ **Wrong:** `/dev/tty.usbserial-EN437698`

**Why?** On macOS:
- `/dev/tty.*` devices are "dial-in" devices that wait for carrier detect
- `/dev/cu.*` devices are "call-out" devices for outgoing connections
- Using `tty` instead of `cu` will cause the application to **hang indefinitely** when opening the serial port
- This is the #1 cause of crashes and hangs on macOS

### Windows Setup

On Windows, use COM port notation:
- Format: `COM3`, `COM4`, etc.
- Find your port in Device Manager under "Ports (COM & LPT)"
- Look for "USB Serial Port (COMx)" or "ENTTEC DMX USB PRO"

### Linux Setup

On Linux, typically:
- Format: `/dev/ttyUSB0`, `/dev/ttyUSB1`, etc.
- You may need to add your user to the `dialout` group:
  ```bash
  sudo usermod -a -G dialout $USER
  ```
- Log out and back in for changes to take effect

## Finding Your ENTTEC Device

### macOS
```bash
ls -la /dev/cu.usbserial-*
```
Look for: `/dev/cu.usbserial-EN######` where ###### is your device serial number

### Windows
1. Open Device Manager (Win + X → Device Manager)
2. Expand "Ports (COM & LPT)"
3. Look for "ENTTEC DMX USB PRO" or "USB Serial Port"
4. Note the COM number (e.g., COM3)

### Linux
```bash
ls -la /dev/ttyUSB*
# or
dmesg | grep tty
```

## Hardware Specifications

- **Baud Rate:** 115200 (fixed, do not change)
- **Data Bits:** 8
- **Parity:** None
- **Stop Bits:** 1
- **Flow Control:** None (disabled)

## Common Issues & Solutions

### Issue 1: Application Hangs on Startup (macOS)

**Symptom:** Script starts but becomes unresponsive, no error message

**Cause:** Using `/dev/tty.usbserial-*` instead of `/dev/cu.usbserial-*`

**Solution:**
1. Kill the hung process: `pkill -9 python3`
2. Update all scripts to use `/dev/cu.usbserial-*`
3. Restart the application

### Issue 2: "Device disconnected or multiple access on port"

**Symptom:**
```
serial.serialutil.SerialException: device reports readiness to read but returned no data
(device disconnected or multiple access on port?)
```

**Cause:** Multiple processes trying to access the same serial port

**Solution:**
1. Find processes using the port (macOS):
   ```bash
   lsof /dev/cu.usbserial-EN437698
   ```
2. Kill competing processes:
   ```bash
   kill -9 <PID>
   ```
3. Or kill all Python processes:
   ```bash
   pkill -9 python3
   ```

### Issue 3: Permission Denied (Linux)

**Symptom:** `PermissionError: [Errno 13] Permission denied: '/dev/ttyUSB0'`

**Solution:**
```bash
# Add user to dialout group
sudo usermod -a -G dialout $USER

# Or change permissions temporarily (not recommended for production)
sudo chmod 666 /dev/ttyUSB0
```

### Issue 4: Device Not Found

**Symptom:** Port doesn't exist or can't be opened

**Solution:**
1. Check USB connection - unplug and replug the device
2. Wait 5 seconds after plugging in
3. Verify device appears in system:
   - **macOS:** `ls /dev/cu.usbserial-*`
   - **Windows:** Device Manager
   - **Linux:** `ls /dev/ttyUSB*`
4. Check USB cable (try a different cable)
5. Try a different USB port

### Issue 5: No DMX Data Received

**Symptom:** Port opens successfully but no DMX packets are received

**Checklist:**
- [ ] DMX console is powered on and outputting
- [ ] XLR cable is properly connected (DMX Out → ENTTEC In)
- [ ] DMX universe on console matches expected universe
- [ ] Console faders are raised (DMX values > 0)
- [ ] Cable is DMX-rated (not audio XLR)

**Test:**
```bash
python3 test_dmx_input.py
```
Move faders - you should see values change. If not, check cables and console settings.

## ENTTEC Protocol Basics

### Message Structure
```
[Start] [Label] [Length LSB] [Length MSB] [Data...] [End]
 0x7E    0xNN    0xLL         0xLL         ...       0xE7
```

### Key Labels
- **Label 5 (0x05):** Received DMX Packet (from console → computer)
- **Label 8 (0x08):** Set Receive Mode (enable always-send mode)

### Receive Mode
The controller sends Label 8 on startup to enable "always-send" mode:
```python
message = bytes([
    0x7E,        # Start delimiter
    0x08,        # Label 8: Set Receive Mode
    0x01, 0x00,  # Length: 1 byte
    0x00,        # Mode: 0 = always send
    0xE7         # End delimiter
])
```

This tells the ENTTEC to continuously forward DMX packets without waiting for polling.

## Best Practices

### 1. Always Check for Existing Processes
Before starting your application:
```bash
# macOS/Linux
lsof /dev/cu.usbserial-EN437698

# Or check all Python processes
ps aux | grep python
```

### 2. Use Timeouts
Set reasonable serial timeouts (0.001-0.1 seconds) to prevent blocking:
```python
serial.Serial(
    port=port_name,
    baudrate=115200,
    timeout=0.001  # 1ms timeout
)
```

### 3. Handle Errors Gracefully
Wrap serial operations in try-except blocks:
```python
try:
    data = port.read(1)
except serial.SerialException as e:
    print(f"Serial error: {e}")
    # Continue with last known values
```

### 4. Clean Shutdown
Always close the serial port on exit:
```python
try:
    # Your code here
finally:
    port.close()
```

### 5. Physical Reset
If all else fails, physically unplug and replug the ENTTEC device. Wait 5 seconds before reconnecting.

## Performance Considerations

### Buffer Draining
The ENTTEC can buffer multiple DMX packets. For low latency, drain the buffer each frame:
```python
for _ in range(10):  # Read up to 10 packets per poll
    message = self._read_message()
    if message:
        process(message)
    else:
        break  # No more data available
```

### Hysteresis Filtering
Reduce noise from DMX by ignoring small changes:
```python
if abs(new_value - old_value) > 5:  # 2% threshold
    old_value = new_value
```

### Typical Performance
- **DMX Packet Rate:** 200-400 packets/second (varies by console)
- **Latency:** 3-80ms from console to computer
- **Frame Rate:** Can sustain 50-60 FPS rendering

## Testing Procedure

### 1. Basic Port Test
```bash
python3 test_serial_noflow.py
```
Expected: Port opens, reads some bytes, closes successfully

### 2. DMX Input Test
```bash
python3 test_dmx_input.py
```
Expected: Shows real-time DMX values, updates when you move console faders

### 3. Full Controller Test
```bash
python3 dmx_fire_controller.py --debug
```
Expected: Shows DMX values AND sends sACN to WLED

## Serial Port Configuration Summary

| Platform | Port Format | Example | Notes |
|----------|-------------|---------|-------|
| macOS | `/dev/cu.usbserial-*` | `/dev/cu.usbserial-EN437698` | ⚠️ Must use `cu` not `tty` |
| Windows | `COMx` | `COM3` | Check Device Manager |
| Linux | `/dev/ttyUSB*` | `/dev/ttyUSB0` | May need dialout group |

## Quick Reference

### Kill All Python Processes (Emergency)
```bash
# macOS/Linux
pkill -9 python3

# Windows
taskkill /F /IM python.exe
```

### Check ENTTEC Connection
```bash
# macOS
ioreg -p IOUSB -l -w0 | grep -i enttec

# Linux
lsusb | grep -i enttec
```

### Monitor Serial Traffic (Advanced)
```bash
# macOS (requires socat)
socat -v /dev/cu.usbserial-EN437698,b115200 STDOUT
```

## Support & Resources

- **ENTTEC API Documentation:** https://www.enttec.com/product/lighting-communication-protocols/dmx512/dmx-usb-pro/
- **Project Documentation:** See `README_DMX_FIRE.md` and `ARCHITECTURE.txt`
- **Issue Tracking:** Check for serial port conflicts first!

---

*Last Updated: 2025-12-19*
