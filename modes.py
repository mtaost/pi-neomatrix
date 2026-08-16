from mode_settings import FIREWORKS_SETTINGS, GAME_OF_LIFE_SETTINGS, PIXEL_RAIN_SETTINGS, PIXEL_STARS_SETTINGS, TETRIS_SETTINGS
from dataclasses import dataclass, field
from typing import Callable


@dataclass(frozen=True)
class ModeSpec:
    id: str
    name: str
    factory: Callable
    capabilities: tuple[str, ...] = ()
    settings_schema: dict = field(default_factory=dict)
    requires_asset: bool = False

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "capabilities": list(self.capabilities),
            "settings_schema": self.settings_schema,
            "requires_asset": self.requires_asset,
        }


def build_mode_registry():
    def life(driver, options):
        from display_modes.gameoflife import GameOfLife
        return GameOfLife(driver, options)

    def spectrum(driver, options):
        from display_modes.spectrumanalyzer import SpectrumAnalyzer
        return SpectrumAnalyzer(driver)

    def image(driver, options):
        from display_modes.imageviewer import ImageViewer
        return ImageViewer(driver, str(options["asset_path"]))

    def thermal(driver, options):
        from display_modes.thermalcamera import ThermalCamera
        return ThermalCamera(driver)

    def rain(driver, options):
        from display_modes.pixelrain import PixelRain
        return PixelRain(driver, options)

    def stars(driver, options):
        from display_modes.pixelstars import PixelStars
        return PixelStars(driver, options)

    def fireworks(driver, options):
        from display_modes.fireworks import Fireworks
        return Fireworks(driver, options)

    def tetris(driver, options):
        from display_modes.tetrisplayer import TetrisPlayer
        return TetrisPlayer(driver, options)

    def off(driver, options):
        from display_modes.displayoff import DisplayOff
        return DisplayOff(driver)

    specs = [
        ModeSpec("life", "Game of Life", life, settings_schema=GAME_OF_LIFE_SETTINGS),
        ModeSpec("spectrum", "Spectrum Analyzer", spectrum, ("microphone",)),
        ModeSpec("image", "Image Viewer", image, requires_asset=True),
        ModeSpec("thermal", "Thermal Camera", thermal, ("mlx90640",)),
        ModeSpec("rain", "Pixel Rain", rain, settings_schema=PIXEL_RAIN_SETTINGS),
        ModeSpec("stars", "Pixel Stars", stars, settings_schema=PIXEL_STARS_SETTINGS),
        ModeSpec("fireworks", "Fireworks", fireworks, settings_schema=FIREWORKS_SETTINGS),
        ModeSpec("tetris", "Tetris AI", tetris, ("cold_clear",), settings_schema=TETRIS_SETTINGS),
        ModeSpec("off", "Display Off", off),
    ]
    return {spec.id: spec for spec in specs}
