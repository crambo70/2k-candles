#!/usr/bin/env python3
"""Test script for 1024 RGB LED fixture via sACN."""

import time
from claude_lights.controller import WLEDController
from claude_lights.states import StateAnimation, Color

def rainbow_wave(led_count: int = 1024):
    """Create a rainbow wave across all LEDs."""
    controller = WLEDController(
        wled_ip="192.168.4.74",
        universe=1,
        start_channel=1,
        led_count=led_count,
        fps=30
    )

    print(f"Controlling {led_count} LEDs across {controller.num_universes} universes")
    print("Press Ctrl+C to stop\n")

    try:
        # Test 1: Solid colors
        print("Red...")
        controller.set_solid_color((255, 0, 0))
        time.sleep(1)

        print("Green...")
        controller.set_solid_color((0, 255, 0))
        time.sleep(1)

        print("Blue...")
        controller.set_solid_color((0, 0, 255))
        time.sleep(1)

        print("White...")
        controller.set_solid_color((255, 255, 255))
        time.sleep(1)

        print("Off...")
        controller.set_solid_color((0, 0, 0))
        time.sleep(1)

        # Test 2: Rainbow chase
        print("\nRainbow chase...")
        colors = [
            (255, 0, 0),    # Red
            (255, 127, 0),  # Orange
            (255, 255, 0),  # Yellow
            (0, 255, 0),    # Green
            (0, 0, 255),    # Blue
            (75, 0, 130),   # Indigo
            (148, 0, 211),  # Violet
        ]

        for _ in range(10):  # 10 cycles
            for color in colors:
                controller.set_solid_color(color)
                time.sleep(0.1)

        # Test 3: Sparkle effect
        print("\nSparkle effect...")
        import random
        for _ in range(100):  # 100 sparkles
            r = random.randint(0, 255)
            g = random.randint(0, 255)
            b = random.randint(0, 255)
            controller.set_solid_color((r, g, b))
            time.sleep(0.05)

        # Turn off
        print("\nTurning off...")
        controller.set_solid_color((0, 0, 0))

    except KeyboardInterrupt:
        print("\n\nStopping...")
    finally:
        controller.shutdown()
        print("Done!")

if __name__ == "__main__":
    rainbow_wave()
