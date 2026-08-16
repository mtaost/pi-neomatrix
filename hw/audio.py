"""Small ALSA helpers shared by the audio diagnostics and display modes.

The INMP441 is an I2S device. Capturing it through ``arecord`` keeps the
application on ALSA's native path and avoids PortAudio device-number changes
between boots.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
import subprocess
from typing import Iterable

import numpy as np


class AudioCaptureError(RuntimeError):
    """Raised when ALSA cannot start or continue an audio capture."""


@dataclass(frozen=True)
class AlsaDevice:
    card: int
    device: int
    card_id: str
    card_name: str
    device_name: str
    direction: str

    @property
    def hardware_name(self) -> str:
        return f"hw:{self.card},{self.device}"

    @property
    def description(self) -> str:
        return f"{self.hardware_name} — {self.card_name}: {self.device_name}"


_DEVICE_LINE = re.compile(
    r"^card (?P<card>\d+): (?P<card_id>[^ ]+) \[(?P<card_name>.+)\], "
    r"device (?P<device>\d+): (?P<device_name>.+)$"
)
_I2S_NAMES = ("i2s", "inmp", "mems")


def _list_devices(command: str, direction: str) -> list[AlsaDevice]:
    try:
        result = subprocess.run(
            [command, "--list-devices"], check=False, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
    except FileNotFoundError as error:
        raise AudioCaptureError(
            f"{command} is not installed; install the alsa-utils package."
        ) from error
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown ALSA error"
        raise AudioCaptureError(f"{command} --list-devices failed: {detail}")

    devices = []
    for line in result.stdout.splitlines():
        match = _DEVICE_LINE.match(line.strip())
        if match:
            values = match.groupdict()
            values["card"] = int(values["card"])
            values["device"] = int(values["device"])
            devices.append(AlsaDevice(**values, direction=direction))
    return devices


def list_capture_devices() -> list[AlsaDevice]:
    return _list_devices("arecord", "capture")


def list_playback_devices() -> list[AlsaDevice]:
    return _list_devices("aplay", "playback")


def select_device(devices: Iterable[AlsaDevice], requested: str | None = None) -> str:
    """Select an explicit device or the single likely I2S device.

    Selecting the first ALSA card is deliberately avoided: HDMI, USB, and the
    I2S microphone can change card order after a reboot.
    """
    devices = list(devices)
    if requested:
        return requested
    if not devices:
        raise AudioCaptureError("No ALSA hardware devices were found.")
    i2s_devices = [
        device for device in devices
        if any(name in device.description.lower() for name in _I2S_NAMES)
    ]
    if len(i2s_devices) == 1:
        return i2s_devices[0].hardware_name
    if len(devices) == 1:
        return devices[0].hardware_name
    choices = ", ".join(device.hardware_name for device in devices)
    raise AudioCaptureError(
        f"More than one device is available ({choices}). Pass --device hw:C,D."
    )


def pcm_s32le_to_float(data: bytes) -> np.ndarray:
    """Convert interleaved S32_LE PCM to normalized floating-point samples."""
    if len(data) % 4:
        raise AudioCaptureError(f"Received a partial S32_LE sample ({len(data)} bytes).")
    return np.frombuffer(data, dtype="<i4").astype(np.float32) / float(2**31)


def select_loudest_channel(samples: np.ndarray, channels: int) -> np.ndarray:
    """Return the active channel from an interleaved I2S capture.

    The Google Voice HAT compatibility overlay requires a two-channel stream.
    An INMP441 transmits on only its selected left or right I2S slot, so using
    the louder channel avoids reducing its signal level by averaging it with
    the unused slot.
    """
    if channels == 1:
        return samples
    frames = samples.reshape((-1, channels))
    rms = np.sqrt(np.mean(np.square(frames, dtype=np.float64), axis=0))
    return frames[:, int(np.argmax(rms))]


def dbfs(samples: np.ndarray) -> float:
    """Return RMS level in dBFS, clamped so digital silence remains printable."""
    if not len(samples):
        return -120.0
    rms = float(np.sqrt(np.mean(np.square(samples, dtype=np.float64))))
    return max(-120.0, 20.0 * math.log10(max(rms, 1e-12)))


class AlsaCapture:
    """S32_LE capture that returns the active channel as a mono sample array."""

    def __init__(self, device=None, sample_rate=48_000, channels=2, period_frames=2_048):
        self.device = device or select_device(list_capture_devices())
        self.sample_rate = int(sample_rate)
        self.channels = int(channels)
        self.period_frames = int(period_frames)
        self._process = None

    def start(self) -> None:
        if self._process is not None:
            return
        command = [
            "arecord", "--quiet", "--file-type=raw", "--format=S32_LE",
            f"--channels={self.channels}", f"--rate={self.sample_rate}",
            f"--period-size={self.period_frames}", f"--buffer-size={self.period_frames * 4}",
            "--device", self.device, "-",
        ]
        try:
            self._process = subprocess.Popen(
                command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
        except OSError as error:
            raise AudioCaptureError(f"Could not start arecord for {self.device}: {error}") from error

    def read(self, frames=None) -> np.ndarray:
        if self._process is None or self._process.stdout is None:
            raise AudioCaptureError("Audio capture was not started.")
        frames = int(frames or self.period_frames)
        expected_bytes = frames * self.channels * 4
        chunks = []
        remaining = expected_bytes
        while remaining:
            chunk = self._process.stdout.read(remaining)
            if not chunk:
                raise self._capture_ended_error()
            chunks.append(chunk)
            remaining -= len(chunk)
        samples = pcm_s32le_to_float(b"".join(chunks))
        return select_loudest_channel(samples, self.channels)

    def _capture_ended_error(self) -> AudioCaptureError:
        assert self._process is not None
        stderr = b""
        if self._process.poll() is not None and self._process.stderr is not None:
            stderr = self._process.stderr.read()
        detail = stderr.decode(errors="replace").strip() or "arecord stopped producing audio"
        return AudioCaptureError(f"Capture from {self.device} failed: {detail}")

    def close(self) -> None:
        process, self._process = self._process, None
        if process is None:
            return
        if process.poll() is None:
            process.terminate()
        try:
            process.communicate(timeout=1)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


def play_tone(device, seconds=2.0, frequency=440.0, sample_rate=48_000) -> None:
    """Play a short, quiet sine tone through a selected ALSA output device."""
    frame_count = int(seconds * sample_rate)
    timeline = np.arange(frame_count, dtype=np.float32) / sample_rate
    samples = (np.sin(2 * np.pi * frequency * timeline) * 0.18 * 32767).astype("<i2")
    command = [
        "aplay", "--quiet", "--file-type=raw", "--format=S16_LE", "--channels=1",
        f"--rate={sample_rate}", "--device", device, "-",
    ]
    try:
        result = subprocess.run(command, input=samples.tobytes(), stderr=subprocess.PIPE, check=False)
    except FileNotFoundError as error:
        raise AudioCaptureError("aplay is not installed; install the alsa-utils package.") from error
    if result.returncode:
        detail = result.stderr.decode(errors="replace").strip() or "unknown ALSA error"
        raise AudioCaptureError(f"Playback to {device} failed: {detail}")
