import re
from .constants import *


def character_wrap(string: str, width=TERM_WIDTH) -> str:
    """
    Character wraps a string. ignores escape sequences
    """

    is_esc = False
    line_len = 0
    new_string = ""
    for idx, char in enumerate(string):
        new_string += char
        line_len += 1 if not is_esc else 0

        # newline
        if char == "\n":
            line_len = 0

        # escape character
        elif char == "\33":
            is_esc = True

        # when we found end of escape sequence
        elif char in "mHKJ" and is_esc:
            is_esc = False
            line_len -= 1

        elif line_len >= width and idx < len(string) and string[idx+1] != "\n":
            new_string += "\n"
            line_len = 0
    return new_string


def apply_style(content: str, brackets: str, style: str):
    """
    Applies style to the content string
    """

    brs = "\\" + "\\".join(list(brackets))
    regex = brs + r"(.*?)" + brs
    for string in re.findall(regex, content):
        content = content.replace(f"{brackets}{string}{brackets}", f"{style}{string}{CS_RESET}")
    return content


def format_message(message) -> str:
    """
    Returns terminal formatted message
    """

    timestamp = message.timestamp.strftime("%H:%M:%S")
    nickname = message.author.nickname

    content = message.content

    # apply styles
    content = apply_style(content, "**", STYLE_BOLD)
    content = apply_style(content, "*", STYLE_ITALICS)
    content = apply_style(content, "__", STYLE_UNDERLINE)
    content = apply_style(content, "~~", STYLE_STRIKETHROUGH)
    content = apply_style(content, "`", CODE_BLOCK)

    return character_wrap(f"{STYLE_DARKEN}[{timestamp}]{CS_RESET} {nickname}{STYLE_DARKEN}>{CS_RESET} {content}")
