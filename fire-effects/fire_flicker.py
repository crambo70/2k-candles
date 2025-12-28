#!/usr/bin/env python3
"""Flickering fire effect on a single RGB pixel."""

import time
import random
import sacn

def flicker_fire(wled_ip: str = "192.168.4.74",
                 universe: int = 1,
                 pixel_index: int = 0,
                 duration: int = 30):
    """
    Create a flickering fire effect on a single pixel.

    Args:
        wled_ip: IP address of WLED device
        universe: DMX universe number
        pixel_index: Which pixel to control (0-based)
        duration: How long to run the effect in seconds
    """

    # Initialize sACN sender
    sender = sacn.sACNsender()
    sender.start()
    sender.activate_output(universe)
    sender[universe].multicast = False
    sender[universe].destination = wled_ip

    # Fire color palette with weights
    fire_colors = [
        # (R, G, B, weight) - weight determines how often this color appears
        (255, 60, 0, 20),    # Deep orange-red (common)
        (255, 100, 0, 18),   # Orange (common)
        (255, 140, 0, 15),   # Light orange (fairly common)
        (255, 200, 0, 12),   # Yellow-orange (less common)
        (200, 40, 0, 10),    # Dark red (less common)
        (255, 255, 0, 8),    # Yellow (occasional)
        (255, 255, 100, 5),  # Pale yellow (rare)
        (255, 255, 200, 2),  # White-hot (very rare - the "tickle" of white)
        (100, 150, 255, 1),  # Blue flame (extremely rare - hottest part)
    ]

    # Create weighted list for random selection
    weighted_colors = []
    for color in fire_colors:
        r, g, b, weight = color
        weighted_colors.extend([(r, g, b)] * weight)

    print(f"🔥 Flickering fire effect on pixel {pixel_index}")
    print(f"   Universe: {universe}, IP: {wled_ip}")
    print(f"   Duration: {duration}s")
    print(f"   Press Ctrl+C to stop early\n")

    start_time = time.time()
    frame_count = 0

    try:
        while time.time() - start_time < duration:
            # Pick a random fire color
            r, g, b = random.choice(weighted_colors)

            # Add some randomness to intensity (flicker)
            intensity = random.uniform(0.6, 1.0)  # 60-100% brightness
            r = int(r * intensity)
            g = int(g * intensity)
            b = int(b * intensity)

            # Calculate DMX channel offset (3 channels per pixel: RGB)
            channel_offset = pixel_index * 3

            # Prepare DMX data (512 channels, all black except our pixel)
            dmx_data = [0] * 512
            dmx_data[channel_offset] = r
            dmx_data[channel_offset + 1] = g
            dmx_data[channel_offset + 2] = b

            # Send the data
            sender[universe].dmx_data = dmx_data

            # Variable frame rate for more organic feel
            # Flames flicker fast, but not uniformly
            sleep_time = random.uniform(0.02, 0.08)  # 20-80ms between updates
            time.sleep(sleep_time)

            frame_count += 1

            # Progress indicator every second
            if frame_count % 20 == 0:
                elapsed = time.time() - start_time
                print(f"🔥 {elapsed:.1f}s - RGB({r},{g},{b}) - intensity: {intensity:.2f}")

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")

    finally:
        # Turn off the pixel
        dmx_data = [0] * 512
        sender[universe].dmx_data = dmx_data
        sender.stop()

        elapsed = time.time() - start_time
        fps = frame_count / elapsed if elapsed > 0 else 0
        print(f"\n✅ Done!")
        print(f"   Total frames: {frame_count}")
        print(f"   Average FPS: {fps:.1f}")
        print(f"   Elapsed time: {elapsed:.1f}s")

if __name__ == "__main__":
    # You can change these parameters:
    flicker_fire(
        wled_ip="192.168.4.74",
        universe=1,
        pixel_index=0,      # First pixel (change to test different pixels)
        duration=30         # Run for 30 seconds
    )
