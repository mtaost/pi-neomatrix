# pi-neomatrix Agent Handoff

## Starting Point

- Baseline commit: `8b6b3e1` (`Initial vibe pass of web ui service`).
- Base commit was clean when this handoff was created; lifecycle hardening described below is now an uncommitted follow-up.
- The Raspberry Pi service was manually tested successfully for Image Viewer, Game of Life, global brightness, and BH1750 lux readout.

## What Exists

- `main.py` starts a Flask/Waitress LAN service on port `8080`; it creates the hardware driver and an optional BH1750 sensor service.
- `controller.py` owns the active mode, configuration persistence, rendering loop, power state, ambient-light policy, frame composition, final black-frame/GPIO shutdown sequence, and mode-crash recovery. A crashing active mode is recorded in API state as `mode_error`, cleaned up, persisted as inactive/off, and rendered black.
- Visual modes publish PIL frames through `display_modes/module.py`; only the controller compositor sends the final frame to `MatrixDriver`.
- `layers.py` applies sleep and brightness layers. Ambient automation is disabled by default and its defaults are persisted in `neomatrix-config.json` (ignored by Git).
- `modes.py` is the stable mode registry. `assets.py` only permits image assets from `res/`; never accept arbitrary file paths or browser uploads without a dedicated security/storage design.
- `webserver/app.py` serves the UI and JSON API. The UI is dependency-free HTML/CSS/JS in `webserver/templates/index.html` and `webserver/static/`.
- `lifecycle.py` handles `SIGINT` and `SIGTERM`: it invokes controller shutdown before exiting. `main.py` registers cleanup before startup, and `driver.py` makes GPIO deinitialization idempotent.
- `logging_setup.py` configures timestamped standard-library logging to stderr (systemd journald). Default level is `INFO`; set `NEOMATRIX_LOG_LEVEL=DEBUG` only for temporary diagnosis. Lifecycle, mode selection, sensor failures/recovery, API rejections, and unexpected mode crashes are logged; per-frame diagnostics are debug-only.

## Current UI Decisions

- `/` is the Display page; `/automation` is a separate page for ambient automation and sensor status.
- The Display header has one compact row: inline-SVG power toggle, inline-SVG brightness icon, slider, and percentage. Brightness is persisted when the slider is released (`change` event), not continuously while dragging.
- Display mode selection is a dropdown. It renders one mode card at a time; selecting a dropdown option does not start it. The card’s action button starts the mode.
- Image Viewer’s card includes the required asset selector. Other cards currently reserve their settings space with placeholder text.
- The Automation page groups settings into Sleep & wake, Adaptive brightness, and Manual changes, with help text beneath each field.
- UI icons are inline SVGs, not font/emoji icons, because the deployed browser font lacked the power glyph.

## Key APIs and Behavior

- `GET /api/state`, `/api/modes`, and `/api/assets` return `{ "state": ..., "error": null }`.
- `POST /api/mode` selects a mode; Image Viewer requires an approved `asset_id`.
- `PATCH /api/settings` updates global brightness and/or automation settings.
- `POST /api/power` toggles `{ "on": true|false }`.
- The service is intended for a trusted LAN only: no authentication, HTTPS, or internet exposure in the current design.

## Run and Test

On the Pi:

```bash
sudo python3 -m pip install -r requirements.txt --break-system-packages
sudo python3 main.py
```

Open `http://<pi-ip>:8080`.

## Deployment Follow-up

The `systemd` unit template at `deploy/pi-neomatrix.service` now uses SIGTERM with a 10-second stop timeout. It has not yet been enabled and validated on the Pi. After the next feature slice stabilizes, make this a deliberate deployment task:

1. Update the unit's project paths for the installed location, install it under `/etc/systemd/system/`, and enable it at boot.
2. Verify the service starts after a reboot, binds only to the trusted LAN as expected, and can access GPIO/I²C as root.
3. Verify `systemctl stop` sends a graceful SIGTERM shutdown that blanks the panel and releases GPIO; separately verify `Restart=on-failure` recovers from a forced process crash.
4. Document the final install, restart, log-inspection, and rollback commands in the README.

Hard power loss, kernel failure, and SIGKILL cannot execute Python cleanup. The intended mitigation is the service restart policy plus writing a known frame at startup.

Hardware-free test suite:

```bash
python3 -m unittest discover -s tests -v
```

The suite covers controller state, config persistence, asset allowlisting, automation policy, API validation, and both UI routes. The prior development environment used a temporary virtual environment with Flask, Waitress, and Pillow when the system Python lacked Flask.

## Recommended Next Work

Implement schema-driven settings for individual display modes, one mode at a time:

1. Add each mode’s declarative settings schema and validation/update hook in `modes.py` / the mode contract.
2. Add a controller/API path for validated active-mode setting updates.
3. Render the returned schema inside the selected mode’s existing card; keep the Display/Automation page structure intact.
4. Begin with a low-risk visual mode such as Game of Life speed or Pixel Rain density/persistence, test it on the physical panel, then generalize.

Avoid changing the controller’s sole-ownership of the hardware driver or bypassing its compositor; this is what keeps mode switching, sleep, and brightness policies consistent.
