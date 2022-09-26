from typing import List
from collections import deque
from time import sleep
import random
import subprocess
import colorlog
from copy import deepcopy

logger = colorlog.getLogger(__name__)


class TetrisGame():
    def __init__(self) -> None:
        self.internal_board: deque(List[str]) = self._generate_blank_board()
        self.bot_board = self._generate_bot_board()
        self.piece_queue: deque = deque(self._generate_seven_pieces())
        # self.last_pieces: deque = deque(self.piece_queue[0])
        # self.last_piece: str = None
        self.this_piece = self.piece_queue[0]

    def get_next_piece(self) -> str:
        """ Gets next piece, repopulates queue if it drops below size 7 """
        piece = self.piece_queue.popleft()
        if len(self.piece_queue) < 7:
            self.piece_queue.extend(self._generate_seven_pieces())

        # self.last_pieces.appendleft(piece)
        # self.last_piece = self.last_pieces.pop()
        self.this_piece = piece
        return piece

    def set_bot_board(self, board: str) -> None:
        self.bot_board = board

    def get_next_pieces(self, num_pieces: int) -> List[str]:
        return list(self.piece_queue)[0:num_pieces]

    def get_bot_board(self) -> str:
        return self.bot_board

    def add_garbage(self, num_lines: int) -> None:
        """ Adds num_lines of garbage to the board """
        # Algorithm to generate garbage 

        # Add lines to bottom of board

        # Update bot board representation

    def update_bot_board(self, board: str, lines_cleared: int) -> None:
        """ Gets the board state from the bot and updates both board representations """

        # To find out where the piece went, we compare to the previous iteration of the board state
        # Convert the new bot board layout to 2d array
        next_state_bot = self._convert_to_2d_arr(board)

        # If any lines are cleared, we need to shift everything down
        if lines_cleared > 0:
            self._clear_lines(lines_cleared)
            logger.info(f"Tetris: cleared {lines_cleared} lines")

        # Compare elements of previous state to this next_state, and whatever is changed is now filled with previous state
        # next_internal_state = self._generate_blank_board()
        for rowIndex, row in enumerate(self.internal_board):
            for colIndex, col in enumerate(row):
                # If bot state reports a piece in this index
                if next_state_bot[rowIndex][colIndex] != '0':
                    # If this is a new piece, ie current internal state does not have this occupied
                    if self.internal_board[rowIndex][colIndex] == '-':
                        # Then this is the newly placed piece, we mark it as such
                        self.internal_board[rowIndex][colIndex] = self.this_piece

        # After everything is processed, set bot_board to the correct representation
        self.bot_board = self._convert_to_bot_board(self.internal_board)
        # print("bot board: " + self.bot_board)
        # self.print_bot_board()
        # self.print_internal_board()
        # self.print_bot_board()

    def _clear_lines(self, num_lines: int):
        """ Searches for any full lines and clears them """
        new_line = ['-'] * 10
        # self.print_bot_board()
        # for row in list(self.internal_board):
        #     print(row)
        #     if '-' not in row:
        #         self.internal_board.remove(row)
        #         logger.warn(f"Removed {row}, examine board state below")
        #         self.print_bot_board()
        #         self.internal_board.appendleft(deepcopy(new_line))
        #         num_lines -= 1
        #         logger.warn("Removed floating line")

        for _ in range(num_lines):
            self.internal_board.pop()
            self.internal_board.appendleft(deepcopy(new_line))

    def _convert_to_2d_arr(self, bot_board: str) -> List[List[str]]:
        """ Takes the str bot_board representation and converts it to a 2d array """
        rows = bot_board.split(';')
        result = []
        for row in rows:
            result.append(row.split(','))

        return result

    def _convert_to_bot_board(self, internal_board: List[List[str]]) -> str:
        internal_board_copy = deepcopy(internal_board)
        for row in range(len(internal_board_copy)):
            for col in range(len(internal_board_copy[row])):
                # print(f"internal_board_copy[{row}][{col}] = {internal_board_copy[row][col]} and that == '-' is {internal_board_copy[row][col] == '-'}")
                internal_board_copy[row][col] = '2' if internal_board_copy[row][col] != '-' else '0'
        rows = []
        for row in internal_board_copy:
            rows.append(','.join(row))

        bot_board = ';'.join(rows)
        return bot_board

    def _generate_seven_pieces(self) -> List[str]:
        """ Returns 7 shuffled pieces """
        pieces = ['I', 'J', 'L', 'O', 'T', 'S', 'Z']
        random.shuffle(pieces)
        return pieces

    def _generate_blank_board(self) -> List[List[str]]:
        BLANK = '-'
        row = [BLANK]*10
        result = deque()
        for _ in range(20):
            result.append(row[:])
        return result

    def _generate_bot_board(self) -> str:
        """ Generates empty bot board for MisaMino """
        board = ("0,0,0,0,0,0,0,0,0,0;"
                 "0,0,0,0,0,0,0,0,0,0;"
                 "0,0,0,0,0,0,0,0,0,0;"
                 "0,0,0,0,0,0,0,0,0,0;"
                 "0,0,0,0,0,0,0,0,0,0;"
                 "0,0,0,0,0,0,0,0,0,0;"
                 "0,0,0,0,0,0,0,0,0,0;"
                 "0,0,0,0,0,0,0,0,0,0;"
                 "0,0,0,0,0,0,0,0,0,0;"
                 "0,0,0,0,0,0,0,0,0,0;"
                 "0,0,0,0,0,0,0,0,0,0;"
                 "0,0,0,0,0,0,0,0,0,0;"
                 "0,0,0,0,0,0,0,0,0,0;"
                 "0,0,0,0,0,0,0,0,0,0;"
                 "0,0,0,0,0,0,0,0,0,0;"
                 "0,0,0,0,0,0,0,0,0,0;"
                 "0,0,0,0,0,0,0,0,0,0;"
                 "0,0,0,0,0,0,0,0,0,0;"
                 "0,0,0,0,0,0,0,0,0,0;"
                 "0,0,0,0,0,0,0,0,0,0")

        return board

    def print_bot_board(self) -> None:
        display = self.bot_board.replace(',', '')
        display = display.replace(';', '\n')
        print(display)

    def print_internal_board(self) -> None:
        for row in self.internal_board:
            print(' '.join(row))


class MisaMinoRunner():
    def __init__(self) -> None:
        self.tetris_game = TetrisGame()
        self.bot_proc = subprocess.Popen(['./tetris_ai'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self._init_bot()

    def _init_bot(self) -> None:
        command = "update game round 1"
        self._write(command)
        logger.info(f"bot_command: {command}")

        command = "settings style 4"
        self._write(command)
        self._read()
        logger.info(f"bot_command: {command}")

        command = "settings level 1"
        self._write(command)
        self._read()
        logger.info(f"bot_command: {command}")

        self._set_pieces()
        self._set_field()
        pass

    def _set_pieces(self) -> None:
        this_piece = self.tetris_game.get_next_piece()
        next_pieces = ','.join(self.tetris_game.get_next_pieces(5))
        this_piece_command = f"update game this_piece_type {this_piece}"
        next_pieces_command = f"update game next_pieces {next_pieces}"

        self._write(this_piece_command)
        self._write(next_pieces_command)
        logger.info(f"bot_command: {this_piece_command}")
        logger.info(f"bot_command: {next_pieces_command}")

    def _set_field(self) -> None:
        command = f"update bot1 field {self.tetris_game.bot_board}"
        self._write(command)
        logger.info(f"bot_command: {command[0:38]}...{command[-20:]}")

    def step_bot(self) -> None:
        # Send command to bot
        command = "action2 moves 1"
        self._write(command)
        logger.info(f"bot_command: {command}")

        # Get response
        try:
            response = self._read()
        except IndexError:
            raise Exception("Bot could not move")
        
        # Parse response
        lines_cleared = int(response[0])
        spins_used = True if response[2] == '1' else False
        new_board_state = response[4:]
        logger.info(f"bot_response: lines- {lines_cleared} spins- {spins_used}")

        # if no moves were found, throw exception
        if lines_cleared == -1:
            raise Exception("MisaMino could not find move")

        # Update game board
        self.tetris_game.update_bot_board(new_board_state, lines_cleared)

        # Set new state
        self._set_pieces()
        self._set_field()

    def _read(self) -> str:
        return self.bot_proc.stdout.readline().decode("utf-8").strip()

    def _write(self, message: str):
        self.bot_proc.stdin.write(f"{message.strip()}\n".encode("utf-8"))
        self.bot_proc.stdin.flush()

    def kill_bot(self) -> None:
        self.bot_proc.stdin.close()
        self.bot_proc.terminate()
        self.bot_proc.wait(timeout=0.2)


if __name__ == "__main__":
    # tetris_game = TetrisGame()
    # print(tetris_game.piece_queue)
    # for _ in range(14):
    #     print(tetris_game.get_next_piece())
    #     # print(tetris_game.piece_queue)
    #     print(tetris_game.get_next_pieces(5))
    #     print(tetris_game.last_piece)
    #     print("\n")
    # tetris_game.print_internal_board()

    bot_runner = MisaMinoRunner()
    for _ in range(50):
        bot_runner.step_bot()
    bot_runner._kill_bot()
