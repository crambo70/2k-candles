#!/usr/bin/env python3
"""
Test script to read DMX input from ENTTEC DMX USB Pro
"""

import serial
import struct
import time
import sys

# Import configuration
try:
    import config
except ImportError:
    print("⚠️  Warning: config.py not found, using defaults")
    class config:
        DMX_SERIAL_PORT = '/dev/cu.usbserial-EN437698'

class EnttecDMXProInput:
    START_DELIMITER = 0x7E
    END_DELIMITER = 0xE7
    LABEL_RECEIVED_DMX = 0x05
    LABEL_SET_RECEIVE_MODE = 0x08

    def __init__(self, port_name, baudrate=115200):
        print(f"Opening serial port: {port_name}")
        try:
            self.port = serial.Serial(
                port=port_name,
                baudrate=baudrate,
                bytesize=8,
                parity='N',
                stopbits=1,
                timeout=0.1
            )
            print(f"✓ Serial port opened successfully")
        except Exception as e:
            print(f"✗ Failed to open serial port: {e}")
            sys.exit(1)

        self.dmx_data = [0] * 512
        self.packet_count = 0
        self.last_update = time.time()

        print("Enabling DMX receive mode...")
        self.enable_always_receive()
        time.sleep(0.2)
        print("✓ Device configured for DMX input\n")

    def enable_always_receive(self):
        """Send Label 8 to enable always-send mode"""
        message = bytes([
            self.START_DELIMITER,
            self.LABEL_SET_RECEIVE_MODE,
            0x01, 0x00,  # Length: 1 byte
            0x00,        # Mode: 0 = always send
            self.END_DELIMITER
        ])
        self.port.write(message)

    def read_message(self):
        """Read a single message from the device"""
        # Wait for start delimiter
        timeout_counter = 0
        while timeout_counter < 100:
            byte = self.port.read(1)
            if not byte:
                timeout_counter += 1
                continue
            if byte[0] == self.START_DELIMITER:
                break
            timeout_counter += 1
        else:
            return None

        # Read label
        label_byte = self.port.read(1)
        if not label_byte:
            return None
        label = label_byte[0]

        # Read length (2 bytes, little-endian)
        length_bytes = self.port.read(2)
        if len(length_bytes) != 2:
            return None
        length = struct.unpack('<H', length_bytes)[0]

        # Read payload
        payload = self.port.read(length)
        if len(payload) != length:
            return None

        # Read end delimiter
        end_byte = self.port.read(1)
        if not end_byte or end_byte[0] != self.END_DELIMITER:
            print(f"Warning: Invalid end delimiter (got {end_byte.hex() if end_byte else 'None'})")

        return {'label': label, 'data': payload}

    def process_dmx_packet(self, payload):
        """Process a Label 5 (Received DMX) packet"""
        if len(payload) < 1:
            return False

        # Check status byte
        status = payload[0]
        if status != 0:
            print(f"⚠ DMX receive error: 0x{status:02X}")
            if status & 0x01:
                print("  - Receive queue overflow")
            if status & 0x02:
                print("  - Receive overrun")
            return False

        # Extract DMX data
        # Skip status byte, may need to adjust for undocumented bytes
        dmx_with_start = payload[1:]

        if len(dmx_with_start) > 0:
            start_code = dmx_with_start[0]
            channels = dmx_with_start[1:]

            # Update internal DMX data array
            for i, value in enumerate(channels):
                if i < 512:
                    self.dmx_data[i] = value

            self.packet_count += 1
            return True
        return False

    def get_channel(self, channel):
        """Get DMX channel value (1-512)"""
        if 1 <= channel <= 512:
            return self.dmx_data[channel - 1]
        return 0

    def get_channels(self, start, end):
        """Get a range of DMX channel values"""
        return [self.get_channel(i) for i in range(start, end + 1)]

    def poll(self):
        """Poll for new DMX data"""
        message = self.read_message()
        if message and message['label'] == self.LABEL_RECEIVED_DMX:
            return self.process_dmx_packet(message['data'])
        return False

    def close(self):
        """Close the serial port"""
        self.port.close()

def main():
    # ENTTEC device path from config
    device_path = config.DMX_SERIAL_PORT

    print("=" * 60)
    print("ENTTEC DMX USB Pro - DMX Input Test")
    print("=" * 60)
    print(f"Serial Port: {device_path}")
    print()

    dmx_input = EnttecDMXProInput(device_path)

    try:
        print("Listening for DMX data...")
        print("Move faders on your DMX console to see values change")
        print("Press Ctrl+C to stop\n")
        print("-" * 60)

        last_print = time.time()
        no_data_timeout = time.time()

        while True:
            if dmx_input.poll():
                no_data_timeout = time.time()

                # Print every 100ms to avoid flooding
                now = time.time()
                if now - last_print >= 0.1:
                    # Display first 16 channels
                    channels_1_8 = dmx_input.get_channels(1, 8)
                    channels_9_16 = dmx_input.get_channels(9, 16)

                    print(f"\rPackets: {dmx_input.packet_count:6d} | "
                          f"Ch 1-8: {' '.join(f'{v:3d}' for v in channels_1_8)} | "
                          f"Ch 9-16: {' '.join(f'{v:3d}' for v in channels_9_16)}",
                          end='', flush=True)

                    last_print = now
            else:
                # Check if we haven't received data in a while
                if time.time() - no_data_timeout > 3.0:
                    print("\r⚠ No DMX data received in 3 seconds. "
                          "Check DMX console connection and output.           ",
                          end='', flush=True)
                    no_data_timeout = time.time()

            time.sleep(0.01)  # 100Hz polling

    except KeyboardInterrupt:
        print("\n\n" + "-" * 60)
        print(f"Stopped. Total packets received: {dmx_input.packet_count}")
        print("=" * 60)
    except Exception as e:
        print(f"\n\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        dmx_input.close()
        print("Serial port closed.")

if __name__ == '__main__':
    main()
