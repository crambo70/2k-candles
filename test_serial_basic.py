#!/usr/bin/env python3
"""Minimal serial port test"""

import serial
import sys

port_name = '/dev/cu.usbserial-EN437698'  # Use cu not tty on macOS

print(f"Attempting to open: {port_name}")
print("Testing with minimal timeout...")

try:
    # Try with very short timeout
    ser = serial.Serial(
        port=port_name,
        baudrate=115200,
        timeout=0.1
    )
    print(f"✓ Port opened successfully!")
    print(f"  Is open: {ser.is_open}")
    print(f"  Baudrate: {ser.baudrate}")

    # Try a quick read
    print("\nAttempting to read 1 byte...")
    data = ser.read(1)
    print(f"  Read {len(data)} bytes: {data.hex() if data else '(none)'}")

    ser.close()
    print("\n✓ Test complete - port is working!")

except serial.SerialException as e:
    print(f"✗ SerialException: {e}")
    sys.exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
