# Thermal Occupancy Detection Handoff

## Objective

Use the MLX90640 thermal camera to put the display into automatic standby when nobody is present, then wake the existing display mode when someone returns. This should behave similarly to the current ambient-light automation, but occupancy should be based on thermal frames rather than BH1750 lux readings.

The preferred behavior is automatic standby: blank and pause the active display while the room is empty, but keep the service and occupancy detector running so the display can wake automatically. Setting `power = false` would require a manual user action to wake it and is probably not the right policy.

## Current architecture

- `main.py` creates the `DisplayController` and starts the BH1750 `SensorService` when available.
- `sensors.py` contains the scalar-reading `SensorService` used by the BH1750.
- `controller.py` owns display power, sleep state, brightness policy, mode lifecycle, frame composition, and the sole hardware frame sink.
- `layers.py` applies sleep and brightness to controller-composed frames.
- `display_modes/thermalcamera.py` currently owns its own MLX90640 I²C connection and reads frames only while the Thermal Camera mode is active.
- `modes.py` exposes the thermal mode with schema-driven settings.
- `webserver/static/app.js` renders mode settings from the registry metadata; thermal custom palette fields and exposure fields are conditionally shown.

Important architectural constraint: occupancy must work while any display mode is active. The current Thermal Camera mode cannot be the long-term owner of occupancy acquisition because it only runs when selected. The MLX90640 should be extracted into a controller-owned/shared thermal sensor service, with both the Thermal Camera renderer and occupancy detector consuming the latest frame.

## Thermal refactor findings

The previous black-frame behavior was most likely caused by:

- A hard-coded 16 Hz MLX90640 refresh rate.
- A 640 kHz I²C setup.
- Every `getFrame()` exception being swallowed and immediately retried in a tight loop.

The Adafruit driver API expects `getFrame(frame_buffer)` with a 768-element buffer and warns that high refresh rates can cause frame retries. The current implementation now starts at 4 Hz and 800 kHz, with 2/4/8/16 Hz selectable.

Current thermal improvements in `display_modes/thermalcamera.py`:

- Hardware imports are lazy, allowing hardware-free tests.
- A fake sensor can be injected for tests.
- Sensor access and refresh-rate updates are protected by a lock.
- Frame failures are logged once per distinct error and retried with a 250 ms delay.
- Recovery is logged.
- Non-finite or malformed frame data is rejected safely.
- The 32×24 frame is rendered through a stable palette and resized with bilinear interpolation.
- Owned I²C resources are released during cleanup.

Current thermal settings in `mode_settings.py` include:

- Sensor refresh rate.
- Exposure mode: `auto`, `percentile`, or `fixed`.
- Exposure smoothing.
- Minimum and maximum temperature.
- Low and high percentiles.
- Built-in palettes: Ironbow, Rainbow, Amber, Grayscale, and Cool.
- Custom cold/middle/hot colors.

Temperature data and API settings remain Celsius internally for compatibility with the MLX90640 data and saved configuration. The thermal min/max controls display their values in Fahrenheit in the UI. The current room-oriented slider ranges are approximately 41–95°F for the minimum and 59–113°F for the maximum.

## Recommended implementation plan

### 1. Extract a shared MLX90640 service

Create a reusable thermal acquisition class/service, likely under `sensors.py` or a new `thermal_sensor.py` module.

Responsibilities:

- Own the I²C bus and MLX90640 object.
- Configure the conservative refresh rate.
- Read frames on a background thread.
- Keep the latest valid 768-value frame and timestamp.
- Expose a thread-safe `get_latest_frame()` or callback/subscriber mechanism.
- Track `available`, `updated_at`, `last_error`, and recovery state.
- Avoid opening a second MLX90640 connection when the Thermal Camera mode is selected.

The existing `ThermalCamera` mode should become a renderer/consumer of this service. It should no longer independently compete for the I²C bus.

### 2. Add a standalone occupancy detector

Keep detection logic independent of hardware and the controller so it can be tested with fake frames.

Initial algorithm:

1. Ignore invalid/non-finite pixels.
2. Estimate background temperature from a robust statistic such as the median or a low percentile.
3. Mark pixels warmer than background by a configurable delta.
4. Group adjacent warm pixels into regions.
5. Require a minimum warm-pixel count and/or region size.
6. Produce `present`, `confidence`, `warm_pixels`, and diagnostic temperature values.

Relative temperature difference is preferable to one fixed absolute temperature because room temperature varies.

Recommended initial settings:

- `enabled`: false by default.
- `temperature_delta`: start around 3–5°F above the estimated background.
- `minimum_region_size`: conservative small connected region threshold.
- `absence_dwell_seconds`: start around 60 seconds.
- `presence_dwell_seconds`: start around 2–5 seconds.
- `startup_calibration_seconds`: allow the sensor/background estimate to settle before making decisions.
- Optional edge exclusion to reduce false positives from warm objects at the frame boundary.

Use hysteresis: the threshold to declare presence should not be identical to the threshold to declare absence.

### 3. Integrate occupancy into controller policy

Add occupancy state separately from the existing manual power state and BH1750 ambient sleep state. The controller should expose a clear sleep reason such as `occupancy_empty`.

When occupancy standby activates:

- Keep `power` logically on.
- Set the controller into a sleeping/paused state.
- Let `SleepLayer` produce a black output.
- Pause the active mode through its existing pause event.

When presence is confirmed:

- Clear occupancy sleep.
- Resume the active mode.
- Reapply the existing brightness and ambient-light policy.

Define precedence explicitly before implementation. A reasonable order is:

1. Manual power-off always keeps the display off.
2. Occupancy-empty standby and ambient-dark sleep can both request sleep.
3. The display wakes only when all enabled automatic sleep conditions permit it.
4. Existing manual override rules should prevent an immediate unwanted sleep after a user interaction, if that matches current ambient automation behavior.

### 4. Add UI and API settings

Add a Presence detection section to the Automation page with:

- Enable occupancy standby.
- Sensitivity / temperature delta.
- Minimum warm region size.
- Absence dwell time.
- Presence wake dwell time.
- Startup calibration duration.
- Current detector status and confidence.
- Last thermal reading/error timestamp.

Expose occupancy state through `/api/state`, for example:

```json
{
  "occupancy": {
    "available": true,
    "present": false,
    "confidence": 0.12,
    "warm_pixels": 0,
    "updated_at": 0,
    "error": null
  }
}
```

Settings should be persisted inside the existing configuration structure, likely under `automation.occupancy` or a sibling `occupancy` block. Keep occupancy disabled by default so a missing MLX90640 does not affect normal service startup.

### 5. Test before physical tuning

Add hardware-free tests for:

- Empty-room frames.
- A human-sized warm region.
- Small isolated hot objects.
- Warm background drift.
- Invalid frames and sensor recovery.
- Presence and absence hysteresis.
- Presence/absence dwell timers.
- Controller pause, black output, and automatic resume.
- API validation and UI route content.

The current suite is run with:

```bash
python3 -m unittest discover -s tests -v
```

### 6. Tune on the Pi

Start at 4 Hz and inspect logs while testing. Validate in this order:

1. Thermal frames continue to arrive while a non-thermal display mode is active.
2. Empty-room detection remains stable for several minutes.
3. A person entering wakes the display after the configured dwell time.
4. Sitting still does not cause intermittent sleep.
5. Warm objects, sunlight, and HVAC changes do not create unacceptable false wakes.
6. Switching display modes does not create a second I²C owner or leak the sensor resource.

Keep thermal data in memory only. Occupancy detection does not require storing images or publishing raw thermal frames through the API.

## Files likely to change

- `sensors.py` or new `thermal_sensor.py`: shared MLX90640 acquisition service.
- `display_modes/thermalcamera.py`: consume shared frames and retain palette/exposure rendering.
- New detector module, likely `occupancy.py`.
- `controller.py`: occupancy state, policy integration, pause/wake behavior, API state.
- `config.py` / `mode_settings.py`: validated persisted settings.
- `webserver/templates/index.html`: Automation page controls.
- `webserver/static/app.js`: form binding and status display.
- Thermal/occupancy tests under `tests/`.
- `README.md`: configuration and Pi tuning instructions after hardware validation.

## Open decisions

- Whether the detector should use connected components, a simpler warm-pixel count, or both.
- Whether occupancy sleep should pause the mode or stop/restart it. Pausing is the recommended first approach.
- Exact precedence between ambient-dark sleep and occupancy-empty sleep.
- Whether to expose raw background temperature and confidence in the UI for tuning.
- Whether the shared thermal service should start only when occupancy is enabled or whenever the MLX90640 is available.
