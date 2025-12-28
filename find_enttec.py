#!/usr/bin/env python3
"""
ENTTEC DMX USB Pro - Device Finder & Tester

Cross-platform utility to find and test ENTTEC devices.
"""

import platform
import glob
import serial
import sys
import time

def find_serial_ports():
    """Find all available serial ports on this system."""
    system = platform.system()
    ports = []

    if system == 'Darwin':  # macOS
        # Look for both cu and tty devices
        cu_ports = glob.glob('/dev/cu.usbserial-*')
        tty_ports = glob.glob('/dev/tty.usbserial-*')

        for port in cu_ports:
            ports.append({
                'port': port,
                'type': 'cu (call-out)',
                'recommended': True,
                'notes': '✅ Correct for macOS'
            })

        for port in tty_ports:
            ports.append({
                'port': port,
                'type': 'tty (dial-in)',
                'recommended': False,
                'notes': '❌ Will hang on macOS - use cu instead'
            })

    elif system == 'Windows':
        import serial.tools.list_ports
        for port in serial.tools.list_ports.comports():
            is_enttec = 'ENTTEC' in port.description or 'USB Serial' in port.description
            ports.append({
                'port': port.device,
                'type': port.description,
                'recommended': is_enttec,
                'notes': '✅ ENTTEC device' if is_enttec else 'Other USB serial device'
            })

    elif system == 'Linux':
        usb_ports = glob.glob('/dev/ttyUSB*')
        acm_ports = glob.glob('/dev/ttyACM*')

        for port in usb_ports:
            ports.append({
                'port': port,
                'type': 'USB serial',
                'recommended': True,
                'notes': '✅ Standard USB serial port'
            })

        for port in acm_ports:
            ports.append({
                'port': port,
                'type': 'ACM device',
                'recommended': False,
                'notes': 'May be ENTTEC or other device'
            })

    return ports

def test_serial_port(port_name, quick=True):
    """Test if a serial port can be opened and read."""
    try:
        print(f"   Testing: {port_name}")

        ser = serial.Serial(
            port=port_name,
            baudrate=115200,
            timeout=0.1,
            rtscts=False,
            dsrdtr=False,
            xonxoff=False
        )

        print(f"   ✅ Port opened successfully")

        if not quick:
            # Try to read some data
            print(f"   Reading data...")
            data = ser.read(10)
            if data:
                print(f"   📡 Read {len(data)} bytes: {data.hex()}")
            else:
                print(f"   📭 No data available (expected if no DMX signal)")

        ser.close()
        return True

    except serial.SerialException as e:
        print(f"   ❌ Failed: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    print("=" * 70)
    print("ENTTEC DMX USB Pro - Device Finder & Tester")
    print("=" * 70)
    print()

    # Platform info
    system = platform.system()
    print(f"🖥️  Platform: {system} ({platform.platform()})")
    print(f"🐍 Python: {platform.python_version()}")
    print()

    # Find serial ports
    print("🔍 Searching for serial ports...")
    ports = find_serial_ports()

    if not ports:
        print("❌ No serial ports found!")
        print()
        print("Troubleshooting:")
        if system == 'Darwin':
            print("  - Check if ENTTEC is plugged in")
            print("  - Try: ls -la /dev/cu.usbserial-*")
        elif system == 'Windows':
            print("  - Check Device Manager → Ports (COM & LPT)")
            print("  - Install ENTTEC drivers if needed")
        elif system == 'Linux':
            print("  - Check if ENTTEC is plugged in")
            print("  - Try: ls -la /dev/ttyUSB*")
            print("  - Add yourself to dialout group:")
            print("    sudo usermod -a -G dialout $USER")
        sys.exit(1)

    print(f"✅ Found {len(ports)} serial port(s):")
    print()

    # Display ports
    recommended_ports = []
    for i, port_info in enumerate(ports, 1):
        marker = "✅" if port_info['recommended'] else "⚠️ "
        print(f"{marker} {i}. {port_info['port']}")
        print(f"      Type: {port_info['type']}")
        print(f"      {port_info['notes']}")
        print()

        if port_info['recommended']:
            recommended_ports.append(port_info['port'])

    # macOS warning
    if system == 'Darwin':
        tty_count = sum(1 for p in ports if 'tty' in p['port'])
        if tty_count > 0:
            print("⚠️  IMPORTANT FOR macOS:")
            print("   ALWAYS use /dev/cu.* devices, NOT /dev/tty.* devices!")
            print("   Using tty devices will cause the application to hang.")
            print()

    # Test recommended ports
    if recommended_ports:
        print("🧪 Testing recommended ports...")
        print()

        working_ports = []
        for port in recommended_ports:
            if test_serial_port(port, quick=True):
                working_ports.append(port)
            print()

        # Summary
        print("=" * 70)
        print("📋 Summary")
        print("=" * 70)

        if working_ports:
            print(f"✅ {len(working_ports)} working port(s) found:")
            for port in working_ports:
                print(f"   {port}")
            print()
            print("📝 To use in your config.py:")
            print(f"   DMX_SERIAL_PORT = '{working_ports[0]}'")
            print()
            print("🧪 To test DMX input:")
            print(f"   python3 test_dmx_input.py")
        else:
            print("❌ No working ports found!")
            print()
            print("Troubleshooting:")
            print("  1. Unplug and replug the ENTTEC device")
            print("  2. Wait 5 seconds")
            print("  3. Run this script again")
            if system == 'Linux':
                print("  4. Check permissions:")
                print("     sudo usermod -a -G dialout $USER")
                print("     (then log out and back in)")

    else:
        print("⚠️  No recommended ports to test.")

    print("=" * 70)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
