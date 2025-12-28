#!/usr/bin/env python3
"""
DMX Fire Controller - Low Latency Integrated System

Reads DMX input from ENTTEC DMX USB Pro and outputs fire effects via sACN.
Optimized for minimal latency with single-threaded main loop.

DMX Input Channels (from console):
- Channel 1-3: Flame Bank 1-3 Intensity (0-255)
- Channel 4: Flicker Intensity (0-255)
- Channel 5: Yellow→Red Shift (0-255)
- Channel 6: Blue Component (0-255)

sACN Output:
- Unicast to WLED device
- Multiple universes for large LED counts
"""

import serial
import struct
import time
import random
import sacn
from typing import Dict, List, Optional
import math
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
# ENTTEC DMX USB Pro Input Handler
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
# Fire Effect Components (from show_control.py)
# ============================================================================

class SmoothFirePixel:
    """Individual fire pixel with smooth transitions and waxing/waning intensity."""

    def __init__(self, pixel_index: int, seed: int):
        self.pixel_index = pixel_index
        self.rng = random.Random(seed)

        # Control parameters (must be set before generating colors)
        self.flicker_intensity = 0.5  # 0.0 to 1.0
        self.color_shift = 0.0  # 0.0 (yellow) to 1.0 (red)
        self.blue_amount = 0.0  # 0.0 (no blue) to 1.0 (max blue/white-hot)

        # Color transition state
        self.current_color = (0, 0, 0)
        self.target_color = self._generate_fire_color()
        self.transition_start_time = time.time()
        self.transition_duration = self.rng.uniform(0.2, 1.5)

        # Brightness waxing/waning
        self.base_intensity = self.rng.uniform(0.4, 0.9)
        self.intensity_phase = self.rng.uniform(0, 6.28)
        self.intensity_speed = self.rng.uniform(0.5, 3.0)

    def _generate_fire_color(self) -> tuple:
        """Generate a fire color using algorithm based on real candle physics."""
        # Check for rare special color flash (1% chance)
        if self.rng.random() < 0.01:
            if self.rng.random() < 0.67:
                return (255, 255, 200)  # White-hot
            else:
                return (100, 150, 255)  # Blue flame

        # Normal fire color generation
        intensity = self.rng.uniform(0.6, 1.0)

        # Red: always high (90-100%)
        red_base = self.rng.uniform(0.90, 1.0)
        red = int(255 * red_base)

        # Green: determines the color (yellow vs red-orange)
        # Base green intensity with normal distribution
        green_intensity = self.rng.gauss(0.55, 0.15)
        green_intensity = max(0.3, min(0.8, green_intensity))

        # Apply color shift: 0.0 = yellow (high green), 1.0 = red (low green)
        # Shift reduces green, making it more red
        green_intensity = green_intensity * (1.0 - self.color_shift * 0.7)
        green = int(255 * green_intensity * math.pow(intensity, 1.1))

        # Blue: independent control for white-hot appearance
        # blue_amount 0.0 = no blue, 1.0 = max blue (white-hot)
        base_blue = self.rng.uniform(30, 100)  # Random blue component for variation
        blue = int(base_blue * self.blue_amount)

        return (red, green, blue)

    def lerp_color(self, c1: tuple, c2: tuple, t: float) -> tuple:
        """Linear interpolation between two colors."""
        t = max(0.0, min(1.0, t))
        r = int(c1[0] + (c2[0] - c1[0]) * t)
        g = int(c1[1] + (c2[1] - c1[1]) * t)
        b = int(c1[2] + (c2[2] - c1[2]) * t)
        return (r, g, b)

    def update(self, current_time: float) -> tuple:
        """Update the pixel color with smooth transitions."""
        # Check if we need a new target color
        elapsed = current_time - self.transition_start_time
        if elapsed >= self.transition_duration:
            # Transition complete, pick new target
            self.current_color = self.target_color
            self.target_color = self._generate_fire_color()
            self.transition_start_time = current_time

            # Random transition speed influenced by flicker_intensity
            # Higher flicker = faster, more dramatic transitions
            # Lower flicker = slower, more gentle transitions
            transition_type = self.rng.random()
            if transition_type < 0.3:
                # Quick flicker
                base_range = (0.05, 0.2)
            elif transition_type < 0.7:
                # Medium transition
                base_range = (0.3, 0.8)
            else:
                # Slow slide
                base_range = (1.0, 2.5)

            # Scale duration by flicker intensity (inverted: high flicker = short duration)
            duration = self.rng.uniform(*base_range)
            # Flicker intensity: 0.0 = 2x slower, 0.5 = normal, 1.0 = 2x faster
            speed_multiplier = 2.0 - self.flicker_intensity
            self.transition_duration = duration * speed_multiplier

        # Calculate interpolation progress
        t = elapsed / self.transition_duration if self.transition_duration > 0 else 1.0

        # Smooth easing (smoothstep)
        t = t * t * (3.0 - 2.0 * t)

        # Interpolate between current and target color
        r, g, b = self.lerp_color(self.current_color, self.target_color, t)

        # Apply waxing/waning intensity (sine wave)
        self.intensity_phase += self.intensity_speed * 0.01
        intensity_variation = (math.sin(self.intensity_phase) + 1.0) / 2.0

        # Blend base intensity with variation
        total_intensity = self.base_intensity * (0.6 + 0.4 * intensity_variation)

        r = int(r * total_intensity)
        g = int(g * total_intensity)
        b = int(b * total_intensity)

        return (r, g, b)


class FlameBank:
    """A controllable bank of fire pixels."""

    def __init__(self, bank_id: int, pixel_indices: List[int]):
        self.bank_id = bank_id
        self.pixel_indices = pixel_indices
        self.intensity = 0.0  # 0.0 to 1.0
        self.target_intensity = 0.0
        self.fire_pixels = []

        # Global fire parameters (shared by all pixels)
        self.flicker_intensity = 0.5  # 0.0 to 1.0
        self.color_shift = 0.0  # 0.0 (yellow) to 1.0 (red)
        self.blue_amount = 0.0  # 0.0 (no blue) to 1.0 (white-hot)

        # Create fire pixel objects
        for idx in pixel_indices:
            self.fire_pixels.append(SmoothFirePixel(idx, seed=idx))

    def set_intensity(self, dmx_value: int):
        """Set bank intensity from DMX value (0-255) with smoothing."""
        # Convert to 0.0-1.0
        target = dmx_value / 255.0

        # Hysteresis: ignore small changes (< 2%)
        diff = abs(target - self.target_intensity)
        if diff > 0.02:
            self.target_intensity = target

        # Smooth interpolation (reduces flickering)
        self.intensity += (self.target_intensity - self.intensity) * 0.3

    def update(self, current_time: float) -> Dict[int, tuple]:
        """
        Update all pixels in this bank.

        Returns:
            Dict mapping pixel_index -> (r, g, b)
        """
        pixel_colors = {}

        if self.intensity <= 0:
            # Bank is off
            for pixel_idx in self.pixel_indices:
                pixel_colors[pixel_idx] = (0, 0, 0)
        else:
            # Update each fire pixel and apply intensity
            for fire_pixel in self.fire_pixels:
                # Apply global fire parameters to each pixel
                fire_pixel.flicker_intensity = self.flicker_intensity
                fire_pixel.color_shift = self.color_shift
                fire_pixel.blue_amount = self.blue_amount

                r, g, b = fire_pixel.update(current_time)
                # Apply bank intensity
                r = int(r * self.intensity)
                g = int(g * self.intensity)
                b = int(b * self.intensity)
                pixel_colors[fire_pixel.pixel_index] = (r, g, b)

        return pixel_colors


# WindEffect class removed - replaced with flicker_intensity and color_shift controls


# ============================================================================
# Main Integrated Controller
# ============================================================================

class DMXFireController:
    """
    Integrated low-latency controller.

    DMX Input → Fire Effects Processing → sACN Output
    """

    def __init__(self,
                 dmx_serial_port: str,
                 dmx_universe: int,
                 output_ip: str,
                 output_universe_start: int,
                 total_pixels: int,
                 spacing: int = 51):
        """
        Initialize the integrated controller.

        Args:
            dmx_serial_port: Serial port for ENTTEC device
            dmx_universe: Logical input universe number (for display only)
            output_ip: IP address of WLED device
            output_universe_start: Starting sACN universe for output
            total_pixels: Total number of LEDs
            spacing: Spacing between fire pixels (every Nth pixel)
        """
        self.dmx_universe = dmx_universe
        self.output_ip = output_ip
        self.output_universe_start = output_universe_start
        self.total_pixels = total_pixels
        self.spacing = spacing

        print(f"\n🔥 DMX Fire Controller - Low Latency Edition")
        print(f"=" * 70)

        # Initialize DMX input
        print(f"\n📡 DMX Input:")
        print(f"   Port: {dmx_serial_port}")
        print(f"   Universe: {dmx_universe} (logical)")
        print(f"   Channels: 1-3 (Banks), 4 (Flicker), 5 (Yellow→Red), 6 (Blue)")

        self.dmx_input = EnttecDMXProInput(dmx_serial_port)
        time.sleep(0.2)  # Let device initialize
        print(f"   ✓ ENTTEC DMX USB Pro ready")

        # Create flame banks (3 banks, evenly divided)
        print(f"\n🔥 Flame Banks:")
        pixels_per_bank = total_pixels // 3
        self.flame_banks = []

        for bank_id in range(3):
            start_idx = bank_id * pixels_per_bank
            end_idx = start_idx + pixels_per_bank if bank_id < 2 else total_pixels
            # Every Nth pixel in this range gets fire
            pixel_indices = list(range(start_idx, end_idx, spacing))
            self.flame_banks.append(FlameBank(bank_id + 1, pixel_indices))
            print(f"   Bank {bank_id + 1}: {len(pixel_indices)} flames "
                  f"(pixels {start_idx:4d}-{end_idx-1:4d}, every {spacing}th)")

        # Global fire effect parameters (controlled by DMX channels 4-6)
        self.global_flicker_intensity = 0.5  # Default: medium flicker
        self.global_color_shift = 0.0  # Default: yellow
        self.global_blue_amount = 0.0  # Default: no blue

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
        Update control parameters from DMX input (non-blocking).

        Returns:
            Number of DMX packets received
        """
        # Poll for new DMX data (drain buffer)
        packets_received = self.dmx_input.poll()

        # Update flame banks from channels 1-3
        for i in range(3):
            dmx_value = self.dmx_input.get_channel(i + 1)
            self.flame_banks[i].set_intensity(dmx_value)

        # Update global fire parameters from channels 4-6
        flicker_dmx = self.dmx_input.get_channel(4)
        color_shift_dmx = self.dmx_input.get_channel(5)
        blue_dmx = self.dmx_input.get_channel(6)

        # Convert DMX (0-255) to 0.0-1.0
        self.global_flicker_intensity = flicker_dmx / 255.0
        self.global_color_shift = color_shift_dmx / 255.0
        self.global_blue_amount = blue_dmx / 255.0

        # Apply to all banks
        for bank in self.flame_banks:
            bank.flicker_intensity = self.global_flicker_intensity
            bank.color_shift = self.global_color_shift
            bank.blue_amount = self.global_blue_amount

        return packets_received

    def _render_frame(self, current_time: float):
        """Render one frame of fire effects."""
        # Clear all universe buffers
        for univ in self.universe_data:
            self.universe_data[univ] = [0] * 512

        # Update all flame banks
        for bank in self.flame_banks:
            pixel_colors = bank.update(current_time)

            for pixel_idx, (r, g, b) in pixel_colors.items():
                # Calculate universe and channel
                universe_idx = pixel_idx // self.leds_per_universe
                local_pixel_idx = pixel_idx % self.leds_per_universe
                univ = self.output_universe_start + universe_idx
                channel_offset = local_pixel_idx * 3

                # Set pixel color
                self.universe_data[univ][channel_offset] = r
                self.universe_data[univ][channel_offset + 1] = g
                self.universe_data[univ][channel_offset + 2] = b

        # Send all universe data
        for univ, data in self.universe_data.items():
            self.sender[univ].dmx_data = data

    def run(self, debug: bool = False):
        """
        Main low-latency control loop.

        Args:
            debug: Enable debug output showing real-time DMX values
        """
        print(f"\n🎭 Starting main control loop (target: 60 FPS)")
        if debug:
            print(f"   🐛 DEBUG MODE: Real-time DMX values enabled")
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

                # 2. Render fire effects
                self._render_frame(frame_start)

                frame_count += 1

                # Debug output every frame (if enabled)
                if debug and frame_count % 10 == 0:  # Every 10 frames
                    ch1 = self.dmx_input.get_channel(1)
                    ch2 = self.dmx_input.get_channel(2)
                    ch3 = self.dmx_input.get_channel(3)
                    ch4 = self.dmx_input.get_channel(4)
                    ch5 = self.dmx_input.get_channel(5)
                    ch6 = self.dmx_input.get_channel(6)
                    print(f"DMX: Ch1:{ch1:3d} Ch2:{ch2:3d} Ch3:{ch3:3d} Ch4:{ch4:3d} Ch5:{ch5:3d} Ch6:{ch6:3d} | "
                          f"Banks: {self.flame_banks[0].intensity:.2f} {self.flame_banks[1].intensity:.2f} "
                          f"{self.flame_banks[2].intensity:.2f}")

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

                    # Show active banks (with threshold to avoid noise)
                    active_banks = [f"B{b.bank_id}:{int(b.intensity*100):3d}%"
                                   for b in self.flame_banks if b.intensity > 0.01]  # 1% threshold

                    # Show fire parameters
                    flicker_str = f"Flicker:{int(self.global_flicker_intensity*100):3d}%"
                    color_str = f"Y→R:{int(self.global_color_shift*100):3d}%"
                    blue_str = f"Blue:{int(self.global_blue_amount*100):3d}%"

                    status = " ".join(active_banks) if active_banks else "All OFF"
                    status += f" | {flicker_str} | {color_str} | {blue_str}"

                    print(f"🔥 {fps:5.1f} FPS | DMX:{dmx_rate:5.1f} pkt/s | Latency:{dmx_latency:4.1f}ms | {status}")
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
        print("\n🛑 Stopping controller...")
        self.running = False

        # Turn off all outputs
        for univ in self.universe_data.keys():
            self.sender[univ].dmx_data = [0] * 512

        self.sender.stop()
        self.dmx_input.close()

        print("✅ Controller stopped")


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

    # Create controller with config values
    controller = DMXFireController(
        dmx_serial_port=config.DMX_SERIAL_PORT,
        dmx_universe=config.DMX_UNIVERSE,
        output_ip=config.WLED_IP,
        output_universe_start=config.WLED_UNIVERSE_START,
        total_pixels=config.TOTAL_PIXELS,
        spacing=config.PIXEL_SPACING
    )

    controller.run(debug=debug_mode)
