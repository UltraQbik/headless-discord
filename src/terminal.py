import os
from string import printable
from sshkeyboard import listen_keyboard_manual

from .types import Message
from .formatting import *


class TerminalMessage:
    """
    Message that the terminal prints
    """

    def __init__(self, **kwargs):
        self.content: str | None = kwargs.get("content")
        self.reference_message: Message | None = kwargs.get("reference_message")

    def __str__(self) -> str:
        return character_wrap(self.content, Terminal.term_width)

    def lines(self) -> list[str]:
        """
        Returns list of lines in message
        """

        return self.__str__().replace("\t", " "*4).split("\n")


class Terminal:
    """
    Terminal rendering class
    """

    # was initialized?
    initialized: bool = False

    # fetch terminals width and height (columns and lines)
    term_width: int = os.get_terminal_size().columns
    term_height: int = os.get_terminal_size().lines

    # size of the messages field
    message_field: int = term_height - 2

    # terminal stuff
    messages: list[TerminalMessage] = []       # terminal rendered messages
    print_buffer: str = ""                     # terminal buffer
    lines: list[str] = []                      # terminal lines
    line_offset: int = 0                       # offset to rendered lines
    line_ptr: int = 0                          # current line

    # terminal user input
    input_callback = None
    user_input: list[str] = [" " for _ in range(term_width)]
    user_cursor: int = 0

    @classmethod
    def initialize_terminal(cls):
        """
        Initializes terminal class
        """

        if not cls.initialized:
            # set to True
            cls.initialized = True

            # initialize ANSI escape codes
            os.system("")

    @classmethod
    async def start_listening(cls):
        """
        Start listening to user input
        """

        await listen_keyboard_manual(
            on_press=cls.key_press_callout, on_release=cls.key_release_callout,
            delay_second_char=0.05, lower=False
        )

    @classmethod
    async def key_press_callout(cls, key: str):
        """
        Callout message when any key is pressed
        """

        if key in printable:
            cls._insert_user_input(key)
        elif key == "space":
            cls._insert_user_input(" ")
        elif key == "backspace":
            cls._pop_user_input()
        elif key == "delete":
            cls._delete_user_input()
        elif key == "enter":
            await cls.input_callback(cls.user_input)
            cls._clear_user_input()
        elif key == "up":
            cls.change_line(-5)
        elif key == "down":
            cls.change_line(5)
        elif key == "left":
            cls._move_user_cursor(-1)
            cls._update_user_input()
        elif key == "right":
            cls._move_user_cursor(1)
            cls._update_user_input()
        elif key == "pageup":
            cls.change_line(-cls.message_field)
        elif key == "pagedown":
            cls.change_line(cls.message_field)
        else:
            cls._insert_user_input(key)

    @classmethod
    async def key_release_callout(cls, key: str):
        """
        Callout message when any key is released
        """

        pass

    @classmethod
    def _print(cls, value, flush=False):
        """
        Internal print method
        """

        cls.print_buffer += value.__str__()
        if flush:
            cls._flush_buffer()

    @classmethod
    def _flush_buffer(cls):
        """
        Flushes the print buffer
        """

        print(cls.print_buffer, flush=True, end="")
        cls.print_buffer = ""

    @classmethod
    def _update_user_input(cls):
        """
        Updates user input
        """

        cls._print(f"\33[{cls.message_field + 2};0H", False)
        to_print = TERM_INPUT_FIELD + "".join(cls.user_input[:cls.user_cursor])
        to_print += TERM_CURSOR + cls.user_input[cls.user_cursor] + TERM_INPUT_FIELD
        to_print += "".join(cls.user_input[cls.user_cursor + 1:]) + CS_RESET
        cls._print("".join(to_print), True)

    @classmethod
    def _insert_user_input(cls, key: str):
        """
        Inserts a character at user cursor
        """

        cls.user_input.insert(cls.user_cursor, key)
        cls.user_input.pop()
        cls._move_user_cursor(1)
        cls._update_user_input()

    @classmethod
    def _pop_user_input(cls):
        """
        Removes a character at user cursor
        """

        cls.user_input.pop(cls.user_cursor - 1)
        cls._move_user_cursor(-1)
        cls.user_input.append(" ")
        cls._update_user_input()

    @classmethod
    def _delete_user_input(cls):
        """
        `delete` key functionality
        """

        cls.user_input.pop(cls.user_cursor)
        cls.user_input.append(" ")
        cls._update_user_input()

    @classmethod
    def _clear_user_input(cls):
        """
        Clears the user input
        """

        cls.user_input = [" " for _ in range(cls.term_width)]
        cls.user_cursor = 0
        cls._update_user_input()

    @classmethod
    def _move_user_cursor(cls, offset: int):
        """
        Moves user cursor
        """

        cls.user_cursor += offset
        cls.user_cursor = max(0, min(len(cls.user_input), cls.user_cursor))

    @classmethod
    def set_term_cursor(cls, x: int, y: int, flush=False):
        """
        Sets X and Y position for terminal cursor
        """

        cls._print(f"\33[{y};{x}H", flush=flush)

    @classmethod
    def clear_terminal(cls):
        """
        Just clears the terminal
        """

        os.system("cls" if os.name == "nt" else "clear")
        cls.set_term_cursor(0, cls.message_field + 1)
        cls._print(f"{TERM_INPUT_FIELD}{'=' * cls.term_width}\n"
                    f"{TERM_INPUT_FIELD}{' ' * cls.term_width}{CS_RESET}", True)
        cls.line_ptr = 0

    @classmethod
    def change_line(cls, offset):
        """
        Changes the line offset
        """

        old = cls.line_offset
        cls.line_offset += offset
        cls.line_offset = max(0, min(len(cls.lines) - 6, cls.line_offset))
        if cls.line_offset != old:
            cls.update_onscreen_lines()

    @classmethod
    def update_lines(cls):
        """
        Updates content of every line with new messages
        """

        cls.lines.clear()
        for msg in cls.messages:
            cls.lines += msg.lines()

    @classmethod
    def update_onscreen_lines(cls):
        """
        Updates content of every terminal line (in message field)
        """

        # move cursor home (0, 0)
        cls._print("\33[H")

        # calculate start and end
        start = cls.line_offset
        end = min(len(cls.lines), start + cls.message_field)

        # calculate line pointer
        cls.line_ptr = end - cls.line_offset

        # print lines
        for line in cls.lines[start:end]:
            cls._print(f"{line}\33[0K\n")

        # deal with empty lines
        cls._print("\33[0K\n" * (cls.message_field - cls.line_ptr))

        # flush the print buffer
        cls._flush_buffer()

    @classmethod
    def update_newest(cls):
        """
        Updates content for newly added lines (when they are visible)
        """

        # check line pointer (if it exceeds the message field => return)
        if cls.line_ptr > cls.message_field:
            return

        # move cursor to correct line
        cls.set_term_cursor(0, cls.line_ptr + 1)

        # calculate start and end
        start = cls.line_offset + cls.line_ptr
        end = min(len(cls.lines), start + cls.message_field)

        # prevent message field overflows
        if end - cls.line_offset > cls.message_field:
            end = start + cls.message_field - cls.line_ptr

        # if there is nothing to print => return
        if end - start == 0:
            return

        # print lines
        for line in cls.lines[start:end]:
            cls._print(f"{line}\33[0K\n")

        # deal with empty lines
        cls._print("\33[0K\n" * (cls.message_field - cls.line_ptr - 1))

        # update line pointer
        cls.line_ptr += end - start

        # flush the print buffer
        cls._flush_buffer()

    @classmethod
    def print(cls, value):
        """
        High level print method for the terminal
        """

        # append new message
        message = TerminalMessage(content=value.__str__())
        cls.messages.append(message)
        cls.lines += message.lines()

        # print out newest lines
        cls.update_newest()

    @classmethod
    def log(cls, value):
        """
        High level print method, but adds [CLIENT] at the beginning
        """

        # make string (slightly) more consistent
        string = value.__str__().replace(CS_RESET, f"{CS_RESET}{CLIENT_COL[2]}")
        string = f"{CLIENT_COL[0]}[CLIENT]{CLIENT_COL[2]} {string}{CS_RESET}"

        # print it out
        cls.print(string)

    @classmethod
    def print_message(cls, message: Message):
        """
        High level print method for printing discord messages
        """

        # append new message
        message = TerminalMessage(content=message.content, reference_message=message)
        cls.messages.append(message)
        cls.lines += message.lines()

        # print out newest lines
        cls.update_newest()
