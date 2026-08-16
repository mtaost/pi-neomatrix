"""Small ``ctypes`` binding for Cold Clear's supported C API.

Cold Clear does the expensive move search in its own thread.  This module
deliberately exposes only the operations the display mode needs; the Python
Tetris engine remains the source of truth for colours and rendering.
"""

from __future__ import annotations

import ctypes
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


PIECES = ("I", "O", "T", "L", "J", "S", "Z")
PIECE_TO_ID = {piece: index for index, piece in enumerate(PIECES)}
ID_TO_PIECE = dict(enumerate(PIECES))

MOVE_PROVIDED = 0
WAITING = 1
BOT_DEAD = 2

MOVE_LEFT = 0
MOVE_RIGHT = 1
MOVE_CW = 2
MOVE_CCW = 3
MOVE_DROP = 4

PROFILE_BALANCED = "balanced"
PROFILE_FAST = "fast"
PROFILE_PERFECT_CLEAR = "perfect_clear"
PROFILES = (PROFILE_BALANCED, PROFILE_FAST, PROFILE_PERFECT_CLEAR)


class _CCMove(ctypes.Structure):
    _fields_ = [
        ("hold", ctypes.c_bool),
        ("expected_x", ctypes.c_uint8 * 4),
        ("expected_y", ctypes.c_uint8 * 4),
        ("movement_count", ctypes.c_uint8),
        ("movements", ctypes.c_int * 32),
        ("nodes", ctypes.c_uint32),
        ("depth", ctypes.c_uint32),
        ("original_rank", ctypes.c_uint32),
    ]


class _CCOptions(ctypes.Structure):
    _fields_ = [
        ("mode", ctypes.c_int),
        ("spawn_rule", ctypes.c_int),
        ("pcloop", ctypes.c_int),
        ("min_nodes", ctypes.c_uint32),
        ("max_nodes", ctypes.c_uint32),
        ("threads", ctypes.c_uint32),
        ("use_hold", ctypes.c_bool),
        ("speculate", ctypes.c_bool),
    ]


class _CCWeights(ctypes.Structure):
    _fields_ = [
        ("back_to_back", ctypes.c_int32), ("bumpiness", ctypes.c_int32),
        ("bumpiness_sq", ctypes.c_int32), ("row_transitions", ctypes.c_int32),
        ("height", ctypes.c_int32), ("top_half", ctypes.c_int32),
        ("top_quarter", ctypes.c_int32), ("jeopardy", ctypes.c_int32),
        ("cavity_cells", ctypes.c_int32), ("cavity_cells_sq", ctypes.c_int32),
        ("overhang_cells", ctypes.c_int32), ("overhang_cells_sq", ctypes.c_int32),
        ("covered_cells", ctypes.c_int32), ("covered_cells_sq", ctypes.c_int32),
        ("tslot", ctypes.c_int32 * 4), ("well_depth", ctypes.c_int32),
        ("max_well_depth", ctypes.c_int32), ("well_column", ctypes.c_int32 * 10),
        ("b2b_clear", ctypes.c_int32), ("clear1", ctypes.c_int32),
        ("clear2", ctypes.c_int32), ("clear3", ctypes.c_int32),
        ("clear4", ctypes.c_int32), ("tspin1", ctypes.c_int32),
        ("tspin2", ctypes.c_int32), ("tspin3", ctypes.c_int32),
        ("mini_tspin1", ctypes.c_int32), ("mini_tspin2", ctypes.c_int32),
        ("perfect_clear", ctypes.c_int32), ("combo_garbage", ctypes.c_int32),
        ("move_time", ctypes.c_int32), ("wasted_t", ctypes.c_int32),
        ("use_bag", ctypes.c_bool), ("timed_jeopardy", ctypes.c_bool),
        ("stack_pc_damage", ctypes.c_bool),
    ]


@dataclass(frozen=True)
class ColdClearMove:
    use_hold: bool
    cells: tuple[tuple[int, int], ...]
    movements: tuple[int, ...]


class ColdClearBot:
    """One Cold Clear asynchronous bot instance."""

    def __init__(self, pieces: Iterable[str], strategy: str = PROFILE_BALANCED, library_path=None):
        if strategy not in PROFILES:
            raise ValueError(f"Unknown Cold Clear strategy: {strategy}")
        pieces = tuple(pieces)
        if not pieces:
            raise ValueError("Cold Clear requires at least one queued piece.")
        try:
            self._library = self._load_library(library_path)
            self._configure_functions()
            options = _CCOptions()
            weights = _CCWeights()
            self._library.cc_default_options(ctypes.byref(options))
            if strategy == PROFILE_FAST:
                self._library.cc_fast_weights(ctypes.byref(weights))
                options.max_nodes = 75_000
            else:
                self._library.cc_default_weights(ctypes.byref(weights))
                options.max_nodes = 250_000
            options.mode = 0  # CC_0G: paths can be replayed one action at a time.
            options.spawn_rule = 0  # CC_ROW_19_OR_20
            options.pcloop = 1 if strategy == PROFILE_PERFECT_CLEAR else 0
            options.min_nodes = 0
            options.threads = 1
            options.use_hold = True
            options.speculate = True
            queue = (ctypes.c_int * len(pieces))(*(PIECE_TO_ID[piece] for piece in pieces))
            self._bot = self._library.cc_launch_async(
                ctypes.byref(options), ctypes.byref(weights), None, queue, len(pieces)
            )
            if not self._bot:
                raise RuntimeError("Cold Clear could not launch its bot thread.")
        except KeyError as error:
            raise ValueError(f"Unknown Tetris piece: {error.args[0]}") from error

    @staticmethod
    def default_library_path() -> Path:
        configured = os.environ.get("NEOMATRIX_COLD_CLEAR_LIBRARY")
        if configured:
            return Path(configured)
        return Path(__file__).resolve().parent / "third_party" / "cold-clear" / "target" / "release" / "libcold_clear.so"

    @classmethod
    def _load_library(cls, library_path):
        path = Path(library_path) if library_path else cls.default_library_path()
        if not path.is_file():
            raise RuntimeError(
                f"Cold Clear library not found at {path}. Run scripts/build-cold-clear.sh first."
            )
        try:
            return ctypes.CDLL(str(path))
        except OSError as error:
            raise RuntimeError(f"Unable to load Cold Clear library at {path}: {error}") from error

    def _configure_functions(self):
        library = self._library
        library.cc_default_options.argtypes = [ctypes.POINTER(_CCOptions)]
        library.cc_default_weights.argtypes = [ctypes.POINTER(_CCWeights)]
        library.cc_fast_weights.argtypes = [ctypes.POINTER(_CCWeights)]
        library.cc_launch_async.argtypes = [
            ctypes.POINTER(_CCOptions), ctypes.POINTER(_CCWeights), ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_int), ctypes.c_uint32,
        ]
        library.cc_launch_async.restype = ctypes.c_void_p
        library.cc_destroy_async.argtypes = [ctypes.c_void_p]
        library.cc_add_next_piece_async.argtypes = [ctypes.c_void_p, ctypes.c_int]
        library.cc_request_next_move.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        library.cc_poll_next_move.argtypes = [
            ctypes.c_void_p, ctypes.POINTER(_CCMove), ctypes.c_void_p, ctypes.c_void_p,
        ]
        library.cc_poll_next_move.restype = ctypes.c_int
        library.cc_reset_async.argtypes = [
            ctypes.c_void_p, ctypes.POINTER(ctypes.c_bool), ctypes.c_bool, ctypes.c_uint32,
        ]

    def add_next_piece(self, piece: str):
        self._require_open()
        self._library.cc_add_next_piece_async(self._bot, PIECE_TO_ID[piece])

    def request_move(self):
        self._require_open()
        self._library.cc_request_next_move(self._bot, 0)

    def poll_move(self) -> ColdClearMove | None:
        self._require_open()
        move = _CCMove()
        status = self._library.cc_poll_next_move(self._bot, ctypes.byref(move), None, None)
        if status == WAITING:
            return None
        if status == BOT_DEAD:
            raise RuntimeError("Cold Clear bot stopped unexpectedly.")
        if status != MOVE_PROVIDED:
            raise RuntimeError(f"Cold Clear returned an unknown poll status: {status}")
        return ColdClearMove(
            use_hold=bool(move.hold),
            cells=tuple(zip(move.expected_x, move.expected_y)),
            movements=tuple(move.movements[:move.movement_count]),
        )


    def reset(self, board, b2b=False, combo=0):
        """Reset Cold Clear after a garbage insertion using bottom-left row order."""
        self._require_open()
        if len(board) != 40 or any(len(row) != 10 for row in board):
            raise ValueError("Cold Clear reset board must be 40 rows by 10 columns.")
        field = (ctypes.c_bool * 400)(*(bool(cell) for row in board for cell in row))
        self._library.cc_reset_async(self._bot, field, bool(b2b), int(combo))

    def close(self):
        if getattr(self, "_bot", None):
            self._library.cc_destroy_async(self._bot)
            self._bot = None

    def _require_open(self):
        if not getattr(self, "_bot", None):
            raise RuntimeError("Cold Clear bot is closed.")
