import os
import re
import json
import asyncio
import requests
import argparse
import websockets
from typing import Any, Callable
from random import random
from datetime import datetime
from string import printable
from sshkeyboard import listen_keyboard_manual


# terminal
TERM_WIDTH = 120
TERM_HEIGHT = 30
TERM_CURSOR = "\33[42m"
TERM_INPUT_FIELD = "\33[48;5;236m"

# API links
GATEWAY = r"wss://gateway.discord.gg/?v=9&encoding=json"
API = r"https://discord.com/api/v9"

# pings
PING_HIGHLIGHT = "\33[36m"
PING_ME_HIGHLIGHT = "\33[96m"
STYLE_DARKEN = "\33[90m"
CODE_BLOCK = "\33[48;5;234m"

# styles
CS_RESET = "\33[0m"
STYLE_BOLD = "\33[1m"
STYLE_ITALICS = "\33[3m"
STYLE_UNDERLINE = "\33[4m"
STYLE_STRIKETHROUGH = "\33[9m"

# client
CLIENT_LOG = "\33[35m[CLIENT]\33[95m"
CLIENT_HELP = [
    "//help - prints out this message",
    "//list_g - prints out list of all guilds",
    f"//list_c {STYLE_ITALICS}guild{CS_RESET} - prints out channels in a guild",
    f"//pick_c {STYLE_ITALICS}guild{CS_RESET} {STYLE_ITALICS}channel{CS_RESET} - selects a channel to view",
]

# initialize ANSI escape codes
# without this, they don't work
os.system("")

# parser
parser = argparse.ArgumentParser(
    prog="HeadlessDiscord",
    description="Terminal version of discord")
parser.add_argument("--auth",
                    help="authentication token (your discord token)",
                    default=os.getenv("DISCORD_AUTH"), required=False)
args = parser.parse_args()


def character_wrap(string: str, width=TERM_WIDTH) -> str:
    """
    Character wraps a string
    """

    line_len = 0
    new_string = ""
    for char in string:
        new_string += char
        line_len += 1
        if char == "\n":
            line_len = 0
        if line_len >= width:
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
    newline_offset = len(timestamp) + len(nickname) + 3

    content = message.content

    # apply styles
    content = apply_style(content, "**", STYLE_BOLD)
    content = apply_style(content, "*", STYLE_ITALICS)
    content = apply_style(content, "__", STYLE_UNDERLINE)
    content = apply_style(content, "~~", STYLE_STRIKETHROUGH)
    content = apply_style(content, "`", CODE_BLOCK)

    # character wrap content
    content = character_wrap(content, TERM_WIDTH - newline_offset - 2)
    content = content.replace("\n", f"\n{STYLE_DARKEN}{'-' * newline_offset}>{CS_RESET} ")

    return f"{STYLE_DARKEN}[{timestamp}]{CS_RESET} {nickname}{STYLE_DARKEN}>{CS_RESET} {content}"


class Member:
    """
    Guild member class
    """

    def __init__(self, **kwargs):
        self.guild_id: str | None = kwargs.get("guild_id")
        self.nick: str | None = kwargs.get("nick")
        self.mute: bool | None = kwargs.get("mute")
        self.deaf: bool | None = kwargs.get("deaf")
        self.joined_at: datetime = datetime.fromisoformat(kwargs.get("joined_at")) if "joined_at" in kwargs else None
        self.roles: list[str] | None = kwargs.get("roles")


class User:
    """
    Broad user class
    """

    def __init__(self, **kwargs):
        # general data
        self.id: str | None = kwargs.get("id")
        self.username: str | None = kwargs.get("username")
        self.global_name: str | None = kwargs.get("global_name")

        # guild data
        self.member: Member | None = Member(**(kwargs["member"])) if "member" in kwargs else None

        # fix annoying nickname thing
        if self.member and self.member.nick is None:
            self.member.nick = self.username

    @property
    def nickname(self) -> str:
        """
        Returns user's guild name, if present, otherwise global_name, otherwise username
        """

        if self.member is not None:
            return self.member.nick
        elif self.global_name is not None:
            return self.global_name
        return self.username

    @staticmethod
    def from_response(response: dict):
        """
        Generates user instance from discord response
        :return: User
        """

        user = User(
            **(response["author"]),
            member=response.get("member", {}))
        if "guild_id" in response:
            user.member.guild_id = response["guild_id"]

        return user

    @staticmethod
    def from_response_mention(mention: dict):
        """
        Generates user instance from discord mention response
        :return: User
        """

        return User(**mention)


class Message:
    """
    Message class
    """

    def __init__(self, **kwargs):
        # general data
        self.id: str | None = kwargs.get("id")
        self.channel_id: str | None = kwargs.get("channel_id")
        self.timestamp: datetime | None = datetime.fromisoformat(
            kwargs.get("timestamp")) if "timestamp" in kwargs else None
        self.author: User | None = User.from_response(kwargs)
        self.mentions: list[User] = [User.from_response_mention(x) for x in kwargs["mentions"]]
        self.mention_everyone: bool = kwargs.get("mention_everyone", False)
        self.content: str = kwargs.get("content")

        # guild data
        self.guild_id: str | None = kwargs.get("guild_id")

        # clean content up
        content_mentions = re.findall(r"<(.*?)>", self.content)
        for content_mention in content_mentions:
            if content_mention[:2] != "@&":
                for mention in self.mentions:
                    if content_mention[1:] == mention.id:
                        username = mention.member.nick if mention.member else mention.username

                        # if user mentioned is the client
                        if mention.id == Client.user.id:
                            username = f"{PING_ME_HIGHLIGHT}@{username}{CS_RESET}"
                        else:
                            username = f"{PING_HIGHLIGHT}@{username}{CS_RESET}"

                        self.content = self.content.replace(f"<{content_mention}>", username)
                        break

        # when @everyone is pinged
        if self.mention_everyone:
            self.content = self.content.replace("@everyone", f"{PING_ME_HIGHLIGHT}@everyone{CS_RESET}")

        # when @everyone is pinged, but not really (aka user doesn't have permission to)
        else:
            self.content = self.content.replace("@everyone", f"{PING_HIGHLIGHT}@everyone{CS_RESET}")

        # when @here is pinged
        self.content = self.content.replace("@here", f"{PING_ME_HIGHLIGHT}@here{CS_RESET}")

    @staticmethod
    def from_response(response: dict):
        """
        Generates message instance from discord response
        :return: Message
        """

        return Message(**response)

    def __str__(self):
        timestamp = self.timestamp.strftime('%H:%M:%S')
        username = self.author.member.nick if self.guild_id else self.author.username
        return f"\33[90m[{timestamp}]\33[0m {username}> {self.content}"


class Channel:
    """
    Channel class
    """

    def __init__(self, **kwargs):
        self.id: str = kwargs.get("id")
        self.name: str = kwargs.get("name")
        self.nsfw: bool = kwargs.get("nsfw")
        self.position: int = kwargs.get("position")
        self.type: int = kwargs.get("type")


class Guild:
    """
    Guild class
    """

    def __init__(self, **kwargs):
        self.id: str = kwargs.get("id")
        self.name: str = kwargs.get("name")
        self.channels: list[Channel] = []
        self.member_count: int = kwargs.get("member_count")
        # TODO: add threads

        # append channels
        for channel in kwargs.get("channels", []):
            # skip any non-channel channels (categories are in channels for some reason)
            if channel["type"] == 4:
                continue
            self.channels.append(Channel(**channel))

        # sort them, because discord gives them in random order
        self.channels.sort(key=lambda x: x.position)

    @staticmethod
    def from_response(response):
        """
        Generates guild instance from discord response
        """

        return Guild(
            id=response["id"],
            name=response["properties"]["name"],
            channels=response["channels"],
            member_count=response["member_count"]
        )


class Client:
    user: User | None = None
    guilds: list[Guild] | None = []
    current_channel: Channel | None = Channel()

    def __init__(self):
        self._auth: str | None = None
        self._socket: websockets.WebSocketClientProtocol | None = None

        self._heartbeat_interval = None
        self._sequence = None

        self.terminal: Term = Term()
        self.terminal.input_callback = self.process_user_commands

    def run(self, token: str) -> None:
        """
        Connects the client
        """

        self._auth = token

        async def coro():
            async with websockets.connect(GATEWAY) as websocket:
                self._socket = websocket
                self._heartbeat_interval = (await self.get_request())["d"]["heartbeat_interval"]

                await self.send_request(
                    {
                        "op": 2,
                        "d": {
                            "token": self._auth,
                            "capabilities": 16381,
                            "properties": {
                                "os": "Windows",
                                "browser": "Chrome",
                                "device": "",
                                "system_locale": "en-US",
                                "browser_user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                                      "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                                "browser_version": "123.0.0.0",
                                "os_version": "10",
                                "referrer": "https://search.brave.com/",
                                "referring_domain": "search.brave.com",
                                "referrer_current": "",
                                "referring_domain_current": "",
                                "release_channel": "stable",
                                "client_build_number": 281369,
                                "client_event_source": None
                            }
                        }
                    }
                )

                print("Connection successful.\n")
                self.terminal.clear_terminal()
                await asyncio.gather(
                    self.process_heartbeat(),
                    self.process_input(),
                    self.terminal.start_listening()
                )

        print("Attempting connect...")
        try:
            asyncio.run(coro())
        except KeyboardInterrupt:
            pass
        except OSError:
            print("\nConnection failed!")
        print("\nConnection closed.")

    async def process_input(self) -> None:
        """
        Processes gateways input things
        """

        while True:
            response = await self.get_request()
            self._sequence = response["s"] if response["s"] else self._sequence

            # ready
            if response["t"] == "READY":
                Client.user = User(**(response["d"]["user"]))
                for guild in response["d"]["guilds"]:
                    Client.guilds.append(Guild.from_response(guild))

            # messages
            elif response["t"] == "MESSAGE_CREATE":
                # if message is in current channel
                if response["d"]["channel_id"] == Client.current_channel.id:
                    self.terminal.messages.append(Message.from_response(response["d"]))
                    self.terminal.partial_update()

            # opcode 1
            elif response["op"] == 1:
                await self.send_heartbeat()

            elif response["op"] == 9:
                self.terminal.print(f"{CLIENT_LOG} disconnected...")

            # anything else
            else:
                with open("big2.json", "a", encoding="utf8") as file:
                    file.write(json.dumps(response, indent=2) + "\n\n")

    def process_user_commands(self, user_input: list[str]) -> None:
        """
        Processes user inputted commands
        """

        # make input string a string
        user_input: str = "".join(user_input).strip(" ")

        # when user inputs // => that's a command
        if user_input[:2] == "//":
            command_raw = user_input[2:]
            command = command_raw.split(" ")

            # help command
            if command[0] == "help":
                self.terminal.print(f"{CLIENT_LOG} here's a list of instructions:{CS_RESET}")
                for help_msg in CLIENT_HELP:
                    self.terminal.print(f"\t{help_msg}")

            # list guilds command
            elif command[0] == "list_g":
                self.terminal.print(f"{CLIENT_LOG} list of guilds:{CS_RESET}")
                for idx, guild in enumerate(Client.guilds):
                    self.terminal.print(f"\t[{idx}] {guild.name}")

            # list channels in guild command
            elif command[0] == "list_c" and len(command) >= 2:
                try:
                    index = int(command[1])
                except ValueError:
                    return
                if abs(index) > len(Client.guilds):
                    return

                self.terminal.print(f"{CLIENT_LOG} list of channels:{CS_RESET}")
                for idx, channel in enumerate(Client.guilds[index].channels):
                    self.terminal.print(f"\t[{idx}] {channel.name}")

            # pick channel in guild command
            elif command[0] == "pick_c" and len(command) >= 3:
                try:
                    guild_idx = int(command[1])
                    channel_idx = int(command[2])
                except ValueError:
                    return
                if abs(guild_idx) > len(Client.guilds):
                    return
                guild = Client.guilds[guild_idx]
                if abs(channel_idx) > len(guild.channels):
                    return

                Client.current_channel = guild.channels[channel_idx]
                self.terminal.print(
                    f"{CLIENT_LOG} now viewing:{STYLE_ITALICS}{Client.current_channel.name}{CS_RESET}")

        # otherwise it's text or something, so make an API request
        else:
            if Client.current_channel.id:
                self.send_api_request(
                    request={"content": user_input},
                    http=f"{API}/channels/{Client.current_channel.id}/messages"
                )
            else:
                self.terminal.print(f"{CLIENT_LOG} you haven't chosen a channel! use '//help'{CS_RESET}")

    async def process_heartbeat(self) -> None:
        """
        Sends heartbeat event to opened gateway, to notify it that the app is running.
        Ran only once, when the connection is opened
        """

        # send heartbeat
        # wait `heartbeat_interval * jitter` as per discord docs
        await asyncio.sleep(self._heartbeat_interval * random() / 1000)
        await self.send_heartbeat()

        # continue the heartbeat
        while self._socket.open:
            await asyncio.sleep(self._heartbeat_interval / 1000)
            await self.send_heartbeat()

    async def send_heartbeat(self) -> None:
        """
        Sends heartbeat request to the gateway
        """

        await self.send_request({"op": 1, "d": self._sequence})

    async def send_request(self, request: Any) -> None:
        """
        Sends a request to connected socket
        """

        await self._socket.send(json.dumps(request))

    async def get_request(self) -> Any:
        """
        Gets request from connected socket
        """

        response = await self._socket.recv()
        if response:
            return json.loads(response)

    def send_api_request(self, request: Any, rtype: str = "POST", http: str = "") -> requests.Response:
        """
        Sends API request to discord
        """

        if rtype == "POST":
            return requests.post(http, headers={"Authorization": self._auth}, json=request)
        elif rtype == "GET":
            return requests.get(http, headers={"Authorization": self._auth}, json=request)


class Term:
    """
    Terminal rendering class
    """

    message_field: int = TERM_HEIGHT - 2
    input_field: str = '[-]: '

    def __init__(self):
        # terminal stuff
        self.messages: list[Message] = []
        self.str_lines: list[str] = []
        self.line_offset: int = 0
        self.current_line: int = 0

        # terminal user input
        self.input_callback: Callable = lambda x: None
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
            self.input_callback(self.user_input)
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

    def _print_messages(self):
        """
        Prints out all messages from message stack
        """

        while self.messages:
            message = self.messages.pop()
            formatted_message = format_message(message)
            self.print(formatted_message)

    def partial_update(self):
        """
        Partially updates the messages (prints missing ones)
        """

        self._print_messages()

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

    def update_all(self):
        """
        Updates everything on the terminal
        """

        self.clear_terminal(False)
        self._print_messages()

        start = self.line_offset
        end = min(len(self.str_lines), self.line_offset + self.message_field)
        print("\33[H" + "\n".join(self.str_lines[start:end]), end="", flush=False)
        self.current_line = end - start

        self._update_input()


def main():
    cli = Client()
    if args.auth:
        cli.run(args.auth)
    else:
        raise Exception("No authentication token was given, use \33[1;31mpython3 main.py --help\33[0m to get help")


def debug():
    terminal = Term()

    async def while_true():
        while True:
            await asyncio.sleep(0.1)

    async def coro():
        terminal.clear_terminal()
        await asyncio.gather(
            terminal.start_listening(),
            while_true())

    try:
        asyncio.run(coro())
    except KeyboardInterrupt:
        print("Ded.")


if __name__ == '__main__':
    main()
    # debug()
