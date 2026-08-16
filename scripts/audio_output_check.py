#!/usr/bin/env python3
"""Play a short test tone through an ALSA speaker/HDMI output."""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hw.audio import AudioCaptureError, list_playback_devices, play_tone, select_device


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", help="ALSA playback device, for example hw:0,0")
    parser.add_argument("--seconds", type=float, default=2.0, help="Tone length (default: 2)")
    parser.add_argument("--frequency", type=float, default=440.0, help="Tone frequency in Hz (default: 440)")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.seconds <= 0 or args.frequency <= 0:
        print("--seconds and --frequency must be positive.", file=sys.stderr)
        return 2
    try:
        device = select_device(list_playback_devices(), args.device)
        print(f"Playing {args.frequency:g} Hz test tone on {device} for {args.seconds:g} seconds...")
        play_tone(device, args.seconds, args.frequency)
    except AudioCaptureError as error:
        print(f"Playback check failed: {error}", file=sys.stderr)
        return 1
    print("Result: ALSA playback completed. Confirm the tone was audible on the selected output.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
