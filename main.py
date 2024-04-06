import os
import re
import json
import asyncio
import argparse
import websockets
from typing import Any
from random import random
from datetime import datetime


# pings
PING_HIGHLIGHT = "\33[36m"
PING_ME_HIGHLIGHT = "\33[1;36m"
STYLE_DARKEN = "\33[90m"
CODE_BLOCK = "\33[2m"

# styles
CS_RESET = "\33[0m"
STYLE_BOLD = "\33[1m"
STYLE_ITALICS = "\33[3m"
STYLE_UNDERLINE = "\33[4m"
STYLE_STRIKETHROUGH = "\33[9m"

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
    guilds: list[Guild] | None = None
    current_guild: Guild | None = None
    current_channel: Channel | None = None

    def __init__(self):
        self._auth_token: str | None = None
        self._socket: websockets.WebSocketClientProtocol | None = None

        self._heartbeat_interval = None
        self._sequence = None

        self._terminal: Terminal = Terminal()

    def run(self, token: str) -> None:
        """
        Connects the client
        """

        self._auth_token = token

        async def coro():
            async with websockets.connect("wss://gateway.discord.gg/?v=9&encoding=json") as websocket:
                self._socket = websocket
                self._heartbeat_interval = (await self.get_request())["d"]["heartbeat_interval"]

                await self.send_request(
                    {
                        "op": 2,
                        "d": {
                            "token": self._auth_token,
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
                self._terminal.clear_terminal()
                await asyncio.gather(
                    self.process_heartbeat(),
                    self.process_input())

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
                Client.guilds = [Guild(**x) for x in response["d"]["guilds"]]

            # messages
            elif response["t"] == "MESSAGE_CREATE":
                self._terminal.messages.append(Message.from_response(response["d"]))
                self._terminal.update_messages()

            # opcode 1
            elif response["op"] == 1:
                await self.send_heartbeat()

            # anything else
            else:
                with open("big.json", "a", encoding="utf8") as file:
                    file.write(json.dumps(response, indent=2) + "\n\n")

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


class Terminal:
    """
    Terminal rendering class
    """

    terminal_lines = 29  # maximum amount of lines we can use

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
        print(f"\33[100m{'='*120}{CS_RESET}\n[TYPE]: ", end="")
        print("\33[H", end="")

        self.cur_line = 0

    def next_page(self) -> None:
        """
        Clears the terminal, and offsets line offset variable
        """

        self.line_offset = max(self.line_offset + self.cur_line, len(self.lines) - self.terminal_lines//2)
        self.clear_terminal()

    def format_message(self, message: Message) -> str:
        """
        Returns terminal formatted message
        """

        timestamp = message.timestamp.strftime("%H:%M:%S")
        nickname = message.author.nickname

        newline_offset = len(timestamp) + len(nickname) + 3
        content = self.character_wrap(message.content, 120 - newline_offset - 2)
        content = content.replace("\n", f"\n{STYLE_DARKEN}{'-'*newline_offset}>{CS_RESET} ")

        return f"{STYLE_DARKEN}[{timestamp}]{CS_RESET} {nickname}> {content}"

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

    def update_all(self) -> None:
        """
        Re-prints all the messages to the terminal
        """

        self.truncate_buffer()
        self.clear_terminal()

        self.line_offset = len(self.lines) - self.terminal_lines//2
        self.cur_line = 0

        self.update_messages()

    def update_messages(self):
        """
        Updates terminal with new message
        """

        self.lines += self.format_message(self.messages[-1]).split("\n")

        # when the message overflows to the next page
        if self.cur_line >= (self.terminal_lines-1):
            self.next_page()

        start = self.line_offset + self.cur_line
        end = min(start + self.terminal_lines, len(self.lines)-1) + 1

        self.cur_line += end - start
        if self.cur_line >= self.terminal_lines:
            end -= self.cur_line - self.terminal_lines + 1
            self.cur_line = self.terminal_lines - 1

        print("\n".join(self.lines[start:end]), end="\n" if self.cur_line < (self.terminal_lines-1) else "")


def main():
    cli = Client()
    if args.auth:
        cli.run(args.auth)
    else:
        raise Exception("No authentication token was given, use \33[1;31mpython3 main.py --help\33[0m to get help")


if __name__ == '__main__':
    main()
