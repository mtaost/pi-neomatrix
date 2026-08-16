"""Autonomous, animated Tetris powered by Cold Clear."""

from __future__ import annotations

import logging
import threading
import time

from PIL import Image

from cold_clear import ColdClearBot
from display_modes import module
from display_modes.tetris_engine import TetrisGame
from mode_settings import TETRIS_SETTINGS, normalize_settings


logger = logging.getLogger(__name__)

COLORS = {
    "I": (25, 165, 225), "J": (33, 65, 225), "L": (255, 91, 2),
    "S": (55, 200, 1), "Z": (225, 15, 10), "O": (255, 159, 2),
    "T": (175, 41, 138), "G": (105, 105, 105), None: (0, 0, 0),
}
GHOST_COLORS = {
    piece: tuple(channel // 3 for channel in color)
    for piece, color in COLORS.items()
    if piece not in (None, "G")
}
PREVIEW_CELLS = {
    "I": ((0, 1), (1, 1), (2, 1), (3, 1)),
    "O": ((1, 0), (2, 0), (1, 1), (2, 1)),
    "T": ((0, 1), (1, 1), (2, 1), (1, 0)),
    "L": ((0, 1), (1, 1), (2, 1), (2, 0)),
    "J": ((0, 1), (1, 1), (2, 1), (0, 0)),
    "S": ((0, 1), (1, 1), (1, 0), (2, 0)),
    "Z": ((0, 0), (1, 0), (1, 1), (2, 1)),
}


class TetrisPlayer(module.Module):
    """A 10-column Tetris game with a five-piece preview sidebar."""

    CLEAR_DURATION = 0.16
    GAME_OVER_DURATION = 1.5

    def __init__(self, driver, options=None, bot_factory=ColdClearBot):
        super().__init__(driver)
        self.settings = normalize_settings(TETRIS_SETTINGS, options)
        self.bot_factory = bot_factory
        self.image = Image.new("RGB", (self.width, self.height), "black")
        self.pixels = self.image.load()
        self.game = None
        self.bot = None
        self._state_lock = threading.RLock()
        self.phase = "new"
        self.phase_until = 0.0
        self._new_game()

    def _new_game(self):
        if self.bot:
            self.bot.close()
        self.game = TetrisGame()
        self.bot = self.bot_factory(self.game.initial_queue, self.settings["strategy"])
        if self.game.start_turn(self.bot.add_next_piece):
            self.bot.request_move()
            self.phase = "thinking"
        else:
            self._set_game_over()

    def _set_game_over(self):
        self.phase = "game_over"
        self.phase_until = time.monotonic() + self.GAME_OVER_DURATION

    def update_settings(self, settings):
        with self._state_lock:
            updated = normalize_settings(TETRIS_SETTINGS, settings, self.settings)
            strategy_changed = updated["strategy"] != self.settings["strategy"]
            self.settings = updated
            if strategy_changed:
                logger.info("Restarting Tetris for strategy profile: %s", updated["strategy"])
                self._new_game()

    def _advance(self):
        now = time.monotonic()
        if self.phase == "game_over":
            if now >= self.phase_until:
                self._new_game()
            return
        if self.phase == "thinking":
            move = self.bot.poll_move()
            if move:
                self.game.begin_bot_move(move, self.bot.add_next_piece)
                self.phase = "playing" if not self.game.game_over else "game_over"
                if self.game.game_over:
                    self._set_game_over()
            return
        if self.phase == "playing":
            if self.game.advance_animation():
                self.phase = "clearing"
                self.phase_until = now + (self.CLEAR_DURATION if self.game.last_cleared else 0)
            return
        if self.phase == "clearing" and now >= self.phase_until:
            injected = self.game.apply_pending_garbage(
                self.settings["simulated_garbage"],
                self._garbage_interval(self.settings["garbage_frequency"]),
                self.settings["garbage_messiness"] / 100.0,
                int(self.settings["garbage_lines"]),
            )
            if injected:
                self.bot.reset(self.game.as_bot_field(), self.game.b2b, self.game.combo)
            if self.game.game_over:
                self._set_game_over()
            elif self.game.start_turn(self.bot.add_next_piece):
                self.bot.request_move()
                self.phase = "thinking"
            else:
                self._set_game_over()

    @staticmethod
    def _garbage_interval(frequency):
        """Convert the UI's high-is-frequent control to locks between rows."""
        return 11 - int(frequency)

    def _draw(self):
        for x in range(self.width):
            for y in range(self.height):
                self.pixels[x, y] = (0, 0, 0)
        for board_y in range(min(16, len(self.game.board))):
            for x, cell in enumerate(self.game.board[board_y]):
                self.pixels[x, 15 - board_y] = COLORS[cell]
        if self.game.active:
            for x, y in self.game.ghost_cells():
                if 0 <= x < 10 and 0 <= y < 16:
                    self.pixels[x, 15 - y] = GHOST_COLORS[self.game.active.kind]
            for x, y in self.game.active.cells():
                if 0 <= x < 10 and 0 <= y < 16:
                    self.pixels[x, 15 - y] = COLORS[self.game.active.kind]
        for y in range(self.height):
            self.pixels[10, y] = (80, 80, 80)
        for index, piece in enumerate(self.game.preview):
            offset_y = 1 + index * 3
            if offset_y + 1 >= self.height:
                break
            for x, y in PREVIEW_CELLS[piece]:
                if 12 + x < self.width and offset_y + y < self.height:
                    self.pixels[12 + x, offset_y + y] = COLORS[piece]
        if self.phase == "game_over":
            for x in range(10):
                self.pixels[x, 7] = (120, 0, 0)

    def run(self):
        while not self.should_stop():
            with self._state_lock:
                self._advance()
                self._draw()
                animation_speed = float(self.settings["animation_speed"])
            self.display()
            if not self.wait(animation_speed):
                break

    def cleanup(self):
        with self._state_lock:
            if self.bot:
                self.bot.close()
                self.bot = None
