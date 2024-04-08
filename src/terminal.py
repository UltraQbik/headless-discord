import os
from typing import Callable
from string import printable
from sshkeyboard import listen_keyboard_manual

from .constants import *
from .types import Message
from .formatting import *


# initialize ANSI escape codes
# without this, they don't work
os.system("")


class Term:
    """
    Terminal rendering class
    """

    message_field: int = TERM_HEIGHT - 2
    input_field: str = '[-]: '

    def __init__(self):
        # terminal stuff
        self.messages: list[Message] = []
        self.message_ptr: int = 0

        # terminal buffering
        self.str_lines: list[str] = []
        self.line_offset: int = 0
        self.current_line: int = 0

        # terminal user input
        self.input_callback = None
        self.user_input: list[str] = [" " for _ in range(TERM_WIDTH - len(self.input_field))]
        self.user_cursor: int = 0

    async def start_listening(self):
        """
        Start listening to user input
        """

        await listen_keyboard_manual(
            on_press=self.key_press_callout, on_release=self.key_release_callout,
            delay_second_char=0.05, lower=False
        )

    async def key_press_callout(self, key: str):
        """
        Callout message when any key is pressed
        """

        if key in printable:
            self._insert_user_input(key)
        elif key == "space":
            self._insert_user_input(" ")
        elif key == "backspace":
            self._pop_user_input()
        elif key == "enter":
            await self.input_callback(self.user_input)
            self._clear_user_input()
        elif key == "up":
            self.change_line(-5)
            self.update_all()
        elif key == "down":
            self.change_line(5)
            self.update_all()
        elif key == "left":
            self._change_user_cursor(-1)
        elif key == "right":
            self._change_user_cursor(1)
        elif key == "pageup":
            self.change_line(-self.message_field)
            self.update_all()
        elif key == "pagedown":
            self.change_line(self.message_field)
            self.update_all()
        else:
            self._insert_user_input(key)

    async def key_release_callout(self, key: str):
        """
        Callout message when any key is released
        """

        pass

    def change_line(self, offset: int):
        """
        Offsets the line pointer
        """

        if offset < 0:
            self.line_offset = max(0, self.line_offset + offset)
        else:
            self.line_offset = min(len(self.str_lines) - 8, self.line_offset + offset)

    @staticmethod
    def set_cursor(x: int, y: int, flush=True):
        """
        Sets the cursor position to the given out
        """

        print(f"\33[{y};{x}H", end="", flush=flush)

    def _clear_user_input(self):
        """
        Clears user input buffer
        """

        self.user_input = [" " for _ in range(TERM_WIDTH - len(self.input_field))]
        self.user_cursor = 0
        self._update_input()

    def _change_user_cursor(self, offset: int):
        """
        Offsets the user input cursor
        """

        if offset < 0:
            self.user_cursor = max(0, self.user_cursor + offset)
        else:
            self.user_cursor = min(len(self.user_input)-1, self.user_cursor + offset)
        self._update_input()

    def _insert_user_input(self, key: str):
        """
        Inserts text into user input string
        """

        self.user_input[self.user_cursor] = key
        self._change_user_cursor(1)
        self._update_input()

    def _pop_user_input(self):
        """
        Basically backspace implementation
        """

        self._change_user_cursor(-1)
        self.user_input[self.user_cursor] = " "
        self._update_input()

    def _update_input(self):
        """
        Updates user input string
        """

        self.set_cursor(len(self.input_field)+1, self.message_field+2, False)
        user_input = "".join(self.user_input[:self.user_cursor])
        user_input += TERM_CURSOR + self.user_input[self.user_cursor] + TERM_INPUT_FIELD
        user_input += "".join(self.user_input[self.user_cursor+1:])
        print(f"\33[0K{TERM_INPUT_FIELD}{user_input}{CS_RESET}", end="", flush=True)

    def clear_terminal(self, flush=True):
        """
        Clears the terminal
        """

        self.current_line = 0
        os.system("cls" if os.name == "nt" else "clear")
        print(
            f"\33[{self.message_field+1};0H"
            f"{TERM_INPUT_FIELD}{'='*TERM_WIDTH}{CS_RESET}\n"
            f"{TERM_INPUT_FIELD}{self.input_field}{' '*(TERM_WIDTH-len(self.input_field))}{CS_RESET}",
            end="", flush=flush)

    def _write_all(self):
        """
        Prints out all messages from message stack
        """

        self.str_lines.clear()
        for message in self.messages:
            self.str_lines += format_message(message).split("\n")
        self.message_ptr = len(self.messages)

    def _write_new(self):
        """
        Writes new messages to the buffer
        """

        for message in self.messages[self.message_ptr:]:
            self.str_lines += format_message(message).split("\n")
        self.message_ptr = len(self.messages)

    def partial_update(self):
        """
        Partially updates the messages (prints missing ones)
        """

        self._write_new()

        start = self.line_offset + self.current_line
        end = min(len(self.str_lines), start + self.message_field)

        # set cursor position to the next line
        self.set_cursor(0, self.current_line + 1)

        # if the amount of lines added overflows the message field
        if end - self.line_offset > self.message_field:
            # clamp it to limits of message field
            end = start + self.message_field - self.current_line

        # offset the current line by the amount of added newline
        self.current_line += end - start

        to_print = "\n".join(self.str_lines[start:end])
        print(to_print, end="", flush=True)

    def print(self, *values, sep=" "):
        """
        Prints out a string to the terminal
        :param values: values that will be printed
        :param sep: separators used between values
        """

        lines = character_wrap(sep.join(map(str, values))).split("\n")
        self.str_lines += lines

        self.partial_update()

    def log(self, *values, sep=""):
        """
        Prints out strings to the terminal, client logging
        :param values: values that will be printed
        :param sep: separator that will be put between values
        """

        lines = character_wrap(
            sep.join(map(lambda x: f"{CLIENT_LOG} {x}{CS_RESET}", values))
        ).split("\n")
        self.str_lines += lines

        self.partial_update()

    def update_all(self):
        """
        Updates everything on the terminal
        """

        self.clear_terminal(False)

        start = self.line_offset
        end = min(len(self.str_lines), self.line_offset + self.message_field)
        print("\33[H" + "\n".join(self.str_lines[start:end]), end="", flush=False)
        self.current_line = end - start

        self._update_input()
