# DMX Fire Controller

Low-latency integrated DMX input to sACN output fire effects controller.

## Architecture

```
[DMX Console] → [ENTTEC DMX USB Pro] → [DMX Fire Controller] → [WLED (sACN)]
   (USB Serial)        (Serial Port)      (Single Process)      (Network)
```

## Features

### Performance Optimizations
- **Ultra-low latency**: ~1ms serial timeout, aggressive buffer draining
- **60 FPS rendering**: Smooth fire effect animation
- **Single-threaded**: No thread context switching overhead
- **Buffer draining**: Reads up to 10 DMX packets per frame

### Noise Reduction
- **Hysteresis filtering**: Ignores DMX changes < 2% (5 DMX values)
- **Smooth interpolation**: Banks ramp gradually (30% per frame)
- **Display threshold**: Status only shows banks > 1% intensity

### Monitoring
- Real-time FPS display
- DMX packet rate (packets/second)
- Latency measurement (ms since last DMX packet)
- Active bank status
- Debug mode for raw DMX values

## Usage

### Basic Run
```bash
python3 dmx_fire_controller.py
```

### Debug Mode
Shows real-time DMX channel values every 10 frames:
```bash
python3 dmx_fire_controller.py --debug
```

## DMX Control Mapping

### Input (from DMX Console)
- **Channel 1**: Flame Bank 1 Intensity (0-255)
- **Channel 2**: Flame Bank 2 Intensity (0-255)
- **Channel 3**: Flame Bank 3 Intensity (0-255)
- **Channel 4**: Flame Bank 4 Intensity (0-255)
- **Channel 5**: Wind Effect Intensity (0-255)
- **Channel 6**: Wind Speed (0-255)

### Output (sACN to WLED)
- **Universe 1-6**: RGB data for 1024 LEDs
- **Fire pixels**: Every 51st pixel (24 total flames)
- **Distribution**: 6 flames per bank, 4 banks total

## Configuration

Edit these parameters in `dmx_fire_controller.py`:

```python
controller = DMXFireController(
    dmx_serial_port='/dev/tty.usbserial-EN437698',  # ENTTEC serial port
    dmx_universe=1,                                  # Logical input universe
    output_ip='192.168.4.74',                        # WLED device IP
    output_universe_start=1,                         # sACN output start universe
    total_pixels=1024,                               # Total LED count
    spacing=51                                       # Fire pixel spacing
)
```

## Fire Banks

The 1024 LEDs are divided into 4 controllable banks:

- **Bank 1**: Pixels 0-255 (every 51st = 6 flames)
- **Bank 2**: Pixels 256-511 (every 51st = 6 flames)
- **Bank 3**: Pixels 512-767 (every 51st = 6 flames)
- **Bank 4**: Pixels 768-1023 (every 51st = 6 flames)

## Status Display

Example output:
```
🔥  60.0 FPS | DMX: 250.0 pkt/s | Latency:  4.2ms | B1:100% B2: 75% B3: 50%
```

- **FPS**: Render frame rate
- **DMX**: Incoming DMX packet rate
- **Latency**: Time since last DMX packet (lower is better)
- **B1-B4**: Active banks with intensity percentage

## Troubleshooting

### High Latency (> 50ms)
- Check DMX console is outputting continuously
- Verify ENTTEC device is connected
- Try debug mode to see raw DMX values

### Flickering/Noise
- Adjust hysteresis threshold (default 2%):
  ```python
  if diff > 0.02:  # Change this value
  ```
- Adjust smoothing factor (default 0.3):
  ```python
  self.intensity += (self.target_intensity - self.intensity) * 0.3
  ```

### No Response to DMX
- Check serial port path is correct
- Verify DMX universe/channels match console output
- Run with `--debug` flag to see raw DMX values

### Port Already in Use
```bash
# Kill processes using sACN port
lsof -ti :5568 | xargs kill -9
```

## Technical Details

### DMX Input Processing
1. Poll serial port (non-blocking, 0.001s timeout)
2. Read up to 10 packets per frame (drain buffer)
3. Apply hysteresis filter to each channel
4. Smooth interpolate to target values

### Fire Effect Rendering
- SmoothFirePixel: Algorithmic fire colors with smooth transitions
- Waxing/waning: Sine wave intensity modulation
- Color palette: Orange-yellow with rare white-hot/blue flashes
- Update rate: 60 FPS

### sACN Output
- 6 universes (1024 LEDs × 3 channels = 3072 ch ÷ 512 = 6 universes)
- Unicast to specific WLED IP
- RGB channel order per LED

## Performance Expectations

- **FPS**: 50-60 FPS sustained
- **DMX Rate**: 200-250 packets/second (typical)
- **Latency**: 3-10ms (typical)
- **CPU Usage**: ~10-15% single core

## Files

- `dmx_fire_controller.py`: Main integrated controller
- `test_dmx_input.py`: DMX input testing utility
- `fire-effects/`: Original fire effect modules
