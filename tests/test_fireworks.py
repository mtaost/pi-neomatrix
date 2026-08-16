import unittest

from display_modes.fireworks import Fireworks


class FakeDriver:
    width = 16
    height = 16


class FireworksTests(unittest.TestCase):
    def test_launches_and_explodes_into_palette_particles(self):
        mode = Fireworks(FakeDriver(), {"burst_size": 8, "palette": "neon"})
        self.assertEqual(mode.settings["palette"], "neon")
        mode._launch_rocket()
        mode.particles[0]["life"] = 1
        mode.step()
        self.assertTrue(any(particle["kind"] == "spark" for particle in mode.particles))
        sparks = [particle for particle in mode.particles if particle["kind"] == "spark"]
        self.assertEqual({particle["color"] for particle in sparks}, {sparks[0]["color"]})

    def test_can_fade_every_fragment_to_one_new_burst_color(self):
        mode = Fireworks(FakeDriver(), {"burst_size": 8, "palette": "neon", "fade_to_color": True})
        mode._launch_rocket()
        rocket = mode.particles[0]
        self.assertNotEqual(rocket["burst_color"], rocket["fade_color"])
        rocket["life"] = 1
        mode.step()
        sparks = [particle for particle in mode.particles if particle["kind"] == "spark"]
        self.assertEqual({particle["fade_color"] for particle in sparks}, {rocket["fade_color"]})


