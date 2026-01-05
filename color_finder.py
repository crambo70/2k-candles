#!/usr/bin/env python3
"""
Color Finder - Direct RGB Control via DMX

Use DMX channels 1-3 to directly control RGB values for all LEDs.
Helps find the perfect base color for candle flames.

DMX Input Channels:
- Channel 1: Red (0-255)
- Channel 2: Green (0-255)
- Channel 3: Blue (0-255)

sACN Output:
- All 1,500 LEDs set to the same solid color
"""

import serial
import struct
import time
import sacn
from typing import Dict, Optional
import sys
import os

# Import configuration
try:
    import config
except ImportError:
    print("⚠️  Error: config.py not found!")
    print("   Please copy config.py.example to config.py and configure your settings.")
    sys.exit(1)


# ============================================================================
# ENTTEC DMX USB Pro Input Handler (same as main controller)
# ============================================================================

class EnttecDMXProInput:
    """Low-latency DMX input from ENTTEC DMX USB Pro."""

    START_DELIMITER = 0x7E
    END_DELIMITER = 0xE7
    LABEL_RECEIVED_DMX = 0x05
    LABEL_SET_RECEIVE_MODE = 0x08

    def __init__(self, port_name: str, baudrate: int = 115200):
        """
        Initialize ENTTEC DMX USB Pro for input.

        Args:
            port_name: Serial port path (e.g., '/dev/tty.usbserial-XXXXXXXX')
            baudrate: Serial baud rate (default: 115200)
        """
        self.port = serial.Serial(
            port=port_name,
            baudrate=baudrate,
            bytesize=8,
            parity='N',
            stopbits=1,
            timeout=0.001  # Ultra-low timeout for minimal latency
        )

        self.dmx_data = [0] * 512
        self.packet_count = 0
        self.last_status = 0
        self.last_packet_time = time.time()

        # Enable always-send mode
        self._enable_always_receive()

    def _enable_always_receive(self):
        """Send Label 8 to enable always-send mode."""
        message = bytes([
            self.START_DELIMITER,
            self.LABEL_SET_RECEIVE_MODE,
            0x01, 0x00,  # Length: 1 byte
            0x00,        # Mode: 0 = always send
            self.END_DELIMITER
        ])
        self.port.write(message)

    def poll(self) -> int:
        """
        Poll for new DMX data (non-blocking, aggressive).
        Reads multiple packets if available.

        Returns:
            Number of packets received
        """
        packets_received = 0

        # Try to read multiple messages (drain the buffer)
        for _ in range(10):  # Max 10 packets per poll
            try:
                message = self._read_message()
                if message and message['label'] == self.LABEL_RECEIVED_DMX:
                    if self._process_dmx_packet(message['data']):
                        packets_received += 1
                else:
                    break  # No more data available
            except serial.SerialException as e:
                # Serial port error - return what we have so far
                print(f"\n⚠️  Serial port error: {e}")
                print("    Continuing with last known DMX values...")
                break

        return packets_received

    def _read_message(self) -> Optional[Dict]:
        """Read a single message from device (non-blocking)."""
        # Look for start delimiter
        start_found = False
        for _ in range(5):  # Max 5 attempts (reduced for speed)
            byte = self.port.read(1)
            if not byte:
                return None
            if byte[0] == self.START_DELIMITER:
                start_found = True
                break

        if not start_found:
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
            pass  # Continue anyway

        return {'label': label, 'data': payload}

    def _process_dmx_packet(self, payload: bytes) -> bool:
        """Process a Label 5 (Received DMX) packet."""
        if len(payload) < 1:
            return False

        # Check status byte
        status = payload[0]
        self.last_status = status

        if status != 0:
            # Non-zero status indicates errors, but we'll process anyway
            pass

        # Extract DMX data (skip status byte)
        dmx_with_start = payload[1:]

        if len(dmx_with_start) > 0:
            # Skip start code, get channel data
            channels = dmx_with_start[1:]

            # Update internal DMX data array
            for i, value in enumerate(channels):
                if i < 512:
                    self.dmx_data[i] = value

            self.packet_count += 1
            self.last_packet_time = time.time()
            return True

        return False

    def get_channel(self, channel: int) -> int:
        """Get DMX channel value (1-512, 1-indexed)."""
        if 1 <= channel <= 512:
            return self.dmx_data[channel - 1]
        return 0

    def close(self):
        """Close the serial port."""
        self.port.close()


# ============================================================================
# Color Finder Controller
# ============================================================================

class ColorFinder:
    """
    Simple RGB color finder using DMX input.

    Channels 1-3 directly control Red, Green, Blue for all LEDs.
    """

    def __init__(self,
                 dmx_serial_port: str,
                 dmx_universe: int,
                 output_ip: str,
                 output_universe_start: int,
                 total_pixels: int):
        """
        Initialize the color finder.

        Args:
            dmx_serial_port: Serial port for ENTTEC device
            dmx_universe: Logical input universe number (for display only)
            output_ip: IP address of WLED device
            output_universe_start: Starting sACN universe for output
            total_pixels: Total number of LEDs
        """
        self.dmx_universe = dmx_universe
        self.output_ip = output_ip
        self.output_universe_start = output_universe_start
        self.total_pixels = total_pixels

        print(f"\n🎨 Color Finder - RGB Control")
        print(f"=" * 70)

        # Initialize DMX input
        print(f"\n📡 DMX Input:")
        print(f"   Port: {dmx_serial_port}")
        print(f"   Universe: {dmx_universe} (logical)")
        print(f"   Channels: 1 (Red), 2 (Green), 3 (Blue)")

        self.dmx_input = EnttecDMXProInput(dmx_serial_port)
        time.sleep(0.2)  # Let device initialize
        print(f"   ✓ ENTTEC DMX USB Pro ready")

        # RGB values
        self.red = 0
        self.green = 0
        self.blue = 0
        self.target_red = 0
        self.target_green = 0
        self.target_blue = 0

        # Calculate output universes
        self.leds_per_universe = 512 // 3  # 170 LEDs per universe
        self.num_universes = (total_pixels + self.leds_per_universe - 1) // self.leds_per_universe

        # Initialize sACN sender
        print(f"\n📤 sACN Output:")
        print(f"   Destination: {output_ip}")
        print(f"   Universes: {output_universe_start}-{output_universe_start + self.num_universes - 1} ({self.num_universes} total)")
        print(f"   Total LEDs: {total_pixels}")

        self.sender = sacn.sACNsender()
        self.sender.start()

        for i in range(self.num_universes):
            univ = output_universe_start + i
            self.sender.activate_output(univ)
            self.sender[univ].multicast = False
            self.sender[univ].destination = output_ip

        print(f"   ✓ sACN sender ready")

        # Pre-allocate universe buffers (performance optimization)
        self.universe_data = {}
        for i in range(self.num_universes):
            univ = output_universe_start + i
            self.universe_data[univ] = [0] * 512

        self.running = False

        print(f"\n" + "=" * 70)

    def _update_from_dmx(self) -> int:
        """
        Update RGB values from DMX input (non-blocking).

        Returns:
            Number of DMX packets received
        """
        # Poll for new DMX data (drain buffer)
        packets_received = self.dmx_input.poll()

        # Get RGB values from channels 1-3
        dmx_red = self.dmx_input.get_channel(1)
        dmx_green = self.dmx_input.get_channel(2)
        dmx_blue = self.dmx_input.get_channel(3)

        # Hysteresis: ignore small changes (< 2%)
        if abs(dmx_red - self.target_red) > 5:
            self.target_red = dmx_red
        if abs(dmx_green - self.target_green) > 5:
            self.target_green = dmx_green
        if abs(dmx_blue - self.target_blue) > 5:
            self.target_blue = dmx_blue

        # Smooth interpolation (reduces jitter)
        self.red += (self.target_red - self.red) * 0.3
        self.green += (self.target_green - self.green) * 0.3
        self.blue += (self.target_blue - self.blue) * 0.3

        return packets_received

    def _render_frame(self):
        """Render one frame - set all LEDs to current RGB color."""
        # Clear all universe buffers
        for univ in self.universe_data:
            self.universe_data[univ] = [0] * 512

        # Set all pixels to the same color
        for pixel_idx in range(self.total_pixels):
            # Calculate universe and channel
            universe_idx = pixel_idx // self.leds_per_universe
            local_pixel_idx = pixel_idx % self.leds_per_universe
            univ = self.output_universe_start + universe_idx
            channel_offset = local_pixel_idx * 3

            # Set pixel color
            self.universe_data[univ][channel_offset] = int(self.red)
            self.universe_data[univ][channel_offset + 1] = int(self.green)
            self.universe_data[univ][channel_offset + 2] = int(self.blue)

        # Send all universe data
        for univ, data in self.universe_data.items():
            self.sender[univ].dmx_data = data

    def run(self, debug: bool = False):
        """
        Main control loop.

        Args:
            debug: Enable debug output showing real-time DMX values
        """
        print(f"\n🎨 Starting color finder (target: 60 FPS)")
        if debug:
            print(f"   🐛 DEBUG MODE: Real-time RGB values enabled")
        print(f"   Press Ctrl+C to stop\n")

        self.running = True
        frame_count = 0
        start_time = time.time()
        last_report = start_time
        last_dmx_count = 0
        target_frame_time = 1.0 / 60.0  # 60 FPS

        try:
            while self.running:
                frame_start = time.time()

                # 1. Update from DMX input (non-blocking, drain buffer)
                packets_this_frame = self._update_from_dmx()

                # 2. Render solid color
                self._render_frame()

                frame_count += 1

                # Debug output every frame (if enabled)
                if debug and frame_count % 10 == 0:  # Every 10 frames
                    r = int(self.red)
                    g = int(self.green)
                    b = int(self.blue)
                    print(f"RGB: R:{r:3d} G:{g:3d} B:{b:3d} | Color: ({r:3d}, {g:3d}, {b:3d})")

                # Status report every 5 seconds
                if frame_start - last_report >= 5.0:
                    elapsed = frame_start - start_time
                    fps = frame_count / elapsed if elapsed > 0 else 0

                    # Calculate DMX packet rate
                    dmx_packets = self.dmx_input.packet_count
                    dmx_rate = (dmx_packets - last_dmx_count) / (frame_start - last_report)
                    last_dmx_count = dmx_packets

                    # Calculate latency (time since last DMX packet)
                    dmx_latency = (time.time() - self.dmx_input.last_packet_time) * 1000  # ms

                    # Show current RGB values
                    r = int(self.red)
                    g = int(self.green)
                    b = int(self.blue)
                    rgb_str = f"RGB: ({r:3d}, {g:3d}, {b:3d})"

                    # Create color bar visualization (simple ASCII)
                    r_bar = "█" * (r // 16) if r > 0 else "·"
                    g_bar = "█" * (g // 16) if g > 0 else "·"
                    b_bar = "█" * (b // 16) if b > 0 else "·"

                    print(f"🎨 {fps:5.1f} FPS | DMX:{dmx_rate:5.1f} pkt/s | Latency:{dmx_latency:4.1f}ms | {rgb_str}")
                    print(f"   R:{r_bar}")
                    print(f"   G:{g_bar}")
                    print(f"   B:{b_bar}")
                    last_report = frame_start

                # Sleep to maintain target frame rate
                frame_time = time.time() - frame_start
                sleep_time = target_frame_time - frame_time
                if sleep_time > 0:
                    time.sleep(sleep_time)

        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user")
        finally:
            self.stop()

    def stop(self):
        """Stop the controller and clean up."""
        print("\n🛑 Stopping color finder...")
        self.running = False

        # Turn off all outputs
        for univ in self.universe_data.keys():
            self.sender[univ].dmx_data = [0] * 512

        self.sender.stop()
        self.dmx_input.close()

        print("✅ Color finder stopped")


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    # Check for debug or config flags
    debug_mode = "--debug" in sys.argv
    show_config = "--config" in sys.argv

    # Print configuration if requested
    if show_config:
        config.print_config()
        sys.exit(0)

    # Validate configuration
    issues = config.validate_config()
    if issues:
        print("\n⚠️  Configuration Issues Detected:")
        for issue in issues:
            print(f"   {issue}")
        print("\nPlease fix config.py and try again.")
        print("Run 'python3 config.py' to see full configuration.\n")
        sys.exit(1)

    # Create color finder with config values
    finder = ColorFinder(
        dmx_serial_port=config.DMX_SERIAL_PORT,
        dmx_universe=config.DMX_UNIVERSE,
        output_ip=config.WLED_IP,
        output_universe_start=config.WLED_UNIVERSE_START,
        total_pixels=config.TOTAL_PIXELS
    )

    finder.run(debug=debug_mode)
