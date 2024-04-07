import os
import re
import json
import asyncio
import requests
import argparse
import threading
import websockets
from typing import Any
from random import random
from datetime import datetime


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


class Guild:
    """
    Guild class
    """

    def __init__(self, **kwargs):
        self.id: str = kwargs.get("id")
        self.channels: list[Channel] = [Channel(**x) for x in kwargs["channels"]]
        self.member_count: int = kwargs.get("member_count")
        # TODO: add threads


class Client:
    user: User | None = None
    guilds: dict[str, Guild] | None = None
    current_channel: Channel | None = Channel()

    def __init__(self):
        self._auth: str | None = None
        self._socket: websockets.WebSocketClientProtocol | None = None

        self._heartbeat_interval = None
        self._sequence = None

        self.terminal: Terminal = Terminal()

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
                threading.Thread(target=self.process_user_input, daemon=True).start()
                await asyncio.gather(
                    self.process_heartbeat(),
                    self.process_input()
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
            self._sequence = response["s"]

            # ready
            if response["t"] == "READY":
                Client.user = User(**(response["d"]["user"]))
                Client.guilds = {x["id"]: Guild(**x) for x in response["d"]["guilds"]}

            # messages
            elif response["t"] == "MESSAGE_CREATE":
                # if message is in current channel
                if response["d"]["channel_id"] == Client.current_channel.id:
                    self.terminal.messages.append(Message.from_response(response["d"]))
                    self.terminal.update_messages()

            # opcode 1
            elif response["op"] == 1:
                await self.send_heartbeat()

            # anything else
            else:
                with open("big2.json", "a", encoding="utf8") as file:
                    file.write(json.dumps(response, indent=2) + "\n\n")

    def process_user_input(self) -> None:
        """
        Processes user input from terminal
        """

        self.terminal.jump_to_input()
        try:
            while True:
                self.process_user_commands(input())
                self.terminal.jump_to_input()
                self.terminal.erase_after_cursor()
        except EOFError:
            pass  # don't care, just die

    def process_user_commands(self, user_input) -> None:
        """
        Processes user inputted commands
        """

        # when user inputs // => that's a command
        if user_input[:2] == "//":
            command = user_input[2:].split(" ")
            if command[0] == "help":
                self.terminal.log_message(f"{CLIENT_LOG} here's a list of instructions:{CS_RESET}")
                for help_msg in CLIENT_HELP:
                    self.terminal.log_message(f"\t{help_msg}")

        # otherwise it's text or something, so make an API request
        else:
            if Client.current_channel.id:
                self.send_api_request(
                    request={"content": user_input},
                    http=f"{API}/channels/{Client.current_channel.id}/messages"
                )
            else:
                self.terminal.log_message(f"{CLIENT_LOG} you haven't chosen a channel! use '//help'{CS_RESET}")

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
            await asyncio.sleep(self._heartbeat_interval)
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


class Terminal:
    """
    Terminal rendering class
    """

    terminal_lines = 28  # maximum amount of lines we can use
    input_message = "[TYPE]: "

    def __init__(self):
        self.messages: list[Message] = []
        self.lines: list[str] = []
        self.line_offset: int = 0
        self.cur_line: int = 0

    @staticmethod
    def character_wrap(content: str, max_len: int = 100) -> str:
        """
        Character wraps the content
        :return: word wrapped content
        """

        line_length = 0
        new_content = ""
        for idx, char in enumerate(content):
            new_content += char
            line_length += 1
            if char == "\n":
                line_length = 0

            # add `\n` when 1 line is bigger than max_len,
            # and it's not the last character in the string
            if line_length >= max_len and idx != (len(content)-1):
                new_content += "\n"
                line_length = 0
        return new_content

    def clear_terminal(self) -> None:
        """
        Clears terminal
        """

        os.system("cls" if os.name == "nt" else "clear")
        print(f"\33[{self.terminal_lines};0H", end="")
        print(f"\33[100m{'='*120}{CS_RESET}\n{self.input_message}", end="")
        print("\33[H", end="")

        self.cur_line = 0

    def next_page(self) -> None:
        """
        Clears the terminal, and offsets line offset variable
        """

        self.line_offset = max(self.line_offset + self.cur_line, len(self.lines) - self.terminal_lines//2)
        self.clear_terminal()

    @staticmethod
    def apply_style(content: str, brackets: str, style: str):
        """
        Applies style to the content string
        """

        brs = "\\" + "\\".join(list(brackets))
        regex = brs + r"(.*?)" + brs
        for string in re.findall(regex, content):
            content = content.replace(f"{brackets}{string}{brackets}", f"{style}{string}{CS_RESET}")
        return content

    def format_message(self, message: Message) -> str:
        """
        Returns terminal formatted message
        """

        timestamp = message.timestamp.strftime("%H:%M:%S")
        nickname = message.author.nickname
        newline_offset = len(timestamp) + len(nickname) + 3

        content = message.content

        # apply styles
        content = self.apply_style(content, "**", STYLE_BOLD)
        content = self.apply_style(content, "*", STYLE_ITALICS)
        content = self.apply_style(content, "__", STYLE_UNDERLINE)
        content = self.apply_style(content, "--", STYLE_STRIKETHROUGH)
        content = self.apply_style(content, "`", CODE_BLOCK)

        # character wrap content
        content = self.character_wrap(content, 120 - newline_offset - 2)
        content = content.replace("\n", f"\n{STYLE_DARKEN}{'-'*newline_offset}>{CS_RESET} ")

        return f"{STYLE_DARKEN}[{timestamp}]{CS_RESET} {nickname}{STYLE_DARKEN}>{CS_RESET} {content}"

    def truncate_buffer(self, amount=50) -> None:
        """
        Truncates message buffer (when needed), to just not waste ram
        """

        if len(self.messages) > amount:
            self.line_offset -= len(self.messages) - amount
            self.messages = self.messages[:-amount]
            self._write_messages()

    def _write_messages(self):
        """
        Rewrites all messages to lines
        """

        self.lines.clear()
        for message in self.messages:
            self.lines += self.format_message(message).split("\n")

    def jump_to_print(self) -> None:
        """
        Jumps to position, where the messages are printed
        """

        print(f"\33[{self.cur_line+1};0H", end="", flush=True)

    def jump_to_input(self) -> None:
        """
        Jumps to position, where the message is inputted
        """

        print(f"\33[{self.terminal_lines+1};{len(self.input_message)+1}H", end="", flush=True)

    @staticmethod
    def store_cursor() -> None:
        """
        Stores cursor's current position
        """

        print("\33[s", end="", flush=True)

    @staticmethod
    def restore_cursor() -> None:
        """
        Restores cursor's previous position.
        Uses SCO, because DEC did not work at all for some reason (using NU shell)
        """

        print("\33[u", end="", flush=True)

    @staticmethod
    def erase_after_cursor() -> None:
        """
        Erases everything after the cursor
        """

        print("\33[0J", end="", flush=True)

    def log_message(self, message: str) -> None:
        """
        Logs your own message, cautious of user input stuff
        """

        self.lines += message.split("\n")
        self.update_messages(False)

    def update_all(self) -> None:
        """
        Re-prints all the messages to the terminal.
        Uses SCO, because DEC did not work at all for some reason (using NU shell)
        """

        self.truncate_buffer()
        self.clear_terminal()

        self.line_offset = len(self.lines) - self.terminal_lines//2
        self.cur_line = 0

        self.update_messages()

    def update_messages(self, read_last=True):
        """
        Updates terminal with new message
        """

        if read_last:
            self.lines += self.format_message(self.messages[-1]).split("\n")

        # when the message overflows to the next page
        if self.cur_line >= (self.terminal_lines-1):
            self.next_page()

        self.store_cursor()
        self.jump_to_print()

        start = self.line_offset + self.cur_line
        end = min(start + self.terminal_lines, len(self.lines)-1) + 1

        self.cur_line += end - start
        if self.cur_line >= self.terminal_lines:
            end -= self.cur_line - self.terminal_lines + 1
            self.cur_line = self.terminal_lines - 1

        print("\n".join(self.lines[start:end]), end="\n" if self.cur_line < (self.terminal_lines-1) else "")
        self.restore_cursor()


def main():
    cli = Client()
    if args.auth:
        cli.run(args.auth)
    else:
        raise Exception("No authentication token was given, use \33[1;31mpython3 main.py --help\33[0m to get help")


if __name__ == '__main__':
    main()
