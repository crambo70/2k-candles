#!/usr/bin/env python3
"""
DMX Fire Controller - Low Latency Integrated System

Reads DMX input from ENTTEC DMX USB Pro and outputs fire effects via sACN.
Optimized for minimal latency with single-threaded main loop.

DMX Input Channels (from console):
- Channel 1: Flicker Speed (color transition speed) (0-255)
- Channel 2: Color Shift - Yellow←→Red (0=Yellow, 127=Base, 255=Red)
- Channel 3: Sporadic Flicker (Wind Gust Effect) (0-255)
- Channel 6: Master Intensity (affects all 13 banks) (0-255)
- Channel 7-19: Flame Bank 1-13 Individual Intensity (0-255)

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
        self.sporadic_flicker = 0.0  # 0.0 (no wind gusts) to 1.0 (frequent dramatic flickers)

        # Color transition state
        self.current_color = (0, 0, 0)
        self.target_color = self._generate_fire_color()
        self.transition_start_time = time.time()
        self.transition_duration = self.rng.uniform(0.2, 1.5)

        # Brightness waxing/waning
        self.base_intensity = self.rng.uniform(0.4, 0.9)
        self.intensity_phase = self.rng.uniform(0, 6.28)
        self.intensity_speed = self.rng.uniform(0.5, 3.0)

        # Wind gust / sporadic flicker state
        self.wind_gust_active = False
        self.wind_gust_intensity = 1.0  # Multiplier for intensity during gust
        self.wind_gust_start_time = 0.0
        self.wind_gust_duration = 0.0

    def _generate_fire_color(self) -> tuple:
        """Generate a fire color based on custom base color (R:255, G:127, B:15)."""
        # Check for rare special color flash (1% chance)
        if self.rng.random() < 0.01:
            if self.rng.random() < 0.67:
                return (255, 255, 200)  # White-hot
            else:
                return (100, 150, 255)  # Blue flame

        # Normal fire color generation based on R:255, G:127, B:15
        intensity = self.rng.uniform(0.6, 1.0)

        # Red: always high, around 255 with slight variation
        red = self.rng.randint(245, 255)

        # Green: base is 127, varies based on color_shift
        # color_shift 0.0 = yellower (green goes up toward ~170-200)
        # color_shift 1.0 = redder (green goes down toward ~50-80)

        # Base green variation around 127
        green_variation = self.rng.gauss(0, 25)  # Normal distribution ±25
        base_green = 127 + green_variation

        # Apply color_shift to push green up (yellow) or down (red)
        # 0.0 = add up to +60 (yellower, max ~187)
        # 1.0 = subtract up to -60 (redder, min ~67)
        shift_amount = (self.color_shift - 0.5) * 2.0  # Map 0-1 to -1 to +1
        green_shift = -shift_amount * 60  # Negative shift makes it yellow, positive makes it red

        green = base_green + green_shift
        green = max(50, min(200, green))  # Clamp to reasonable range
        green = int(green * intensity)  # Apply intensity variation

        # Blue: base is 15, with slight variation
        blue_base = 15 + self.rng.randint(-5, 10)
        blue = max(0, min(30, blue_base))

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

            # Check if this is a special flash color (white-hot or blue flame)
            is_white_flash = (self.target_color[0] == 255 and self.target_color[1] == 255 and self.target_color[2] == 200)
            is_blue_flash = (self.target_color[0] == 100 and self.target_color[1] == 150 and self.target_color[2] == 255)

            if is_white_flash or is_blue_flash:
                # Special flash: very short duration (100-250ms)
                self.transition_duration = self.rng.uniform(0.1, 0.25)
            else:
                # Normal fire color transitions
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

        # Wind gust / sporadic flicker effect
        wind_multiplier = 1.0
        if self.sporadic_flicker > 0.01:  # Only if sporadic flicker is enabled
            # Check if we should trigger a new wind gust
            if not self.wind_gust_active:
                # Probability of triggering a gust per frame (at 60 FPS)
                # sporadic_flicker = 0.0: never
                # sporadic_flicker = 0.5: ~2% chance per frame = ~1x per second
                # sporadic_flicker = 1.0: ~5% chance per frame = ~3x per second
                gust_probability = self.sporadic_flicker * 0.05
                if self.rng.random() < gust_probability:
                    # Trigger wind gust!
                    self.wind_gust_active = True
                    self.wind_gust_start_time = current_time
                    # Gust duration: 0.05 to 0.4 seconds (quick drop and recovery)
                    self.wind_gust_duration = self.rng.uniform(0.05, 0.4)
                    # Intensity drop: 20% to 90% reduction
                    self.wind_gust_intensity = self.rng.uniform(0.1, 0.8)

            # Apply active wind gust
            if self.wind_gust_active:
                gust_elapsed = current_time - self.wind_gust_start_time
                if gust_elapsed < self.wind_gust_duration:
                    # During gust: ramp down then back up
                    gust_progress = gust_elapsed / self.wind_gust_duration
                    # Triangle wave: down to minimum at 0.5, back up at 1.0
                    if gust_progress < 0.5:
                        # Dropping (0.0 -> 0.5)
                        wind_multiplier = 1.0 - (gust_progress * 2.0) * (1.0 - self.wind_gust_intensity)
                    else:
                        # Recovering (0.5 -> 1.0)
                        wind_multiplier = self.wind_gust_intensity + ((gust_progress - 0.5) * 2.0) * (1.0 - self.wind_gust_intensity)
                else:
                    # Gust complete
                    self.wind_gust_active = False
                    wind_multiplier = 1.0

        # Apply total intensity with wind effect
        total_intensity *= wind_multiplier

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
        self.sporadic_flicker = 0.0  # 0.0 (no wind gusts) to 1.0 (frequent dramatic flickers)

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
                fire_pixel.sporadic_flicker = self.sporadic_flicker

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
                 spacing: int = 1,
                 use_multicast: bool = True,
                 output_ip_two: str = None):
        """
        Initialize the integrated controller.

        Args:
            dmx_serial_port: Serial port for ENTTEC device
            dmx_universe: Logical input universe number (for display only)
            output_ip: IP address of WLED device (used for unicast mode)
            output_universe_start: Starting sACN universe for output
            total_pixels: Total number of LEDs
            spacing: Spacing between fire pixels (every Nth pixel)
            use_multicast: True for multicast (multi-WLED), False for unicast
            output_ip_two: IP address of second WLED device (for dual unicast)
        """
        self.dmx_universe = dmx_universe
        self.output_ip = output_ip
        self.output_ip_two = output_ip_two
        self.output_universe_start = output_universe_start
        self.total_pixels = total_pixels
        self.spacing = spacing
        self.use_multicast = use_multicast

        print(f"\n🔥 DMX Fire Controller - Low Latency Edition")
        print(f"=" * 70)

        # Initialize DMX input
        print(f"\n📡 DMX Input:")
        print(f"   Port: {dmx_serial_port}")
        print(f"   Universe: {dmx_universe} (logical)")
        print(f"   Channels: 1 (Speed), 2 (Yellow←→Red), 3 (Wind), 6 (Master), 7-19 (Banks)")
        print(f"   Base Color: RGB(255, 127, 15)")

        self.dmx_input = EnttecDMXProInput(dmx_serial_port)
        time.sleep(0.2)  # Let device initialize
        print(f"   ✓ ENTTEC DMX USB Pro ready")

        # Create flame banks (13 banks, with gap between WLED boxes)
        # WLED ONE: Banks 1-7 (125 LEDs each = 875 pixels, universes 1-6)
        # GAP: 145 pixels (875-1019) - unused, between universes 6 and 7
        # WLED TWO: Banks 8-13 starting at universe 7 (pixel 1020)
        #   Banks 8-10: 125 LEDs each
        #   Banks 11-13: 150 LEDs each
        print(f"\n🔥 Flame Banks:")
        bank_sizes = [125] * 7  # WLED ONE banks
        bank_sizes += [125] * 3 + [150] * 3  # WLED TWO banks

        self.flame_banks = []
        current_pixel = 0

        for bank_id, bank_size in enumerate(bank_sizes):
            start_idx = current_pixel
            end_idx = start_idx + bank_size

            # After bank 7 (WLED ONE), skip to universe 7 (pixel 1020)
            if bank_id == 7:
                current_pixel = 1020  # Start of universe 7
                start_idx = current_pixel
                end_idx = start_idx + bank_size

            # Every Nth pixel in this range gets fire
            pixel_indices = list(range(start_idx, end_idx, spacing))
            self.flame_banks.append(FlameBank(bank_id + 1, pixel_indices))

            if bank_id == 6:
                print(f"   Bank {bank_id + 1:2d}: {len(pixel_indices):4d} flames "
                      f"(pixels {start_idx:4d}-{end_idx-1:4d}) → WLED ONE")
                print(f"   --- GAP: pixels 875-1019 (145 pixels, unused) ---")
            elif bank_id == 7:
                print(f"   Bank {bank_id + 1:2d}: {len(pixel_indices):4d} flames "
                      f"(pixels {start_idx:4d}-{end_idx-1:4d}) → WLED TWO")
            else:
                box = "WLED ONE" if bank_id < 7 else "WLED TWO"
                print(f"   Bank {bank_id + 1:2d}: {len(pixel_indices):4d} flames "
                      f"(pixels {start_idx:4d}-{end_idx-1:4d}) → {box}")

            current_pixel = end_idx

        # Global fire effect parameters (controlled by DMX channels 1-3)
        self.global_flicker_intensity = 0.5  # Default: medium flicker
        self.global_color_shift = 0.0  # Default: yellow
        self.global_sporadic_flicker = 0.0  # Default: no wind gusts

        # Master intensity (controlled by DMX channel 6)
        self.master_intensity = 1.0  # Default: full intensity
        self.target_master_intensity = 1.0

        # Calculate output universes
        self.leds_per_universe = 512 // 3  # 170 LEDs per universe
        self.num_universes = (total_pixels + self.leds_per_universe - 1) // self.leds_per_universe

        # Calculate bank split for dual-WLED setup
        # Banks 1-6 go to first group, Banks 7-13 go to second group
        num_banks = len(self.flame_banks)
        self.banks_group1 = self.flame_banks[:6]  # Banks 1-6
        self.banks_group2 = self.flame_banks[6:]  # Banks 7-13

        # Calculate pixels for each group
        group1_pixels = sum(len(b.pixel_indices) for b in self.banks_group1)
        group2_pixels = sum(len(b.pixel_indices) for b in self.banks_group2)
        group1_max_pixel = max((max(b.pixel_indices) for b in self.banks_group1), default=0)
        group2_min_pixel = min((min(b.pixel_indices) for b in self.banks_group2), default=0)

        # Calculate universe ranges
        # Group 1 starts at output_universe_start
        group1_universes = (group1_max_pixel // self.leds_per_universe) + 1
        # Group 2 starts right after group 1
        group2_start_universe = output_universe_start + group1_universes
        group2_universes = self.num_universes - group1_universes

        # Initialize sACN sender
        print(f"\n📤 sACN Output:")
        if use_multicast:
            print(f"   Mode: MULTICAST")
            print(f"   Total Universes: {output_universe_start}-{output_universe_start + self.num_universes - 1} ({self.num_universes} total)")
            print(f"   WLED ONE: Universes {output_universe_start}-{output_universe_start + group1_universes - 1} (Banks 1-6, ~{group1_pixels} flames)")
            print(f"   WLED TWO: Universes {group2_start_universe}-{output_universe_start + self.num_universes - 1} (Banks 7-13, ~{group2_pixels} flames)")
        else:
            if output_ip_two:
                print(f"   Mode: DUAL UNICAST")
                print(f"   WLED ONE: {output_ip} (Universes 1-6)")
                print(f"   WLED TWO: {output_ip_two} (Universes 7-11)")
            else:
                print(f"   Mode: UNICAST")
                print(f"   Destination: {output_ip}")
            print(f"   Universes: {output_universe_start}-{output_universe_start + self.num_universes - 1} ({self.num_universes} total)")
        print(f"   Total LEDs: {total_pixels}")

        self.sender = sacn.sACNsender()
        self.sender.start()

        for i in range(self.num_universes):
            univ = output_universe_start + i
            self.sender.activate_output(univ)
            if use_multicast:
                self.sender[univ].multicast = True
            else:
                self.sender[univ].multicast = False
                # Dual unicast: universes 1-6 to WLED ONE, 7+ to WLED TWO
                if output_ip_two and univ >= 7:
                    self.sender[univ].destination = output_ip_two
                else:
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

        # Update global fire parameters from channels 1-3
        flicker_dmx = self.dmx_input.get_channel(1)
        color_shift_dmx = self.dmx_input.get_channel(2)
        sporadic_flicker_dmx = self.dmx_input.get_channel(3)

        # Convert DMX (0-255) to 0.0-1.0
        self.global_flicker_intensity = flicker_dmx / 255.0
        self.global_color_shift = color_shift_dmx / 255.0
        self.global_sporadic_flicker = sporadic_flicker_dmx / 255.0

        # Update master intensity from channel 6
        master_dmx = self.dmx_input.get_channel(6)
        target = master_dmx / 255.0

        # Hysteresis for master intensity
        if abs(target - self.target_master_intensity) > 0.02:
            self.target_master_intensity = target

        # Smooth interpolation for master intensity
        self.master_intensity += (self.target_master_intensity - self.master_intensity) * 0.3

        # Update flame banks from channels 7-19 (13 banks)
        for i in range(13):
            dmx_value = self.dmx_input.get_channel(7 + i)
            self.flame_banks[i].set_intensity(dmx_value)

        # Apply global parameters to all banks
        for bank in self.flame_banks:
            bank.flicker_intensity = self.global_flicker_intensity
            bank.color_shift = self.global_color_shift
            bank.sporadic_flicker = self.global_sporadic_flicker

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
                # Apply master intensity
                r = int(r * self.master_intensity)
                g = int(g * self.master_intensity)
                b = int(b * self.master_intensity)

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
        target_frame_time = 1.0 / config.TARGET_FPS

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
                    speed = self.dmx_input.get_channel(1)
                    color = self.dmx_input.get_channel(2)
                    wind = self.dmx_input.get_channel(3)
                    master = self.dmx_input.get_channel(6)
                    # Show first 5 banks
                    banks = [self.dmx_input.get_channel(7 + i) for i in range(5)]
                    print(f"DMX: Speed:{speed:3d} Color:{color:3d} Wind:{wind:3d} Master:{master:3d} | "
                          f"Banks 1-5: {banks[0]:3d} {banks[1]:3d} {banks[2]:3d} {banks[3]:3d} {banks[4]:3d}")

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
                    active_banks = [b for b in self.flame_banks if b.intensity > 0.01]
                    num_active = len(active_banks)

                    # Show bank status
                    if num_active == 0:
                        bank_status = "All OFF"
                    elif num_active == len(self.flame_banks):
                        bank_status = f"All 13 ON"
                    elif num_active <= 5:
                        # Show individual banks if only a few are active
                        bank_list = ", ".join([f"B{b.bank_id}" for b in active_banks])
                        bank_status = f"{num_active} active: {bank_list}"
                    else:
                        # Just show count if many are active
                        bank_status = f"{num_active}/13 active"

                    # Show fire parameters
                    master_str = f"Master:{int(self.master_intensity*100):3d}%"
                    flicker_str = f"Speed:{int(self.global_flicker_intensity*100):3d}%"
                    # Color shift interpretation: <50% = Yellow, >50% = Red, 50% = Base
                    if self.global_color_shift < 0.4:
                        color_str = f"Color:Yellow"
                    elif self.global_color_shift > 0.6:
                        color_str = f"Color:Red"
                    else:
                        color_str = f"Color:Base"
                    wind_str = f"Wind:{int(self.global_sporadic_flicker*100):3d}%"

                    status = f"{bank_status} | {master_str} | {flicker_str} | {color_str} | {wind_str}"

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
    # Get second WLED IP if configured (for dual unicast)
    output_ip_two = getattr(config, 'WLED_IP_TWO', None)

    controller = DMXFireController(
        dmx_serial_port=config.DMX_SERIAL_PORT,
        dmx_universe=config.DMX_UNIVERSE,
        output_ip=config.WLED_IP,
        output_universe_start=config.WLED_UNIVERSE_START,
        total_pixels=config.TOTAL_PIXELS,
        spacing=config.PIXEL_SPACING,
        use_multicast=config.USE_MULTICAST,
        output_ip_two=output_ip_two
    )

    controller.run(debug=debug_mode)
