#!/usr/bin/env python3
"""
Fire Effects Show Control System

Listens for incoming DMX/sACN control signals and manages fire effects accordingly.

Control Universe Setup (example: Universe 100):
- Channel 1-4: Flame Bank 1-4 Intensity (0-255, 0=off, 255=full)
- Channel 5: Wind Effect Intensity (0-255)
- Channel 6: Wind Speed (0-255, affects how fast wind moves)
- Channel 7-8: Reserved for future effects

Flame Banks divide the 1024 LEDs into controllable zones.
"""

import sacn
import time
import threading
from typing import Dict, List, Optional
from fire_smooth import SmoothFirePixel


class FlameBank:
    """A controllable bank of fire pixels."""

    def __init__(self, bank_id: int, pixel_indices: List[int]):
        """
        Initialize a flame bank.

        Args:
            bank_id: Bank identifier (1-4)
            pixel_indices: List of pixel indices in this bank
        """
        self.bank_id = bank_id
        self.pixel_indices = pixel_indices
        self.intensity = 0.0  # 0.0 to 1.0
        self.fire_pixels = []

        # Create fire pixel objects
        for idx in pixel_indices:
            self.fire_pixels.append(SmoothFirePixel(idx, seed=idx))

    def set_intensity(self, dmx_value: int):
        """Set bank intensity from DMX value (0-255)."""
        self.intensity = dmx_value / 255.0

    def update(self, current_time: float) -> Dict[int, tuple]:
        """
        Update all pixels in this bank.

        Returns:
            Dict mapping pixel_index -> (r, g, b)
        """
        pixel_colors = {}

        if self.intensity <= 0:
            # Bank is off, return black for all pixels
            for pixel_idx in self.pixel_indices:
                pixel_colors[pixel_idx] = (0, 0, 0)
        else:
            # Update each fire pixel and apply intensity
            for fire_pixel in self.fire_pixels:
                r, g, b = fire_pixel.update(current_time)
                # Apply bank intensity
                r = int(r * self.intensity)
                g = int(g * self.intensity)
                b = int(b * self.intensity)
                pixel_colors[fire_pixel.pixel_index] = (r, g, b)

        return pixel_colors


class WindEffect:
    """Simulates wind gusts moving across flame banks."""

    def __init__(self):
        self.intensity = 0.0  # 0.0 to 1.0
        self.speed = 0.5  # 0.0 to 1.0
        self.position = 0.0  # Current wind position (0.0 to 1.0 across strip)
        self.last_update = time.time()

    def set_intensity(self, dmx_value: int):
        """Set wind intensity from DMX value (0-255)."""
        self.intensity = dmx_value / 255.0

    def set_speed(self, dmx_value: int):
        """Set wind speed from DMX value (0-255)."""
        self.speed = dmx_value / 255.0

    def get_modifier(self, pixel_index: int, total_pixels: int) -> float:
        """
        Get wind intensity modifier for a specific pixel.

        Args:
            pixel_index: The pixel index
            total_pixels: Total number of pixels in strip

        Returns:
            Modifier value (0.0 to 1.0) - multiplies with base intensity
        """
        if self.intensity <= 0:
            return 1.0  # No wind effect

        # Update wind position based on speed
        current_time = time.time()
        elapsed = current_time - self.last_update
        self.last_update = current_time

        # Wind moves across the strip
        self.position += self.speed * elapsed * 0.5  # 0.5 = base speed scaling
        if self.position > 1.0:
            self.position = 0.0

        # Calculate how close this pixel is to the wind position
        pixel_position = pixel_index / total_pixels
        distance = abs(pixel_position - self.position)

        # Wind has a "width" - affects nearby pixels
        wind_width = 0.1 + (self.intensity * 0.2)  # 10-30% of strip width

        if distance < wind_width:
            # Within wind zone - reduce intensity (flicker down)
            proximity = 1.0 - (distance / wind_width)
            reduction = proximity * self.intensity * 0.7  # Max 70% reduction
            return 1.0 - reduction

        return 1.0  # Outside wind zone


class FireShowControl:
    """Main show control system for fire effects."""

    def __init__(self,
                 control_universe: int = 100,
                 output_ip: str = "192.168.4.74",
                 output_universe_start: int = 1,
                 total_pixels: int = 1024):
        """
        Initialize show control.

        Args:
            control_universe: DMX universe to listen for control signals
            output_ip: IP address of WLED device
            output_universe_start: Starting universe for output
            total_pixels: Total number of LEDs
        """
        self.control_universe = control_universe
        self.output_ip = output_ip
        self.output_universe_start = output_universe_start
        self.total_pixels = total_pixels

        # Create flame banks (4 banks, evenly divided)
        pixels_per_bank = total_pixels // 4
        self.flame_banks = []

        for bank_id in range(4):
            start_idx = bank_id * pixels_per_bank
            end_idx = start_idx + pixels_per_bank if bank_id < 3 else total_pixels
            # Every 51st pixel in this range gets fire
            pixel_indices = list(range(start_idx, end_idx, 51))
            self.flame_banks.append(FlameBank(bank_id + 1, pixel_indices))
            print(f"  Bank {bank_id + 1}: {len(pixel_indices)} flames "
                  f"(pixels {start_idx}-{end_idx-1}, every 51st)")

        # Wind effect
        self.wind = WindEffect()

        # sACN receiver for control
        self.receiver = sacn.sACNreceiver()
        self.receiver.start()
        self.receiver.join_multicast(control_universe)

        # Register callback for control universe
        @self.receiver.listen_on('universe', universe=control_universe)
        def control_callback(packet):
            self._handle_control_dmx(packet.dmxData)

        # sACN sender for output
        self.sender = sacn.sACNsender()
        self.sender.start()

        # Calculate output universes needed
        leds_per_universe = 512 // 3  # 170 LEDs per universe
        num_universes = (total_pixels + leds_per_universe - 1) // leds_per_universe

        for i in range(num_universes):
            univ = output_universe_start + i
            self.sender.activate_output(univ)
            self.sender[univ].multicast = False
            self.sender[univ].destination = output_ip

        self.num_universes = num_universes
        self.running = False
        self.render_thread = None

    def _handle_control_dmx(self, dmx_data: list):
        """Handle incoming DMX control data."""
        # Channels are 1-indexed in DMX, but 0-indexed in array
        # Channel 1-4: Flame banks
        for i in range(4):
            if len(dmx_data) > i:
                self.flame_banks[i].set_intensity(dmx_data[i])

        # Channel 5: Wind intensity
        if len(dmx_data) > 4:
            self.wind.set_intensity(dmx_data[4])

        # Channel 6: Wind speed
        if len(dmx_data) > 5:
            self.wind.set_speed(dmx_data[5])

    def _render_loop(self):
        """Main render loop - updates and outputs fire effects."""
        leds_per_universe = 512 // 3

        # Prepare universe buffers
        universe_data = {}
        for i in range(self.num_universes):
            univ = self.output_universe_start + i
            universe_data[univ] = [0] * 512

        frame_count = 0
        start_time = time.time()
        last_report = start_time

        while self.running:
            current_time = time.time()

            # Clear all universe buffers
            for univ in universe_data:
                universe_data[univ] = [0] * 512

            # Update all flame banks
            for bank in self.flame_banks:
                pixel_colors = bank.update(current_time)

                for pixel_idx, (r, g, b) in pixel_colors.items():
                    # Apply wind effect
                    wind_modifier = self.wind.get_modifier(pixel_idx, self.total_pixels)
                    r = int(r * wind_modifier)
                    g = int(g * wind_modifier)
                    b = int(b * wind_modifier)

                    # Calculate universe and channel
                    universe_idx = pixel_idx // leds_per_universe
                    local_pixel_idx = pixel_idx % leds_per_universe
                    univ = self.output_universe_start + universe_idx
                    channel_offset = local_pixel_idx * 3

                    # Set pixel color
                    universe_data[univ][channel_offset] = r
                    universe_data[univ][channel_offset + 1] = g
                    universe_data[univ][channel_offset + 2] = b

            # Send all universe data
            for univ, data in universe_data.items():
                self.sender[univ].dmx_data = data

            frame_count += 1

            # Status report every 5 seconds
            if current_time - last_report >= 5.0:
                elapsed = current_time - start_time
                fps = frame_count / elapsed if elapsed > 0 else 0

                # Show active banks
                active_banks = [f"Bank{b.bank_id}:{int(b.intensity*100)}%"
                               for b in self.flame_banks if b.intensity > 0]
                wind_str = f"Wind:{int(self.wind.intensity*100)}%@{int(self.wind.speed*100)}%" if self.wind.intensity > 0 else ""

                status = " | ".join(active_banks) if active_banks else "All off"
                if wind_str:
                    status += f" | {wind_str}"

                print(f"🔥 {fps:.1f} FPS | {status}")
                last_report = current_time

            # Target ~60 FPS
            time.sleep(1.0 / 60.0)

    def start(self):
        """Start the show control system."""
        print(f"\n🎭 Fire Effects Show Control Starting")
        print(f"   Control Universe: {self.control_universe}")
        print(f"   Output: {self.output_ip} (universes {self.output_universe_start}-{self.output_universe_start + self.num_universes - 1})")
        print(f"   Total Pixels: {self.total_pixels}")
        print(f"\n   Flame Banks:")

        self.running = True
        self.render_thread = threading.Thread(target=self._render_loop, daemon=True)
        self.render_thread.start()

        print(f"\n   Control Channels (Universe {self.control_universe}):")
        print(f"   - Ch 1-4: Flame Bank 1-4 Intensity (0-255)")
        print(f"   - Ch 5: Wind Effect Intensity (0-255)")
        print(f"   - Ch 6: Wind Speed (0-255)")
        print(f"\n🎭 Show Control Running! Press Ctrl+C to stop\n")

    def stop(self):
        """Stop the show control system."""
        print("\n🛑 Stopping show control...")
        self.running = False
        if self.render_thread:
            self.render_thread.join(timeout=2.0)

        # Turn off all outputs
        for i in range(self.num_universes):
            univ = self.output_universe_start + i
            self.sender[univ].dmx_data = [0] * 512

        self.sender.stop()
        self.receiver.stop()
        print("✅ Show control stopped")


if __name__ == "__main__":
    show = FireShowControl(
        control_universe=100,
        output_ip="192.168.4.74",
        output_universe_start=1,
        total_pixels=1024
    )

    try:
        show.start()
        # Keep running until interrupted
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        show.stop()
