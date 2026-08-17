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
    def test_logarithmic_bands_stop_at_twelve_kilohertz(self):
        analyzer = SpectrumAnalyzer(FakeDriver())
        self.assertAlmostEqual(analyzer.bin_edges[-1], 12_000)

    def test_lowest_band_has_its_own_resolved_fft_sample(self):
        analyzer = SpectrumAnalyzer(FakeDriver())
        frequency = analyzer.SAMPLE_RATE / analyzer.CHUNK_SIZE * 3
        time = np.arange(analyzer.CHUNK_SIZE) / analyzer.SAMPLE_RATE
        samples = (0.4 * np.sin(2 * np.pi * frequency * time)).astype(np.float32)
        self.assertGreater(analyzer._calculate_levels(samples)[0], 0)

    def test_overlapping_fft_advances_on_a_half_window_hop(self):
        analyzer = SpectrumAnalyzer(FakeDriver())
        hop = np.full(analyzer.HOP_SIZE, 0.25, dtype=np.float32)
        window = analyzer._append_samples(hop)
        self.assertTrue(np.all(window[:analyzer.HOP_SIZE] == 0))
        self.assertTrue(np.all(window[analyzer.HOP_SIZE:] == 0.25))

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

    def test_live_settings_change_gain_and_palette(self):
        analyzer = SpectrumAnalyzer(FakeDriver(), {"gain_db": 18, "palette": "fixed", "fixed_color": "#123456"})
        self.assertEqual(analyzer.settings["gain_db"], 18.0)
        self.assertEqual(analyzer._bar_color(4, 8, 16), (18, 52, 86))

        analyzer.update_settings({"palette": "ocean"})
        self.assertNotEqual(analyzer._bar_color(4, 0, 16), analyzer._bar_color(4, 15, 16))

    def test_automatic_gain_tracks_signal_without_amplifying_silence(self):
        analyzer = SpectrumAnalyzer(FakeDriver(), {"auto_gain": True})
        quiet_signal = np.full(analyzer.CHUNK_SIZE, 0.01, dtype=np.float32)
        quiet_signal[::2] *= -1
        self.assertGreater(analyzer._effective_gain_db(quiet_signal), 0)

        analyzer.auto_gain_db = 8
        self.assertEqual(analyzer._effective_gain_db(np.zeros(analyzer.CHUNK_SIZE)), 8)

        loud_signal = np.full(analyzer.CHUNK_SIZE, 0.8, dtype=np.float32)
        loud_signal[::2] *= -1
        self.assertLess(analyzer._effective_gain_db(loud_signal), 8)

    def test_peak_markers_hold_then_fall_with_gravity(self):
        analyzer = SpectrumAnalyzer(FakeDriver(), {"peak_markers": True})
        loud = np.array([8] + [0] * 15)
        quiet = np.zeros(16, dtype=int)
        analyzer._update_peak_markers(loud, now=0.0)
        analyzer._update_peak_markers(quiet, now=0.2)
        self.assertEqual(analyzer.peak_levels[0], 8)

        analyzer._update_peak_markers(quiet, now=0.7)
        self.assertLess(analyzer.peak_levels[0], 8)
        self.assertGreater(analyzer.peak_levels[0], 0)

        analyzer.update_settings({"peak_markers": False})
        self.assertTrue(np.all(analyzer.peak_levels == 0))

    def test_center_mirror_draws_symmetric_bars(self):
        analyzer = SpectrumAnalyzer(FakeDriver(), {"mirror_from_center": True, "palette": "fixed", "fixed_color": "#123456"})
        analyzer._draw_bars(np.array([8] + [0] * 15))
        for y in (4, 5, 6, 7, 8, 9, 10, 11):
            self.assertEqual(analyzer.pixels[0, y], (18, 52, 86))
        self.assertEqual(analyzer.pixels[0, 3], (0, 0, 0))
        self.assertEqual(analyzer.pixels[0, 12], (0, 0, 0))


if __name__ == "__main__":
    unittest.main()
