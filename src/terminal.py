import os
from string import printable
from sshkeyboard import listen_keyboard_manual

from .types import Message
from .formatting import *

# initialize ANSI escape codes
# without this, they don't work
os.system("")


def char_len(string: str) -> int:
    """
    Returns length of string, excluding the ANSI escape sequences
    """

    # if there are no escape sequences, just return length
    if string.find("\33") == -1:
        return len(string)

    count = 0
    is_escape = False
    for char in string:
        if char == "\33":
            is_escape = True
            continue
        if is_escape and char in "mHKJ":
            is_escape = False
            continue
        if not is_escape:
            count += 1
    return count


class TerminalMessage:
    """
    Message that the terminal prints
    """

    def __init__(self, **kwargs):
        self.content: str | None = kwargs.get("content")
        self.reference_message: Message | None = kwargs.get("reference_message")

    def __str__(self) -> str:
        return character_wrap(self.content, Term.term_width)

    def lines(self) -> list[str]:
        """
        Returns list of lines in message
        """

        return self.__str__().split("\n")


class Term:
    """
    Terminal rendering class
    """

    term_width: int = os.get_terminal_size().columns
    term_height: int = os.get_terminal_size().lines

    message_field: int = term_height - 2

    def __init__(self):
        # terminal stuff
        self.messages: list[TerminalMessage] = []       # terminal rendered messages
        self.print_buffer: str = ""                     # terminal buffer
        self.lines: list[str] = []                      # terminal lines
        self.line_offset: int = 0                       # offset to rendered lines
        self.line_ptr: int = 0                          # current line

        # terminal user input
        self.input_callback = None
        self.user_input: list[str] = [" " for _ in range(self.term_width)]
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
        elif key == "delete":
            self._delete_user_input()
        elif key == "enter":
            await self.input_callback(self.user_input)
            self._clear_user_input()
        elif key == "up":
            self.change_line(-5)
        elif key == "down":
            self.change_line(5)
        elif key == "left":
            self._move_user_cursor(-1)
            self._update_user_input()
        elif key == "right":
            self._move_user_cursor(1)
            self._update_user_input()
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

    def _print(self, value, flush=False):
        """
        Internal print method
        """

        self.print_buffer += value.__str__()
        if flush:
            self._flush_buffer()

    def _flush_buffer(self):
        """
        Flushes the print buffer
        """

        print(self.print_buffer, flush=True, end="")
        self.print_buffer = ""

    def _update_user_input(self):
        """
        Updates user input
        """

        self._print(f"\33[{self.message_field+2};0H", False)
        to_print = TERM_INPUT_FIELD + "".join(self.user_input[:self.user_cursor])
        to_print += TERM_CURSOR + self.user_input[self.user_cursor] + TERM_INPUT_FIELD
        to_print += "".join(self.user_input[self.user_cursor+1:]) + CS_RESET
        self._print("".join(to_print), True)

    def _insert_user_input(self, key: str):
        """
        Inserts a character at user cursor
        """

        self.user_input.insert(self.user_cursor, key)
        self.user_input.pop()
        self._move_user_cursor(1)
        self._update_user_input()

    def _pop_user_input(self):
        """
        Removes a character at user cursor
        """

        self.user_input.pop(self.user_cursor-1)
        self._move_user_cursor(-1)
        self.user_input.append(" ")
        self._update_user_input()

    def _delete_user_input(self):
        """
        `delete` key functionality
        """

        self.user_input.pop(self.user_cursor)
        self.user_input.append(" ")
        self._update_user_input()

    def _clear_user_input(self):
        """
        Clears the user input
        """

        self.user_input = [" " for _ in range(self.term_width)]
        self.user_cursor = 0
        self._update_user_input()

    def _move_user_cursor(self, offset: int):
        """
        Moves user cursor
        """

        self.user_cursor += offset
        self.user_cursor = max(0, min(len(self.user_input), self.user_cursor))

    def set_term_cursor(self, x: int, y: int, flush=False):
        """
        Sets X and Y position for terminal cursor
        """

        self._print(f"\33[{y};{x}H", flush=flush)

    def clear_terminal(self):
        """
        Just clears the terminal
        """

        os.system("cls" if os.name == "nt" else "clear")
        self.set_term_cursor(0, self.message_field+1)
        self._print(f"{TERM_INPUT_FIELD}{'='*self.term_width}\n"
                    f"{TERM_INPUT_FIELD}{' '*self.term_width}{CS_RESET}", True)
        self.line_ptr = 0

    def change_line(self, offset):
        """
        Changes the line offset
        """

        old = self.line_offset
        self.line_offset += offset
        self.line_offset = max(0, min(len(self.lines)-6, self.line_offset))
        if self.line_offset != old:
            self.update_onscreen_lines()

    def update_lines(self):
        """
        Updates content of every line with new messages
        """

        self.lines.clear()
        for msg in self.messages:
            self.lines += msg.lines()

    def update_onscreen_lines(self):
        """
        Updates content of every terminal line (in message field)
        """

        # move cursor home (0, 0)
        self._print("\33[H")

        # calculate start and end
        start = self.line_offset
        end = min(len(self.lines), start + self.message_field)

        # calculate line pointer
        self.line_ptr = end - self.line_offset

        # print lines
        for line in self.lines[start:end]:
            spaces = " " * (self.term_width - char_len(line))
            self._print(f"{line}{spaces}")

        # deal with empty lines
        for _ in range(self.message_field - self.line_ptr):
            self._print(' ' * self.term_width)

        # flush the print buffer
        self._flush_buffer()

    def update_newest(self):
        """
        Updates content for newly added lines (when they are visible)
        """

        # check line pointer (if it exceeds the message field => return)
        if self.line_ptr > self.message_field:
            return

        # move cursor to correct line
        self.set_term_cursor(0, self.line_ptr+1)

        # calculate start and end
        start = self.line_offset + self.line_ptr
        end = min(len(self.lines), start + self.message_field)

        # prevent message field overflows
        if end - self.line_offset > self.message_field:
            end = start + self.message_field - self.line_ptr

        # if there is nothing to print => return
        if end - start == 0:
            return

        # print lines
        for line in self.lines[start:end]:
            spaces = " " * (self.term_width - char_len(line))
            self._print(f"{line}{spaces}")

        # deal with empty lines
        for _ in range(self.message_field - self.line_ptr - 1):
            self._print(' ' * self.term_width)

        # update line pointer
        self.line_ptr += end - start

        # flush the print buffer
        self._flush_buffer()

    def print(self, value):
        """
        High level print method for the terminal
        """

        # append new message
        message = TerminalMessage(content=value.__str__())
        self.messages.append(message)
        self.lines += message.lines()

        # print out newest lines
        self.update_newest()

    def log(self, value):
        """
        High level print method, but adds [CLIENT] at the beginning
        """

        # make value
        value = CLIENT_LOG + " " + value.__str__()
        value = value.replace(CS_RESET, f"{CS_RESET}\33[95m")

        # print it out
        self.print(value)

    def print_message(self, message: Message):
        """
        High level print method for printing discord messages
        """

        # append new message
        message = TerminalMessage(content=message.content, reference_message=message)
        self.messages.append(message)
        self.lines += message.lines()

        # print out newest lines
        self.update_newest()
