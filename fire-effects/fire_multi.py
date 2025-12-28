#!/usr/bin/env python3
"""Flickering fire effect on every 9th pixel with independent animation."""

import time
import random
import sacn

class FirePixel:
    """Individual fire pixel with its own state and timing."""

    def __init__(self, pixel_index: int, seed: int):
        """
        Initialize a fire pixel.

        Args:
            pixel_index: The pixel index (0-1023)
            seed: Random seed for this pixel's behavior
        """
        self.pixel_index = pixel_index
        self.rng = random.Random(seed)  # Independent random generator

        # Fire color palette with weights
        self.fire_colors = [
            # (R, G, B, weight)
            (255, 60, 0, 20),    # Deep orange-red (common)
            (255, 100, 0, 18),   # Orange (common)
            (255, 140, 0, 15),   # Light orange (fairly common)
            (255, 200, 0, 12),   # Yellow-orange (less common)
            (200, 40, 0, 10),    # Dark red (less common)
            (255, 255, 0, 8),    # Yellow (occasional)
            (255, 255, 100, 5),  # Pale yellow (rare)
            (255, 255, 200, 2),  # White-hot (very rare)
            (100, 150, 255, 1),  # Blue flame (extremely rare)
        ]

        # Create weighted list for random selection
        self.weighted_colors = []
        for color in self.fire_colors:
            r, g, b, weight = color
            self.weighted_colors.extend([(r, g, b)] * weight)

        # Each pixel has its own update interval
        self.next_update = time.time() + self.rng.uniform(0, 0.1)
        self.update_interval = self.rng.uniform(0.02, 0.08)

        # Each pixel has a base intensity (some burn brighter than others)
        self.base_intensity = self.rng.uniform(0.5, 1.0)  # 50-100% base brightness

        # Current color
        self.current_color = (0, 0, 0)

    def update(self, current_time: float) -> tuple:
        """
        Update the pixel color if it's time.

        Args:
            current_time: Current timestamp

        Returns:
            Tuple of (R, G, B) color values
        """
        if current_time >= self.next_update:
            # Pick a random fire color
            r, g, b = self.rng.choice(self.weighted_colors)

            # Add flicker intensity on top of base intensity
            flicker = self.rng.uniform(0.6, 1.0)  # 60-100% flicker
            total_intensity = self.base_intensity * flicker
            r = int(r * total_intensity)
            g = int(g * total_intensity)
            b = int(b * total_intensity)

            self.current_color = (r, g, b)

            # Set next update time with variable interval
            self.update_interval = self.rng.uniform(0.02, 0.08)
            self.next_update = current_time + self.update_interval

        return self.current_color


def multi_fire(wled_ip: str = "192.168.4.74",
               start_universe: int = 1,
               led_count: int = 1024,
               spacing: int = 9,
               duration: int = 60):
    """
    Create flickering fire effect on every Nth pixel.

    Args:
        wled_ip: IP address of WLED device
        start_universe: Starting DMX universe number
        led_count: Total number of LEDs
        spacing: Space between fire pixels (every Nth pixel)
        duration: How long to run the effect in seconds
    """

    # Calculate which pixels will have fire
    fire_pixel_indices = list(range(0, led_count, spacing))
    num_fire_pixels = len(fire_pixel_indices)

    print(f"🔥 Multi-pixel fire effect")
    print(f"   Total LEDs: {led_count}")
    print(f"   Fire pixels: {num_fire_pixels} (every {spacing}th pixel)")
    print(f"   Fire pixel indices: {fire_pixel_indices[:10]}... (showing first 10)")
    print(f"   IP: {wled_ip}")
    print(f"   Duration: {duration}s")
    print(f"   Press Ctrl+C to stop early\n")

    # Create fire pixel objects with different seeds
    fire_pixels = []
    for idx, pixel_idx in enumerate(fire_pixel_indices):
        fire_pixels.append(FirePixel(pixel_idx, seed=pixel_idx))

    # Calculate universes needed
    channels_per_led = 3
    channels_per_universe = 512
    leds_per_universe = channels_per_universe // channels_per_led  # 170 LEDs
    num_universes = (led_count + leds_per_universe - 1) // leds_per_universe

    print(f"   Universes: {num_universes} (universe {start_universe}-{start_universe + num_universes - 1})\n")

    # Initialize sACN sender
    sender = sacn.sACNsender()
    sender.start()

    # Activate all needed universes
    for i in range(num_universes):
        univ = start_universe + i
        sender.activate_output(univ)
        sender[univ].multicast = False
        sender[univ].destination = wled_ip

    # Prepare DMX buffers for all universes
    universe_data = {}
    for i in range(num_universes):
        univ = start_universe + i
        universe_data[univ] = [0] * 512

    start_time = time.time()
    frame_count = 0
    last_report = start_time

    try:
        while time.time() - start_time < duration:
            current_time = time.time()

            # Update all fire pixels
            for fire_pixel in fire_pixels:
                r, g, b = fire_pixel.update(current_time)

                # Calculate which universe and channel this pixel belongs to
                pixel_idx = fire_pixel.pixel_index
                universe_idx = pixel_idx // leds_per_universe
                local_pixel_idx = pixel_idx % leds_per_universe

                univ = start_universe + universe_idx
                channel_offset = local_pixel_idx * channels_per_led

                # Set the pixel color in the appropriate universe buffer
                universe_data[univ][channel_offset] = r
                universe_data[univ][channel_offset + 1] = g
                universe_data[univ][channel_offset + 2] = b

            # Send all universe data
            for univ, data in universe_data.items():
                sender[univ].dmx_data = data

            frame_count += 1

            # Progress report every 2 seconds
            if current_time - last_report >= 2.0:
                elapsed = current_time - start_time
                fps = frame_count / elapsed if elapsed > 0 else 0
                print(f"🔥 {elapsed:.1f}s - {num_fire_pixels} pixels flickering @ {fps:.1f} FPS")
                last_report = current_time

            # Small sleep to prevent CPU spinning
            time.sleep(0.001)

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")

    finally:
        # Turn off all pixels
        for univ in universe_data.keys():
            sender[univ].dmx_data = [0] * 512
        sender.stop()

        elapsed = time.time() - start_time
        fps = frame_count / elapsed if elapsed > 0 else 0
        print(f"\n✅ Done!")
        print(f"   Total frames: {frame_count}")
        print(f"   Average FPS: {fps:.1f}")
        print(f"   Elapsed time: {elapsed:.1f}s")

if __name__ == "__main__":
    # Every 17th pixel gets fire
    multi_fire(
        wled_ip="192.168.4.74",
        start_universe=1,
        led_count=1024,
        spacing=17,
        duration=60  # Run for 60 seconds
    )
