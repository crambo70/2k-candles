#!/usr/bin/env python3
"""
Test Console for Fire Effects Show Control

Simulates a lighting console sending DMX control signals.
Provides preset scenes and interactive control.
"""

import sacn
import time
import sys


class TestConsole:
    """Simulated lighting console for testing fire effects."""

    def __init__(self, control_universe: int = 100):
        """
        Initialize test console.

        Args:
            control_universe: DMX universe to send control signals to
        """
        self.control_universe = control_universe

        # Initialize sACN sender
        self.sender = sacn.sACNsender()
        self.sender.start()
        self.sender.activate_output(control_universe)
        self.sender[control_universe].multicast = True  # Use multicast for local testing

        # Current DMX values
        self.dmx = [0] * 512

        print(f"🎛️  Test Console initialized on Universe {control_universe}")

    def set_channel(self, channel: int, value: int):
        """Set a DMX channel value (1-indexed)."""
        self.dmx[channel - 1] = max(0, min(255, value))

    def send(self):
        """Send current DMX values."""
        self.sender[self.control_universe].dmx_data = self.dmx

    def stop(self):
        """Stop the console."""
        # Send all zeros
        self.dmx = [0] * 512
        self.send()
        self.sender.stop()

    # ===== Preset Scenes =====

    def scene_all_off(self):
        """Turn all flame banks off."""
        print("Scene: ALL OFF")
        for ch in range(1, 7):
            self.set_channel(ch, 0)
        self.send()

    def scene_all_full(self):
        """All flame banks at full intensity."""
        print("Scene: ALL FULL")
        self.set_channel(1, 255)  # Bank 1
        self.set_channel(2, 255)  # Bank 2
        self.set_channel(3, 255)  # Bank 3
        self.set_channel(4, 255)  # Bank 4
        self.set_channel(5, 0)    # Wind off
        self.set_channel(6, 0)    # Wind speed
        self.send()

    def scene_banks_sequential(self, intensity: int = 200):
        """Turn on banks one at a time."""
        print(f"Scene: BANKS SEQUENTIAL @ {intensity}")
        banks = [1, 2, 3, 4]

        for bank_ch in banks:
            # Turn on this bank
            self.set_channel(bank_ch, intensity)
            self.send()
            print(f"  Bank {bank_ch} ON")
            time.sleep(2)

        time.sleep(2)

        # Turn off in reverse
        for bank_ch in reversed(banks):
            self.set_channel(bank_ch, 0)
            self.send()
            print(f"  Bank {bank_ch} OFF")
            time.sleep(2)

    def scene_wave(self, duration: int = 30):
        """Wave pattern - banks fade in and out in sequence."""
        print(f"Scene: WAVE (running for {duration}s)")
        start_time = time.time()

        while time.time() - start_time < duration:
            elapsed = time.time() - start_time
            # Each bank gets a sine wave offset by 90 degrees
            import math

            for bank_id in range(1, 5):
                # Sine wave for this bank
                phase = (elapsed + (bank_id - 1) * 2) * 0.5  # Offset each bank
                intensity = (math.sin(phase) + 1) / 2  # 0 to 1
                dmx_value = int(intensity * 255)
                self.set_channel(bank_id, dmx_value)

            self.send()
            time.sleep(0.05)

        self.scene_all_off()

    def scene_wind_gust(self, wind_intensity: int = 200, wind_speed: int = 150):
        """Activate wind effect with all banks on."""
        print(f"Scene: WIND GUST (intensity={wind_intensity}, speed={wind_speed})")

        # Turn on all banks
        for bank_ch in range(1, 5):
            self.set_channel(bank_ch, 200)

        # Set wind
        self.set_channel(5, wind_intensity)
        self.set_channel(6, wind_speed)
        self.send()

        print("  Wind active for 20 seconds...")
        time.sleep(20)

        # Turn off wind
        print("  Wind stopping...")
        self.set_channel(5, 0)
        self.set_channel(6, 0)
        self.send()

    def scene_storm(self, duration: int = 30):
        """Simulate a storm with varying wind."""
        print(f"Scene: STORM (running for {duration}s)")

        # All banks on
        for bank_ch in range(1, 5):
            self.set_channel(bank_ch, 220)

        start_time = time.time()
        import random

        while time.time() - start_time < duration:
            # Random wind gusts
            wind_intensity = random.randint(100, 255)
            wind_speed = random.randint(80, 200)

            self.set_channel(5, wind_intensity)
            self.set_channel(6, wind_speed)
            self.send()

            print(f"  Gust: intensity={wind_intensity}, speed={wind_speed}")

            # Random duration for this gust
            time.sleep(random.uniform(1, 4))

        # Calm down
        print("  Storm ending...")
        self.set_channel(5, 0)
        self.set_channel(6, 0)
        self.send()
        time.sleep(2)
        self.scene_all_off()

    def scene_fade_in_out(self, duration: int = 10):
        """Fade all banks in and out."""
        print(f"Scene: FADE IN/OUT ({duration}s each direction)")

        # Fade in
        print("  Fading in...")
        for level in range(0, 256, 5):
            for bank_ch in range(1, 5):
                self.set_channel(bank_ch, level)
            self.send()
            time.sleep(duration / (256 / 5))

        time.sleep(2)

        # Fade out
        print("  Fading out...")
        for level in range(255, -1, -5):
            for bank_ch in range(1, 5):
                self.set_channel(bank_ch, level)
            self.send()
            time.sleep(duration / (256 / 5))

    # ===== Interactive Control =====

    def interactive_mode(self):
        """Interactive control mode."""
        print("\n" + "="*60)
        print("🎛️  INTERACTIVE CONSOLE MODE")
        print("="*60)
        print("\nCommands:")
        print("  1-4 [value]  - Set flame bank 1-4 (0-255)")
        print("  w [value]    - Set wind intensity (0-255)")
        print("  s [value]    - Set wind speed (0-255)")
        print("  all [value]  - Set all banks to value")
        print("  off          - Turn everything off")
        print("  status       - Show current values")
        print("  quit         - Exit interactive mode")
        print("\nExample: '1 200' sets Bank 1 to intensity 200")
        print("="*60 + "\n")

        while True:
            try:
                cmd = input("Console> ").strip().lower()

                if not cmd:
                    continue

                parts = cmd.split()

                if cmd == "quit" or cmd == "q":
                    print("Exiting interactive mode...")
                    break

                elif cmd == "off":
                    self.scene_all_off()

                elif cmd == "status":
                    print(f"\nCurrent DMX values:")
                    print(f"  Bank 1: {self.dmx[0]}")
                    print(f"  Bank 2: {self.dmx[1]}")
                    print(f"  Bank 3: {self.dmx[2]}")
                    print(f"  Bank 4: {self.dmx[3]}")
                    print(f"  Wind Intensity: {self.dmx[4]}")
                    print(f"  Wind Speed: {self.dmx[5]}\n")

                elif parts[0] in ['1', '2', '3', '4'] and len(parts) == 2:
                    bank = int(parts[0])
                    value = int(parts[1])
                    self.set_channel(bank, value)
                    self.send()
                    print(f"✓ Bank {bank} → {value}")

                elif parts[0] == 'w' and len(parts) == 2:
                    value = int(parts[1])
                    self.set_channel(5, value)
                    self.send()
                    print(f"✓ Wind Intensity → {value}")

                elif parts[0] == 's' and len(parts) == 2:
                    value = int(parts[1])
                    self.set_channel(6, value)
                    self.send()
                    print(f"✓ Wind Speed → {value}")

                elif parts[0] == 'all' and len(parts) == 2:
                    value = int(parts[1])
                    for bank in range(1, 5):
                        self.set_channel(bank, value)
                    self.send()
                    print(f"✓ All banks → {value}")

                else:
                    print("❌ Invalid command. Type 'quit' to exit or try a valid command.")

            except (ValueError, IndexError):
                print("❌ Invalid input format")
            except KeyboardInterrupt:
                print("\nExiting...")
                break


def main():
    """Main test console program."""
    console = TestConsole(control_universe=100)

    if len(sys.argv) > 1:
        # Run specific scene
        scene = sys.argv[1].lower()

        try:
            if scene == "off":
                console.scene_all_off()
            elif scene == "full":
                console.scene_all_full()
                time.sleep(30)
            elif scene == "sequential":
                console.scene_banks_sequential()
            elif scene == "wave":
                console.scene_wave(duration=30)
            elif scene == "wind":
                console.scene_wind_gust()
            elif scene == "storm":
                console.scene_storm(duration=30)
            elif scene == "fade":
                console.scene_fade_in_out()
            elif scene == "interactive":
                console.interactive_mode()
            else:
                print(f"Unknown scene: {scene}")
                print("Available scenes: off, full, sequential, wave, wind, storm, fade, interactive")

        except KeyboardInterrupt:
            print("\nInterrupted")
        finally:
            console.scene_all_off()
            console.stop()

    else:
        # No arguments - show menu
        print("\n🎭 Fire Effects Test Console")
        print("\nAvailable scenes:")
        print("  1. off         - Turn everything off")
        print("  2. full        - All banks at full (30s)")
        print("  3. sequential  - Banks turn on one by one")
        print("  4. wave        - Sine wave across banks (30s)")
        print("  5. wind        - Wind gust effect (20s)")
        print("  6. storm       - Random wind storm (30s)")
        print("  7. fade        - Fade in and out (20s)")
        print("  8. interactive - Interactive console mode")
        print("\nUsage: python3 test_console.py <scene>")
        print("Example: python3 test_console.py interactive\n")


if __name__ == "__main__":
    main()
