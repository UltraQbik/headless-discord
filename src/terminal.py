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


class TerminalMessage:
    """
    Message that the terminal prints
    """

    def __init__(self, **kwargs):
        self.content: str | None = kwargs.get("content")

    def __str__(self) -> str:
        return character_wrap(self.content)

    def lines(self) -> list[str]:
        """
        Returns list of lines in message
        """

        return self.__str__().split("\n")


class Term:
    """
    Terminal rendering class
    """

    message_field: int = TERM_HEIGHT - 2
    input_field: str = '[-]: '

    def __init__(self):
        # terminal stuff
        self.messages: list[TerminalMessage] = []       # terminal rendered messages
        self.print_buffer: str = ""                     # terminal buffer
        self.lines: list[str] = []                      # terminal lines
        self.line_offset: int = 0                       # offset to rendered lines
        self.line_ptr: int = 0                          # current line

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
        elif key == "down":
            self.change_line(5)
        elif key == "left":
            self._change_user_cursor(-1)
        elif key == "right":
            self._change_user_cursor(1)
        elif key == "pageup":
            self.change_line(-self.message_field)
        elif key == "pagedown":
            self.change_line(self.message_field)
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

        old = self.line_offset
        if offset < 0:
            self.line_offset = max(0, self.line_offset + offset)
        else:
            self.line_offset = min(len(self.lines) - 8, self.line_offset + offset)
        if old != self.line_offset:
            self.clear_message_field(flush=False)
            self.update_onscreen()

    def _print(self, value):
        """
        Internal print method, adds value to buffer
        """

        self.print_buffer += value.__str__()

    def refresh(self):
        """
        Prints out terminal print buffer
        """

        print(self.print_buffer, end="", flush=True)

    def set_cursor(self, x: int, y: int):
        """
        Sets the cursor position to the given out
        """

        self._print(f"\33[{y};{x}H")

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
            self.user_cursor = min(len(self.user_input) - 1, self.user_cursor + offset)
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

        print(f"\33[{self.message_field + 2};{len(self.input_field) + 1}H", end="", flush=False)
        user_input = "".join(self.user_input[:self.user_cursor])
        user_input += TERM_CURSOR + self.user_input[self.user_cursor] + TERM_INPUT_FIELD
        user_input += "".join(self.user_input[self.user_cursor + 1:])
        print(f"\33[0K{TERM_INPUT_FIELD}{user_input}{CS_RESET}", end="", flush=True)

    def clear_terminal(self, flush=True):
        """
        Clears the terminal
        """

        os.system("cls" if os.name == "nt" else "clear")
        self._print(
            f"\33[{self.message_field + 1};0H"
            f"{TERM_INPUT_FIELD}{'=' * TERM_WIDTH}{CS_RESET}\n"
            f"{TERM_INPUT_FIELD}{self.input_field}{' ' * (TERM_WIDTH - len(self.input_field))}{CS_RESET}")
        if flush:
            self.refresh()

    def clear_message_field(self, flush=True):
        """
        Clears just the message field, without reprinting the entire frame. Flushes the buffer
        """

        self._print("\33[H" + ("\33[0K\n"*self.message_field))
        self.line_ptr = 0
        if flush:
            self.refresh()

    def update_all(self):
        """
        Updates all terminal lines with messages. Flushes the buffer
        """

        self.clear_terminal(flush=False)
        self.line_ptr = 0
        self.lines.clear()
        for message in self.messages:
            self.lines += message.lines()
        self.update_onscreen()

    def update_onscreen(self):
        """
        Updates lines that are currently on screen. Flushes the buffer
        """

        start = self.line_ptr + self.line_offset
        end = min(start + self.message_field, len(self.lines))

        # prevent message field overflows
        if end - self.line_offset > self.message_field:
            end = start + self.message_field - self.line_ptr

        self.set_cursor(0, self.line_ptr+1)

        # offset the line pointer
        self.line_ptr += end - start

        # go to line pointer points to, and print the message
        self._print("\n".join(self.lines[start:end]))
        self.refresh()

    def print(self, value):
        """
        Prints out a value to the screen. Flushes the buffer
        """

        # append new message to the terminal
        self.messages.append(TerminalMessage(content=value.__str__()))
        self.lines += self.messages[-1].lines()

        # update onscreen messages
        self.update_onscreen()

    def log(self, value):
        """
        Prints message as a client
        """

        # append new message to the terminal
        self.messages.append(TerminalMessage(content=f"{CLIENT_LOG} {value}{CS_RESET}"))
        self.lines += self.messages[-1].lines()

        # update onscreen messages
        self.update_onscreen()
