from mode_settings import GAME_OF_LIFE_SETTINGS
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
        return PixelRain(driver)

    def stars(driver, options):
        from display_modes.pixelstars import PixelStars
        return PixelStars(driver)

    def tetris(driver, options):
        from display_modes.tetrisplayer import TetrisPlayer
        return TetrisPlayer(driver)

    def off(driver, options):
        from display_modes.displayoff import DisplayOff
        return DisplayOff(driver)

    specs = [
        ModeSpec("life", "Game of Life", life, settings_schema=GAME_OF_LIFE_SETTINGS),
        ModeSpec("spectrum", "Spectrum Analyzer", spectrum, ("microphone",)),
        ModeSpec("image", "Image Viewer", image, requires_asset=True),
        ModeSpec("thermal", "Thermal Camera", thermal, ("mlx90640",)),
        ModeSpec("rain", "Pixel Rain", rain),
        ModeSpec("stars", "Pixel Stars", stars),
        ModeSpec("tetris", "Tetris AI", tetris, ("tetris_ai",)),
        ModeSpec("off", "Display Off", off),
    ]
    return {spec.id: spec for spec in specs}
