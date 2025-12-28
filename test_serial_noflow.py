#!/usr/bin/env python3
"""Test serial port with flow control disabled"""

import serial
import sys

port_name = '/dev/cu.usbserial-EN437698'

print(f"Attempting to open: {port_name}")
print("With flow control disabled...")

try:
    ser = serial.Serial(
        port=port_name,
        baudrate=115200,
        timeout=0.1,
        rtscts=False,      # Disable RTS/CTS flow control
        dsrdtr=False,      # Disable DSR/DTR flow control
        xonxoff=False      # Disable software flow control
    )
    print(f"✓ Port opened successfully!")
    print(f"  Is open: {ser.is_open}")
    print(f"  Baudrate: {ser.baudrate}")

    print("\nAttempting to read 10 bytes...")
    data = ser.read(10)
    print(f"  Read {len(data)} bytes: {data.hex() if data else '(none)'}")

    ser.close()
    print("\n✓ Test complete!")

except serial.SerialException as e:
    print(f"✗ SerialException: {e}")
    sys.exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
