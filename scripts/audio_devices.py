#!/usr/bin/env python3
"""List ALSA capture and playback devices for the Pi audio diagnostics."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hw.audio import AudioCaptureError, list_capture_devices, list_playback_devices


def show(title, devices):
    print(title)
    if devices:
        for device in devices:
            print(f"  {device.description}")
    else:
        print("  (none)")


def main():
    try:
        show("Capture devices:", list_capture_devices())
        show("Playback devices:", list_playback_devices())
    except AudioCaptureError as error:
        print(f"Audio device check failed: {error}", file=sys.stderr)
        return 1
    print("\nUse the hw:C,D value with the other audio diagnostic scripts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
