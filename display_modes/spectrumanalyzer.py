import logging
import time

import numpy as np

from display_modes import module
from hw.audio import AlsaCapture, AudioCaptureError


logger = logging.getLogger(__name__)


class SpectrumAnalyzer(module.Module):
    """16-band spectrum analyzer backed by the Pi's native ALSA I2S capture."""

    SAMPLE_RATE = 48_000
    CHUNK_SIZE = 2_048
    MIN_FREQUENCY = 32
    MAX_FREQUENCY = 20_000
    NOISE_FLOOR_DBFS = -72.0
    FULL_SCALE_DBFS = -24.0
    DECAY = 0.78
    BAND_WEIGHTS = np.array(
        [0.85, 0.85, 0.9, 0.95, 1.0, 1.0, 1.05, 1.05, 1.1, 1.1, 1.1, 1.2, 1.2, 1.25, 1.3, 1.3]
    )

    def __init__(self, driver, capture_factory=AlsaCapture):
        if driver.width != 16 or driver.height != 16:
            raise ValueError(f"Unacceptable Dimensions:{driver.width}x{driver.height}")
        super().__init__(driver)
        self.capture_factory = capture_factory
        self.capture = None
        self.levels = np.zeros(self.width, dtype=float)
        self.window = np.hanning(self.CHUNK_SIZE).astype(np.float32)
        self.frequencies = np.fft.rfftfreq(self.CHUNK_SIZE, d=1.0 / self.SAMPLE_RATE)
        self.bin_edges = self._generate_bins(self.width)

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

    @staticmethod
    def _spectrum_colors():
        return [(0, 255, 0)] * 11 + [(255, 255, 0)] * 3 + [(255, 0, 0)] * 2

    def _open_capture(self):
        capture = self.capture_factory(sample_rate=self.SAMPLE_RATE, channels=2, period_frames=self.CHUNK_SIZE)
        capture.start()
        self.capture = capture
        logger.info("Spectrum analyzer capturing from %s at %d Hz", capture.device, self.SAMPLE_RATE)

    def _close_capture(self):
        capture, self.capture = self.capture, None
        if capture:
            capture.close()

    def run(self):
        colors = self._spectrum_colors()
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
                levels = self._calculate_levels(self.capture.read(self.CHUNK_SIZE))
                self.driver.clear(self.image)
                for x, height in enumerate(levels):
                    for y in range(height):
                        self.pixels[x, self.height - 1 - y] = colors[y]
                self.display()
                logger.debug("Spectrum FPS: %.2f", 1.0 / max(time.monotonic() - start, 1e-6))
            except AudioCaptureError as error:
                logger.warning("Spectrum audio stream failed; reconnecting: %s", error)
                self._close_capture()
                self.wait(1.0)

    def cleanup(self):
        self._close_capture()
        super().cleanup()
