"""Rules, animation state, and garbage handling for the Tetris display mode."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import random

from cold_clear import MOVE_CCW, MOVE_CW, MOVE_DROP, MOVE_LEFT, MOVE_RIGHT


WIDTH = 10
HEIGHT = 40
PIECES = ("I", "J", "L", "O", "S", "T", "Z")
# Cold Clear's perfect-clear loop needs eleven queued pieces when hold is
# enabled. Keep that lookahead internally while displaying only five pieces.
QUEUE_LOOKAHEAD = 11

_NORTH_CELLS = {
    "I": ((-1, 0), (0, 0), (1, 0), (2, 0)),
    "O": ((0, 0), (1, 0), (0, 1), (1, 1)),
    "T": ((-1, 0), (0, 0), (1, 0), (0, 1)),
    "L": ((-1, 0), (0, 0), (1, 0), (1, 1)),
    "J": ((-1, 0), (0, 0), (1, 0), (-1, 1)),
    "S": ((-1, 0), (0, 0), (0, 1), (1, 1)),
    "Z": ((-1, 1), (0, 1), (0, 0), (1, 0)),
}
_ROTATIONS = ("N", "E", "S", "W")

# These are Cold Clear/libtetris's SRS rotation points, not a separate ruleset.
_KICKS = {
    "O": {"N": ((0, 0),) * 5, "E": ((0, -1),) * 5, "S": ((-1, -1),) * 5, "W": ((-1, 0),) * 5},
    "I": {
        "N": ((0, 0), (-1, 0), (2, 0), (-1, 0), (2, 0)),
        "E": ((-1, 0), (0, 0), (0, 0), (0, 1), (0, -2)),
        "S": ((-1, 1), (1, 1), (-2, 1), (1, 0), (-2, 0)),
        "W": ((0, 1), (0, 1), (0, 1), (0, -1), (0, 2)),
    },
}
_JLSTZ_KICKS = {
    "N": ((0, 0),) * 5,
    "E": ((0, 0), (1, 0), (1, -1), (0, 2), (1, 2)),
    "S": ((0, 0),) * 5,
    "W": ((0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)),
}


class TetrisSyncError(RuntimeError):
    """Cold Clear's advertised lock position did not match the replayed path."""


@dataclass
class FallingPiece:
    kind: str
    x: int = 4
    y: int = 19
    rotation: str = "N"
    tspin: str = "none"

    def cells(self):
        offsets = _NORTH_CELLS[self.kind]
        if self.rotation == "E":
            offsets = tuple((y, -x) for x, y in offsets)
        elif self.rotation == "S":
            offsets = tuple((-x, -y) for x, y in offsets)
        elif self.rotation == "W":
            offsets = tuple((-y, x) for x, y in offsets)
        return tuple((self.x + x, self.y + y) for x, y in offsets)


class TetrisGame:
    """A compact, deterministic game model in Cold Clear's bottom-left coordinates."""

    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        self.board = [[None for _ in range(WIDTH)] for _ in range(HEIGHT)]
        self.queue = deque()
        self.hold_piece = None
        self.active = None
        self.pending_actions = deque()
        self.expected_cells = None
        self.hard_drop_preview = False
        self.combo = 0
        self.b2b = False
        self.locks_since_garbage = 0
        self.garbage_hole = None
        self.game_over = False
        self.last_cleared = ()
        # Cold Clear's queue includes the active piece.
        self._extend_queue(QUEUE_LOOKAHEAD + 1)

    @property
    def initial_queue(self):
        return tuple(self.queue)

    @property
    def preview(self):
        return tuple(self.queue)[:5]

    def _extend_queue(self, length):
        added = []
        while len(self.queue) < length:
            if not hasattr(self, "_bag") or not self._bag:
                self._bag = list(PIECES)
                self.rng.shuffle(self._bag)
            piece = self._bag.pop()
            self.queue.append(piece)
            added.append(piece)
        return tuple(added)

    def start_turn(self, add_piece=None):
        if self.game_over:
            return False
        if self.active is not None:
            raise RuntimeError("Cannot start a turn while a piece is active.")
        self.active = self._spawn(self.queue.popleft())
        added = self._extend_queue(QUEUE_LOOKAHEAD)
        if add_piece:
            for piece in added:
                add_piece(piece)
        if self.active is None:
            self.game_over = True
            return False
        return True

    def begin_bot_move(self, move, add_piece=None):
        if not self.active:
            raise RuntimeError("Cannot replay a move without an active piece.")
        if move.use_hold:
            held = self.hold_piece
            self.hold_piece = self.active.kind
            self.active = self._spawn(held or self.queue.popleft())
            added = self._extend_queue(QUEUE_LOOKAHEAD)
            if add_piece:
                for piece in added:
                    add_piece(piece)
            if self.active is None:
                self.game_over = True
                return
        self.pending_actions = deque(move.movements)
        self.expected_cells = frozenset(move.cells)
        self.hard_drop_preview = False

    def advance_animation(self):
        """Run one visual action.  Returns True once the placement has locked."""
        if not self.active:
            return False
        if self.hard_drop_preview:
            self.hard_drop_preview = False
            self._sonic_drop()
            # Cold Clear's SonicDrop is a movement, not a lock: T-spin paths
            # can rotate or shift again after reaching the ground.
            if self.pending_actions:
                return False
            return self._finish_move()
        if not self.pending_actions:
            # In CC_0G mode Cold Clear optimizes low stacks by returning a
            # ground placement with no explicit SonicDrop input. Show its
            # landing spot for one frame, then hard drop there.
            if frozenset(self.active.cells()) != self.expected_cells:
                self.hard_drop_preview = True
                return False
            return self._finish_move()
        action = self.pending_actions.popleft()
        if action == MOVE_LEFT:
            self._shift(-1, 0)
        elif action == MOVE_RIGHT:
            self._shift(1, 0)
        elif action == MOVE_CW:
            self._rotate(True)
        elif action == MOVE_CCW:
            self._rotate(False)
        elif action == MOVE_DROP:
            self.hard_drop_preview = True
        else:
            raise TetrisSyncError(f"Unknown Cold Clear movement: {action}")
        return False

    def _finish_move(self):
        if frozenset(self.active.cells()) != self.expected_cells:
            raise TetrisSyncError(
                f"Cold Clear path ended at {sorted(self.active.cells())}, expected {sorted(self.expected_cells)}"
            )
        for x, y in self.active.cells():
            if not 0 <= y < HEIGHT or self.board[y][x] is not None:
                raise TetrisSyncError("Cold Clear move attempted an invalid lock location.")
            self.board[y][x] = self.active.kind
        self.last_cleared = tuple(index for index, row in enumerate(self.board) if all(row))
        if self.last_cleared:
            self.board = [row for row in self.board if not all(row)]
            self.board.extend([[None for _ in range(WIDTH)] for _ in self.last_cleared])
            self.combo += 1
            self.b2b = len(self.last_cleared) == 4 or self.active.tspin != "none"
        else:
            self.combo = 0
        self.active = None
        self.expected_cells = None
        self.hard_drop_preview = False
        self.locks_since_garbage += 1
        return True

    def apply_pending_garbage(self, enabled, frequency, messiness, lines=1):
        """Insert standard garbage rows after a completed turn when due."""
        if not enabled or self.locks_since_garbage < frequency or self.game_over:
            return False
        self.locks_since_garbage = 0
        for _ in range(int(lines)):
            if self.garbage_hole is None:
                self.garbage_hole = self.rng.randrange(WIDTH)
            elif self.rng.random() < messiness:
                choices = [column for column in range(WIDTH) if column != self.garbage_hole]
                self.garbage_hole = self.rng.choice(choices)
            overflow = any(self.board[-1])
            self.board.pop()
            self.board.insert(0, [None if x == self.garbage_hole else "G" for x in range(WIDTH)])
            if overflow:
                self.game_over = True
                break
        return True

    def as_bot_field(self):
        return [[cell is not None for cell in row] for row in self.board]

    def _obstructed(self, piece):
        return any(x < 0 or x >= WIDTH or y < 0 or y >= HEIGHT or self.board[y][x] is not None for x, y in piece.cells())

    def _spawn(self, piece):
        """Match Cold Clear's CC_ROW_19_OR_20 spawn rule."""
        active = FallingPiece(piece)
        if not self._obstructed(active):
            return active
        active.y += 1
        return None if self._obstructed(active) else active

    def _shift(self, dx, dy):
        self.active.x += dx
        self.active.y += dy
        if self._obstructed(self.active):
            self.active.x -= dx
            self.active.y -= dy
            return False
        self.active.tspin = "none"
        return True

    def ghost_cells(self):
        """Return the current piece's hard-drop landing cells without moving it."""
        if not self.active:
            return ()
        ghost = FallingPiece(
            self.active.kind,
            self.active.x,
            self.active.y,
            self.active.rotation,
            self.active.tspin,
        )
        while True:
            ghost.y -= 1
            if self._obstructed(ghost):
                ghost.y += 1
                return ghost.cells()

    def _sonic_drop(self):
        while self._shift(0, -1):
            pass

    def _rotate(self, clockwise):
        old_rotation = self.active.rotation
        index = _ROTATIONS.index(old_rotation)
        target = _ROTATIONS[(index + (1 if clockwise else -1)) % 4]
        points = _KICKS.get(self.active.kind, _JLSTZ_KICKS)
        initial_points, target_points = points[old_rotation], points[target]
        original_x, original_y = self.active.x, self.active.y
        self.active.rotation = target
        for kick_index, ((x1, y1), (x2, y2)) in enumerate(zip(initial_points, target_points)):
            self.active.x, self.active.y = original_x + x1 - x2, original_y + y1 - y2
            if not self._obstructed(self.active):
                self._set_tspin_status(kick_index)
                return True
        self.active.rotation = old_rotation
        self.active.x, self.active.y = original_x, original_y
        return False

    def _set_tspin_status(self, kick_index):
        if self.active.kind != "T":
            self.active.tspin = "none"
            return
        mini_corners, non_mini_corners = {
            "N": (((-1, 1), (1, 1)), ((1, -1), (-1, -1))),
            "E": (((1, 1), (1, -1)), ((-1, -1), (-1, 1))),
            "S": (((1, -1), (-1, -1)), ((-1, 1), (1, 1))),
            "W": (((-1, -1), (-1, 1)), ((1, 1), (1, -1))),
        }[self.active.rotation]
        occupied = lambda dx, dy: self._cell_occupied(self.active.x + dx, self.active.y + dy)
        mini_count = sum(occupied(dx, dy) for dx, dy in mini_corners)
        if mini_count + sum(occupied(dx, dy) for dx, dy in non_mini_corners) < 3:
            self.active.tspin = "none"
        else:
            self.active.tspin = "full" if kick_index == 4 or mini_count == 2 else "mini"

    def _cell_occupied(self, x, y):
        return x < 0 or x >= WIDTH or y < 0 or y >= HEIGHT or self.board[y][x] is not None
