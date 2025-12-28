#!/usr/bin/env python3
"""Smooth flickering fire effect with waxing/waning brightness."""

import time
import random
import sacn

class SmoothFirePixel:
    """Individual fire pixel with smooth transitions and waxing/waning intensity."""

    def __init__(self, pixel_index: int, seed: int):
        """
        Initialize a fire pixel.

        Args:
            pixel_index: The pixel index (0-1023)
            seed: Random seed for this pixel's behavior
        """
        self.pixel_index = pixel_index
        self.rng = random.Random(seed)

        # Use algorithm-based colors inspired by real candle physics
        # Rather than discrete palette, we'll generate colors dynamically
        # based on intensity using the relationship: green fades faster than red
        self.use_algorithmic_color = True

        # Rare special colors (white-hot and blue flame flashes)
        self.special_colors = [
            (255, 255, 200, 2),  # White-hot (very rare)
            (100, 150, 255, 1),  # Blue flame (extremely rare)
        ]

        # Track when to use special colors
        self.special_color_active = False
        self.special_color = None
        self.special_color_end_time = 0

        # Color transition state
        self.current_color = (0, 0, 0)
        self.target_color = self._generate_fire_color()
        self.transition_start_time = time.time()
        self.transition_duration = self.rng.uniform(0.2, 1.5)  # Varies: quick to slow

        # Brightness waxing/waning (uses sine-like oscillation)
        self.base_intensity = self.rng.uniform(0.4, 0.9)  # Base brightness level
        self.intensity_phase = self.rng.uniform(0, 6.28)  # Random starting phase
        self.intensity_speed = self.rng.uniform(0.5, 3.0)  # How fast it oscillates

    def _generate_fire_color(self) -> tuple:
        """
        Generate a fire color using algorithm based on real candle physics.
        Red: 75-100% base, Green: varies based on intensity, Blue: 0 (except rare flashes)

        Returns:
            Tuple of (R, G, B)
        """
        import math

        # Check for rare special color flash (1% chance)
        if self.rng.random() < 0.01:
            # Pick white-hot or blue flame
            if self.rng.random() < 0.67:  # 2/3 chance white, 1/3 blue
                return (255, 255, 200)  # White-hot
            else:
                return (100, 150, 255)  # Blue flame

        # Normal fire color generation
        # Most common: orange-yellow
        # Range: red-orange (darkest) -> orange-yellow (most common) -> yellow (brightest)
        intensity = self.rng.uniform(0.6, 1.0)

        # Red: always high (90-100%)
        red_base = self.rng.uniform(0.90, 1.0)
        red = int(255 * red_base)

        # Green: determines the color
        # Use normal distribution centered on orange-yellow
        # Most common: ~50-60% green (orange-yellow)
        # Occasional: 30-40% (red-orange) or 70-80% (yellow)
        green_intensity = self.rng.gauss(0.55, 0.15)  # Normal dist, mean=55%, std=15%
        green_intensity = max(0.3, min(0.8, green_intensity))  # Clamp to 30-80%
        green = int(255 * green_intensity * math.pow(intensity, 1.1))

        # Blue: none (realistic candle has no blue)
        blue = 0

        return (red, green, blue)

    def lerp_color(self, c1: tuple, c2: tuple, t: float) -> tuple:
        """
        Linear interpolation between two colors.

        Args:
            c1: Starting color (R, G, B)
            c2: Target color (R, G, B)
            t: Interpolation factor (0.0 to 1.0)

        Returns:
            Interpolated color (R, G, B)
        """
        t = max(0.0, min(1.0, t))  # Clamp to [0, 1]
        r = int(c1[0] + (c2[0] - c1[0]) * t)
        g = int(c1[1] + (c2[1] - c1[1]) * t)
        b = int(c1[2] + (c2[2] - c1[2]) * t)
        return (r, g, b)

    def update(self, current_time: float) -> tuple:
        """
        Update the pixel color with smooth transitions.

        Args:
            current_time: Current timestamp

        Returns:
            Tuple of (R, G, B) color values
        """
        # Check if we need a new target color
        elapsed = current_time - self.transition_start_time
        if elapsed >= self.transition_duration:
            # Transition complete, pick new target
            self.current_color = self.target_color
            self.target_color = self._generate_fire_color()
            self.transition_start_time = current_time

            # Random transition speed: some quick flickers, some slow slides
            transition_type = self.rng.random()
            if transition_type < 0.3:  # 30% quick flicker
                self.transition_duration = self.rng.uniform(0.05, 0.2)
            elif transition_type < 0.7:  # 40% medium transition
                self.transition_duration = self.rng.uniform(0.3, 0.8)
            else:  # 30% slow slide
                self.transition_duration = self.rng.uniform(1.0, 2.5)

        # Calculate interpolation progress
        t = elapsed / self.transition_duration if self.transition_duration > 0 else 1.0

        # Smooth easing (ease-in-out)
        t = t * t * (3.0 - 2.0 * t)  # Smoothstep function

        # Interpolate between current and target color
        r, g, b = self.lerp_color(self.current_color, self.target_color, t)

        # Apply waxing/waning intensity
        # Use sine wave for smooth oscillation
        import math
        self.intensity_phase += self.intensity_speed * 0.01  # Increment phase
        intensity_variation = (math.sin(self.intensity_phase) + 1.0) / 2.0  # 0.0 to 1.0

        # Blend base intensity with variation
        total_intensity = self.base_intensity * (0.6 + 0.4 * intensity_variation)

        r = int(r * total_intensity)
        g = int(g * total_intensity)
        b = int(b * total_intensity)

        return (r, g, b)


def smooth_fire(wled_ip: str = "192.168.4.74",
                start_universe: int = 1,
                led_count: int = 1024,
                spacing: int = 17,
                duration: int = 60):
    """
    Create smooth flickering fire effect on every Nth pixel.

    Args:
        wled_ip: IP address of WLED device
        start_universe: Starting DMX universe number
        led_count: Total number of LEDs
        spacing: Space between fire pixels
        duration: How long to run the effect in seconds
    """

    # Calculate fire pixels
    fire_pixel_indices = list(range(0, led_count, spacing))
    num_fire_pixels = len(fire_pixel_indices)

    print(f"🔥 Smooth fire effect")
    print(f"   Total LEDs: {led_count}")
    print(f"   Fire pixels: {num_fire_pixels} (every {spacing}th pixel)")
    print(f"   IP: {wled_ip}")
    print(f"   Duration: {duration}s")
    print(f"   Features: Smooth transitions, waxing/waning intensity")
    print(f"   Press Ctrl+C to stop early\n")

    # Create fire pixels with different seeds
    fire_pixels = []
    for pixel_idx in fire_pixel_indices:
        fire_pixels.append(SmoothFirePixel(pixel_idx, seed=pixel_idx))

    # Calculate universes
    channels_per_led = 3
    leds_per_universe = 512 // channels_per_led
    num_universes = (led_count + leds_per_universe - 1) // leds_per_universe

    print(f"   Universes: {num_universes} (universe {start_universe}-{start_universe + num_universes - 1})\n")

    # Initialize sACN
    sender = sacn.sACNsender()
    sender.start()

    for i in range(num_universes):
        univ = start_universe + i
        sender.activate_output(univ)
        sender[univ].multicast = False
        sender[univ].destination = wled_ip

    # Prepare DMX buffers
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

                # Calculate universe and channel
                pixel_idx = fire_pixel.pixel_index
                universe_idx = pixel_idx // leds_per_universe
                local_pixel_idx = pixel_idx % leds_per_universe

                univ = start_universe + universe_idx
                channel_offset = local_pixel_idx * channels_per_led

                # Set pixel color
                universe_data[univ][channel_offset] = r
                universe_data[univ][channel_offset + 1] = g
                universe_data[univ][channel_offset + 2] = b

            # Send all universe data
            for univ, data in universe_data.items():
                sender[univ].dmx_data = data

            frame_count += 1

            # Progress report
            if current_time - last_report >= 2.0:
                elapsed = current_time - start_time
                fps = frame_count / elapsed if elapsed > 0 else 0
                print(f"🔥 {elapsed:.1f}s - {num_fire_pixels} pixels burning @ {fps:.1f} FPS")
                last_report = current_time

            # Target ~60 FPS for smooth animation
            time.sleep(1.0 / 60.0)

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
    smooth_fire(
        wled_ip="192.168.4.74",
        start_universe=1,
        led_count=1024,
        spacing=51,
        duration=999999  # Run indefinitely (until Ctrl+C)
    )
