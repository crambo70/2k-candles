"""
Configuration file for 1,500 Candles Fire Controller

Edit this file to configure your hardware setup.
"""

import platform

# =============================================================================
# ENTTEC DMX USB Pro Configuration
# =============================================================================

# Serial Port - PLATFORM SPECIFIC!
#
# macOS:   '/dev/cu.usbserial-EN437698'  ⚠️ MUST use 'cu' not 'tty'!
# Windows: 'COM3' or 'COM4' etc.
# Linux:   '/dev/ttyUSB0' or '/dev/ttyUSB1' etc.
#
# To find your device:
#   macOS:   ls -la /dev/cu.usbserial-*
#   Windows: Check Device Manager → Ports (COM & LPT)
#   Linux:   ls -la /dev/ttyUSB*

DMX_SERIAL_PORT = '/dev/cu.usbserial-EN437698'  # UPDATE THIS FOR YOUR SYSTEM

# DMX Settings
DMX_UNIVERSE = 1  # Logical DMX universe (for display only)
DMX_BAUDRATE = 115200  # Do not change - ENTTEC fixed rate

# =============================================================================
# WLED Network Configuration
# =============================================================================

# WLED Device IP Address
WLED_IP = '192.168.4.74'  # UPDATE THIS FOR YOUR WLED

# sACN Universe Settings
WLED_UNIVERSE_START = 1  # First universe for sACN output
SACN_PORT = 5568  # Standard sACN port (do not change)

# =============================================================================
# LED Strip Configuration
# =============================================================================

# Total number of LEDs in your strip
TOTAL_PIXELS = 1500

# Fire pixel spacing
# 1 = every pixel gets fire (1500 flames)
# 2 = every other pixel (750 flames)
# 3 = every 3rd pixel (500 flames)
PIXEL_SPACING = 1

# =============================================================================
# Performance Tuning
# =============================================================================

# Target rendering frame rate
TARGET_FPS = 60

# DMX polling settings
DMX_TIMEOUT = 0.001  # Serial read timeout in seconds (1ms)
DMX_PACKETS_PER_FRAME = 10  # Max packets to drain per frame

# Noise reduction
HYSTERESIS_THRESHOLD = 5  # Ignore DMX changes < this value (out of 255)
SMOOTH_RAMP_FACTOR = 0.3  # 0.0 = instant, 1.0 = very slow

# =============================================================================
# Fire Effect Parameters
# =============================================================================

# Default values when no DMX control
DEFAULT_FLICKER_INTENSITY = 0.5  # 0.0 to 1.0
DEFAULT_COLOR_SHIFT = 0.0  # 0.0 = yellow, 1.0 = red
DEFAULT_BLUE_AMOUNT = 0.0  # 0.0 = no blue, 1.0 = white-hot

# =============================================================================
# Auto-Detection Helpers
# =============================================================================

def get_platform_info():
    """Get current platform information."""
    return {
        'system': platform.system(),  # 'Darwin' (macOS), 'Windows', 'Linux'
        'platform': platform.platform(),
        'python_version': platform.python_version()
    }

def suggest_serial_port():
    """Suggest serial port based on platform."""
    import glob
    import os

    system = platform.system()

    if system == 'Darwin':  # macOS
        ports = glob.glob('/dev/cu.usbserial-*')
        if ports:
            return ports[0]
        return '/dev/cu.usbserial-EN437698'

    elif system == 'Windows':
        # Try common COM ports
        for port in ['COM3', 'COM4', 'COM5', 'COM6']:
            if os.path.exists(f'\\\\.\\{port}'):
                return port
        return 'COM3'

    elif system == 'Linux':
        ports = glob.glob('/dev/ttyUSB*')
        if ports:
            return ports[0]
        return '/dev/ttyUSB0'

    return None

def validate_config():
    """Validate configuration settings."""
    import glob

    issues = []

    # Check serial port
    system = platform.system()
    if system == 'Darwin' and DMX_SERIAL_PORT.startswith('/dev/tty.'):
        issues.append("⚠️  CRITICAL: macOS must use /dev/cu.* not /dev/tty.*")
        issues.append(f"   Suggested: {suggest_serial_port()}")

    # Check if port exists
    if system == 'Darwin':
        if not glob.glob(DMX_SERIAL_PORT):
            issues.append(f"⚠️  Serial port not found: {DMX_SERIAL_PORT}")
            suggested = suggest_serial_port()
            if suggested:
                issues.append(f"   Suggested: {suggested}")

    # Validate network settings
    import socket
    try:
        socket.inet_aton(WLED_IP)
    except socket.error:
        issues.append(f"⚠️  Invalid IP address: {WLED_IP}")

    # Validate LED count
    if TOTAL_PIXELS < 1 or TOTAL_PIXELS > 10000:
        issues.append(f"⚠️  Invalid TOTAL_PIXELS: {TOTAL_PIXELS}")

    return issues

# =============================================================================
# Convenience Functions
# =============================================================================

def print_config():
    """Print current configuration."""
    print("=" * 70)
    print("1,500 Candles Fire Controller - Configuration")
    print("=" * 70)
    print(f"\n🖥️  Platform: {platform.system()} ({platform.platform()})")
    print(f"🐍 Python: {platform.python_version()}")
    print(f"\n📡 ENTTEC DMX USB Pro:")
    print(f"   Port: {DMX_SERIAL_PORT}")
    print(f"   Universe: {DMX_UNIVERSE} (logical)")
    print(f"   Baudrate: {DMX_BAUDRATE}")
    print(f"\n🌐 WLED Network:")
    print(f"   IP: {WLED_IP}")
    print(f"   Universe: {WLED_UNIVERSE_START}-{WLED_UNIVERSE_START + (TOTAL_PIXELS * 3 // 512)}")
    print(f"   Port: {SACN_PORT}")
    print(f"\n💡 LED Configuration:")
    print(f"   Total Pixels: {TOTAL_PIXELS}")
    print(f"   Spacing: Every {PIXEL_SPACING}{'st' if PIXEL_SPACING == 1 else 'nd' if PIXEL_SPACING == 2 else 'rd' if PIXEL_SPACING == 3 else 'th'} pixel")
    print(f"   Fire Pixels: {TOTAL_PIXELS // PIXEL_SPACING}")
    print(f"\n⚡ Performance:")
    print(f"   Target FPS: {TARGET_FPS}")
    print(f"   DMX Timeout: {DMX_TIMEOUT * 1000:.1f}ms")

    # Validation
    issues = validate_config()
    if issues:
        print(f"\n⚠️  Configuration Issues:")
        for issue in issues:
            print(f"   {issue}")
    else:
        print(f"\n✅ Configuration valid!")

    print("=" * 70)

if __name__ == '__main__':
    # When run directly, print configuration and validate
    print_config()
