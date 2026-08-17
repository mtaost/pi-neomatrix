import logging
import time
import colorsys

import numpy as np

from display_modes import module
from hw.audio import AlsaCapture, AudioCaptureError
from mode_settings import SPECTRUM_SETTINGS, hex_to_rgb, normalize_settings


logger = logging.getLogger(__name__)


class SpectrumAnalyzer(module.Module):
    """16-band spectrum analyzer backed by the Pi's native ALSA I2S capture."""

    SAMPLE_RATE = 48_000
    # A 4,096-sample FFT resolves 11.7 Hz bins at 48 kHz. This keeps the
    # 32–46 Hz first logarithmic display band distinct without borrowing a
    # sample from its neighboring band. Analyze it with 50% overlap so frames
    # still update every 2,048 samples (about 43 ms).
    CHUNK_SIZE = 4_096
    HOP_SIZE = 2_048
    MIN_FREQUENCY = 32
    MAX_FREQUENCY = 12_000
    NOISE_FLOOR_DBFS = -72.0
    FULL_SCALE_DBFS = -24.0
    AUTO_GAIN_TARGET_DBFS = -30.0
    # Require a signal meaningfully above the measured room floor before
    # tracking it, then keep tracking until it has fallen below this lower
    # threshold. The gap prevents background noise from repeatedly toggling
    # automatic gain on and off.
    AUTO_GAIN_START_DBFS = -62.0
    AUTO_GAIN_SILENCE_DBFS = -66.0
    AUTO_GAIN_RISE = 0.08
    AUTO_GAIN_FALL = 0.35
    AUTO_GAIN_IDLE_RETURN = 0.025
    DECAY = 0.78
    PEAK_HOLD_SECONDS = 0.35
    PEAK_GRAVITY = 24.0
    PEAK_COLOR = (255, 255, 255)
    BAND_WEIGHTS = np.array(
        [0.85, 0.85, 0.9, 0.95, 1.0, 1.0, 1.05, 1.05, 1.1, 1.1, 1.1, 1.2, 1.2, 1.25, 1.3, 1.3]
    )

    def __init__(self, driver, options=None, capture_factory=AlsaCapture):
        if driver.width != 16 or driver.height != 16:
            raise ValueError(f"Unacceptable Dimensions:{driver.width}x{driver.height}")
        super().__init__(driver)
        self.capture_factory = capture_factory
        self.capture = None
        self.levels = np.zeros(self.width, dtype=float)
        self.sample_buffer = np.zeros(self.CHUNK_SIZE, dtype=np.float32)
        self.peak_levels = np.zeros(self.width, dtype=float)
        self.peak_hold_until = np.zeros(self.width, dtype=float)
        self.peak_velocities = np.zeros(self.width, dtype=float)
        self._peaks_updated_at = None
        self.window = np.hanning(self.CHUNK_SIZE).astype(np.float32)
        self.frequencies = np.fft.rfftfreq(self.CHUNK_SIZE, d=1.0 / self.SAMPLE_RATE)
        self.bin_edges = self._generate_bins(self.width)
        self.update_settings(options)

    def update_settings(self, values=None):
        was_auto_gain = getattr(self, "settings", {}).get("auto_gain", False)
        had_markers = getattr(self, "settings", {}).get("peak_markers", False)
        self.settings = normalize_settings(SPECTRUM_SETTINGS, values, getattr(self, "settings", None))
        self.fixed_color = hex_to_rgb(self.settings["fixed_color"])
        if not was_auto_gain and self.settings["auto_gain"]:
            self.auto_gain_db = self.settings["gain_db"]
            self.auto_gain_tracking = False
        elif not hasattr(self, "auto_gain_db"):
            self.auto_gain_db = self.settings["gain_db"]
            self.auto_gain_tracking = False
        if had_markers and not self.settings["peak_markers"]:
            self._reset_peak_markers()

    def _reset_peak_markers(self):
        self.peak_levels.fill(0)
        self.peak_hold_until.fill(0)
        self.peak_velocities.fill(0)
        self._peaks_updated_at = None

    def _generate_bins(self, n_bins):
        """Generate the original logarithmic bands, clamped to Nyquist."""
        upper = min(self.MAX_FREQUENCY, self.SAMPLE_RATE // 2)
        ratio = (upper / self.MIN_FREQUENCY) ** (1.0 / n_bins)
        return np.array([self.MIN_FREQUENCY * ratio**index for index in range(n_bins + 1)])

    def _calculate_levels(self, samples):
        """Map one PCM chunk to smoothed LED heights using logarithmic FFT bands."""
        if len(samples) != self.CHUNK_SIZE:
            raise ValueError(f"Expected {self.CHUNK_SIZE} samples, received {len(samples)}")
        centered = samples - np.mean(samples)
        gain = 10 ** (self._effective_gain_db(centered) / 20.0)
        centered *= gain
        spectrum = np.abs(np.fft.rfft(centered * self.window)) * (2.0 / self.window.sum())
        heights = np.zeros(self.width, dtype=float)
        for index, (low, high) in enumerate(zip(self.bin_edges[:-1], self.bin_edges[1:])):
            band = spectrum[(self.frequencies >= low) & (self.frequencies < high)]
            if band.size:
                level_dbfs = 20.0 * np.log10(max(float(np.sqrt(np.mean(band**2))), 1e-12))
                normalized = (level_dbfs - self.NOISE_FLOOR_DBFS) / (self.FULL_SCALE_DBFS - self.NOISE_FLOOR_DBFS)
                heights[index] = normalized * self.height * self.BAND_WEIGHTS[index]
        heights = np.clip(heights, 0, self.height)
        self.levels = np.maximum(heights, self.levels * self.DECAY)
        return self.levels.astype(int)

    def _effective_gain_db(self, centered_samples):
        if not self.settings["auto_gain"]:
            return self.settings["gain_db"]
        rms = float(np.sqrt(np.mean(np.square(centered_samples, dtype=np.float64))))
        input_dbfs = 20 * np.log10(max(rms, 1e-12))
        if input_dbfs >= self.AUTO_GAIN_START_DBFS:
            self.auto_gain_tracking = True
        if input_dbfs <= self.AUTO_GAIN_SILENCE_DBFS:
            self.auto_gain_tracking = False
        if not self.auto_gain_tracking:
            # Do not preserve a gain that was raised for an earlier sound.
            # Return gradually so the visualizer remains calm between tracks.
            self.auto_gain_db += (
                self.settings["gain_db"] - self.auto_gain_db
            ) * self.AUTO_GAIN_IDLE_RETURN
            return self.auto_gain_db
        desired_gain = np.clip(
            self.AUTO_GAIN_TARGET_DBFS - input_dbfs,
            SPECTRUM_SETTINGS["gain_db"]["min"],
            SPECTRUM_SETTINGS["gain_db"]["max"],
        )
        responsiveness = self.AUTO_GAIN_FALL if desired_gain < self.auto_gain_db else self.AUTO_GAIN_RISE
        self.auto_gain_db += (desired_gain - self.auto_gain_db) * responsiveness
        return self.auto_gain_db

    def _append_samples(self, samples):
        """Advance the overlapping FFT window by one captured hop."""
        if len(samples) != self.HOP_SIZE:
            raise ValueError(f"Expected {self.HOP_SIZE} samples, received {len(samples)}")
        self.sample_buffer = np.concatenate((self.sample_buffer[self.HOP_SIZE:], samples))
        return self.sample_buffer

    @staticmethod
    def _interpolate(stops, position):
        position = min(1.0, max(0.0, position))
        scaled = position * (len(stops) - 1)
        lower = int(scaled)
        upper = min(lower + 1, len(stops) - 1)
        blend = scaled - lower
        return tuple(round(stops[lower][index] * (1 - blend) + stops[upper][index] * blend) for index in range(3))

    def _bar_color(self, x, y, height):
        palette = self.settings["palette"]
        if palette == "fixed":
            return self.fixed_color
        position = y / max(self.height - 1, 1)
        if palette == "rainbow_gradient":
            hue = (x / max(self.width, 1) + position * 0.18) % 1.0
            return tuple(round(component * 255) for component in colorsys.hsv_to_rgb(hue, 1.0, 1.0))
        gradients = {
            "classic": ((0, 255, 0), (255, 255, 0), (255, 0, 0)),
            "ocean": ((0, 255, 220), (0, 110, 255), (180, 0, 255)),
            "sunset": ((255, 230, 100), (255, 120, 55), (235, 35, 110)),
        }
        return self._interpolate(gradients[palette], position)

    def _update_peak_markers(self, levels, now):
        """Hold new maxima briefly before applying accelerating downward motion."""
        previous = self._peaks_updated_at
        elapsed = 0.0 if previous is None else max(0.0, now - previous)
        self._peaks_updated_at = now
        for x, level in enumerate(levels):
            if level >= self.peak_levels[x]:
                self.peak_levels[x] = level
                self.peak_hold_until[x] = now + self.PEAK_HOLD_SECONDS
                self.peak_velocities[x] = 0.0
            elif now >= self.peak_hold_until[x]:
                self.peak_velocities[x] += self.PEAK_GRAVITY * elapsed
                self.peak_levels[x] = max(level, self.peak_levels[x] - self.peak_velocities[x] * elapsed)

    def _draw_peak_markers(self, levels):
        for x, peak in enumerate(self.peak_levels):
            if peak <= levels[x]:
                continue
            if self.settings["mirror_from_center"]:
                peak_offset = min(self.height // 2 - 1, int(np.ceil(peak / 2)))
                bar_offset = int(np.ceil(levels[x] / 2))
                if peak_offset <= bar_offset:
                    continue
                self.pixels[x, self.height // 2 + peak_offset] = self.PEAK_COLOR
                self.pixels[x, self.height // 2 - 1 - peak_offset] = self.PEAK_COLOR
                continue
            row = self.height - 1 - min(self.height - 1, int(np.ceil(peak)))
            self.pixels[x, row] = self.PEAK_COLOR

    def _draw_bars(self, levels):
        if self.settings["mirror_from_center"]:
            half_height = self.height // 2
            for x, height in enumerate(levels):
                for offset in range(int(np.ceil(height / 2))):
                    color = self._bar_color(x, offset * 2, height)
                    self.pixels[x, half_height + offset] = color
                    self.pixels[x, half_height - 1 - offset] = color
            return
        for x, height in enumerate(levels):
            for y in range(height):
                self.pixels[x, self.height - 1 - y] = self._bar_color(x, y, height)

    def _open_capture(self):
        capture = self.capture_factory(sample_rate=self.SAMPLE_RATE, channels=2, period_frames=self.HOP_SIZE)
        capture.start()
        self.capture = capture
        logger.info("Spectrum analyzer capturing from %s at %d Hz", capture.device, self.SAMPLE_RATE)

    def _close_capture(self):
        capture, self.capture = self.capture, None
        if capture:
            capture.close()

    def run(self):
        while not self.should_stop():
            if self.capture is None:
                try:
                    self._open_capture()
                except AudioCaptureError as error:
                    logger.warning("Spectrum audio unavailable: %s", error)
                    self.wait(2.0)
                    continue
            try:
                start = time.monotonic()
                levels = self._calculate_levels(self._append_samples(self.capture.read(self.HOP_SIZE)))
                self.driver.clear(self.image)
                self._draw_bars(levels)
                if self.settings["peak_markers"]:
                    self._update_peak_markers(levels, time.monotonic())
                    self._draw_peak_markers(levels)
                self.display()
                logger.debug("Spectrum FPS: %.2f", 1.0 / max(time.monotonic() - start, 1e-6))
            except AudioCaptureError as error:
                logger.warning("Spectrum audio stream failed; reconnecting: %s", error)
                self._close_capture()
                self.wait(1.0)

    def cleanup(self):
        self._close_capture()
        super().cleanup()
