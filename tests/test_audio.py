import unittest

import numpy as np

from display_modes.spectrumanalyzer import SpectrumAnalyzer
from hw.audio import AlsaDevice, AudioCaptureError, pcm_s32le_to_float, select_device, select_loudest_channel


class FakeDriver:
    width = 16
    height = 16


class AudioHelpersTests(unittest.TestCase):
    def test_pcm_s32le_conversion_preserves_full_scale_values(self):
        raw = np.array([0, 2**30, -(2**30)], dtype="<i4").tobytes()
        np.testing.assert_allclose(pcm_s32le_to_float(raw), [0.0, 0.5, -0.5])

    def test_ambiguous_devices_require_an_explicit_selection(self):
        devices = [
            AlsaDevice(0, 0, "hdmi", "HDMI", "PCM", "capture"),
            AlsaDevice(1, 0, "usb", "USB", "Mic", "capture"),
        ]
        with self.assertRaises(AudioCaptureError):
            select_device(devices)

    def test_single_i2s_device_is_selected_even_with_other_cards(self):
        devices = [
            AlsaDevice(0, 0, "hdmi", "HDMI", "PCM", "capture"),
            AlsaDevice(1, 0, "sndrpii2scard", "snd_rpi_i2s_card", "I2S", "capture"),
        ]
        self.assertEqual(select_device(devices), "hw:1,0")

    def test_two_channel_capture_selects_the_active_inmp441_slot(self):
        quiet = np.array([0.001, -0.001, 0.001, -0.001], dtype=np.float32)
        active = np.array([0.4, -0.4, 0.4, -0.4], dtype=np.float32)
        interleaved = np.column_stack((quiet, active)).reshape(-1)
        np.testing.assert_allclose(select_loudest_channel(interleaved, 2), active)


class SpectrumBinningTests(unittest.TestCase):
    def test_logarithmic_bands_produce_a_visible_tone_column(self):
        analyzer = SpectrumAnalyzer(FakeDriver())
        time = np.arange(analyzer.CHUNK_SIZE) / analyzer.SAMPLE_RATE
        samples = (0.4 * np.sin(2 * np.pi * 1_000 * time)).astype(np.float32)
        levels = analyzer._calculate_levels(samples)
        tone_band = next(
            index
            for index, (low, high) in enumerate(zip(analyzer.bin_edges[:-1], analyzer.bin_edges[1:]))
            if low <= 1_000 < high
        )
        self.assertGreater(levels[tone_band], 0)
        self.assertLessEqual(max(levels), analyzer.height)


if __name__ == "__main__":
    unittest.main()
