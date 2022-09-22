from display_modes.tetris_runner import MisaMinoRunner
from PIL import Image
from display_modes import module
from time import sleep, time
import colorlog

logger = colorlog.getLogger(__name__)


jstris_mino_colors = {'I': (25, 165, 225), 'J': (33, 65, 225), 'L': (277, 91, 2), 'S': (55, 200, 1), 'Z':
                      (225, 15, 10), 'O': (277, 159, 2), 'X': (153, 153, 153), 'T': (175, 41, 138), '-': (0, 0, 0)}

piece_coords = {'I': [(0, 0), (1, 0), (2, 0), (3, 0)],
                'L': [(0, 1), (1, 1), (2, 1), (2, 0)],
                'J': [(0, 0), (0, 1), (1, 1), (2, 1)],
                'T': [(0, 1), (1, 1), (2, 1), (1, 0)],
                'S': [(0, 1), (1, 1), (1, 0), (2, 0)],
                'Z': [(0, 0), (1, 0), (1, 1), (2, 1)],
                'O': [(1, 0), (1, 1), (2, 0), (2, 1)]}


class TetrisPlayer(module.Module):
    def __init__(self, driver):
        super().__init__(driver)
        self.driver = driver
        self.image = Image.new('RGB', (self.width, self.height), 'black')
        self.pixels = self.image.load()
        self.tetris_runner = MisaMinoRunner()
        self.color_map: dict = jstris_mino_colors
        self.delay: float = 0.2
        self.draw_border()

    def step_game(self):
        self.tetris_runner.step_bot()

    def draw_border(self):
        for row in range(16):
            self.pixels[10, row] = (100, 100, 100)

    def draw_board(self):
        for row in range(16):
            for col in range(10):
                mino_on_board = self.tetris_runner.tetris_game.internal_board[row + 4][col]
                self.pixels[col, row] = self.color_map[mino_on_board]

        self.draw_next_piece()
        self.draw_piece_queue()

    def draw_piece_queue(self):
        """ Draws next pieces on the sidebar """
        x_offset = 12
        y_offset = 1
        # First clear the old pixels
        for x in range(x_offset, self.driver.width):
            for y in range(y_offset, self.driver.height):
                self.pixels[x, y] = (0, 0, 0)

        num_pieces = 5
        next_pieces = self.tetris_runner.tetris_game.get_next_pieces(num_pieces)


        for piece in next_pieces:
            color = self.color_map[piece]
            for x, y in piece_coords[piece]:
                self.pixels[x + x_offset, y + y_offset] = color

            y_offset += 3

    def draw_next_piece(self):
        """ Draws next piece at the top """
        x_offset = 3
        y_offset = 0
        next_piece = self.tetris_runner.tetris_game.this_piece

        color = self.color_map[next_piece]
        for x, y in piece_coords[next_piece]:
            self.pixels[x + x_offset, y + y_offset] = color

    def run(self):
        while True:
            start = time()

            self.draw_board()
            self.display()
            self.step_game()
            sleep(self.delay)

            stop = time()
            fps = 1.0/(stop - start)
            logger.info(f"PPS: {fps:.2f}")


if __name__ == "main":
    tp = TetrisPlayer()
    tp.run()
