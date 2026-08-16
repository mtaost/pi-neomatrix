#!/usr/bin/env python3
"""Record and measure the INMP441's ambient sound level."""

import argparse
from pathlib import Path
import sys
import wave

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hw.audio import AlsaCapture, AudioCaptureError, dbfs


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", help="ALSA device, for example hw:1,0")
    parser.add_argument("--seconds", type=float, default=5.0, help="Measurement duration (default: 5)")
    parser.add_argument("--rate", type=int, default=48_000, help="Sample rate (default: 48000)")
    parser.add_argument("--channels", type=int, default=2, help="I2S stream channels (default: 2)")
    parser.add_argument("--chunk", type=int, default=2_048, help="Frames per read (default: 2048)")
    parser.add_argument("--wav", type=Path, help="Optional destination for a 32-bit WAV recording")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.seconds <= 0 or args.rate <= 0 or args.channels <= 0 or args.chunk <= 0:
        print("--seconds, --rate, --channels, and --chunk must be positive.", file=sys.stderr)
        return 2
    capture = None
    writer = None
    levels = []
    peaks = []
    try:
        capture = AlsaCapture(args.device, args.rate, channels=args.channels, period_frames=args.chunk)
        if args.wav:
            args.wav.parent.mkdir(parents=True, exist_ok=True)
            writer = wave.open(str(args.wav), "wb")
            writer.setnchannels(1)
            writer.setsampwidth(4)
            writer.setframerate(args.rate)
        capture.start()
        print(f"Measuring ambient sound from {capture.device} for {args.seconds:g} seconds...")
        remaining = int(args.seconds * args.rate)
        while remaining > 0:
            samples = capture.read(min(args.chunk, remaining))
            if writer:
                pcm = np.rint(samples.clip(-1, 1 - 1 / 2**31) * 2**31).astype("<i4")
                writer.writeframes(pcm.tobytes())
            levels.append(dbfs(samples))
            peaks.append(float(np.max(np.abs(samples))))
            remaining -= len(samples)
    except AudioCaptureError as error:
        print(f"Microphone check failed: {error}", file=sys.stderr)
        return 1
    finally:
        if writer:
            writer.close()
        if capture:
            capture.close()

    mean_level = float(np.mean(levels))
    peak_dbfs = 20 * np.log10(max(max(peaks), 1e-12))
    print(f"Ambient RMS: {mean_level:.1f} dBFS")
    print(f"Peak:        {peak_dbfs:.1f} dBFS")
    if args.wav:
        print(f"Recording:   {args.wav}")
    if peak_dbfs <= -90:
        print("Result: near digital silence. Check I2S wiring, overlay, and device selection.")
        return 1
    print("Result: microphone is producing audio. Clap or speak near it and run again to confirm the peak rises.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
