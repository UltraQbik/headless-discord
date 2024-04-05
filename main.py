import re
import json
import asyncio
import argparse
import websockets
from typing import Any
from random import random
from datetime import datetime


parser = argparse.ArgumentParser(
    prog="HeadlessDiscord",
    description="Terminal version of discord")
parser.add_argument("auth", help="authentication token (your discord token)")
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

        # guild data
        self.member: Member | None = Member(**(kwargs["member"])) if "member" in kwargs else None

    @property
    def nickname(self) -> str:
        """
        Returns member's nickname. If user is not a guild member, falls back to username
        """

        if self.member and self.member.nick:
            return self.member.nick
        return self.username

    @staticmethod
    def from_response(response: dict):
        """
        Generates user instance from discord response
        :return: User
        """

        return User(
            **(response["author"]),
            member=response.get("member", {}))

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
        self.mentions: list[User] | None = [
            User.from_response_mention(x) for x in kwargs.get("mentions", [])]
        self.content = kwargs.get("content")

        # guild data
        self.guild_id: str | None = kwargs.get("guild_id")

    @staticmethod
    def from_response(response: dict):
        """
        Generates message instance from discord response
        :return: Message
        """

        return Message(**response)

    def __str__(self):
        return f"[{self.timestamp.strftime('%H:%M:%S')}] {self.author.nickname}> {self.content}"


class Client:
    def __init__(self):
        self._auth_token: str | None = None
        self._socket: websockets.WebSocketClientProtocol | None = None

        self._heartbeat_interval = None
        self._sequence = None

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
        print("Connection closed.")

    async def process_input(self) -> None:
        """
        Processes gateways input things
        """

        while True:
            response = await self.get_request()
            self._sequence = response["s"]

            if response["t"] == "MESSAGE_CREATE":
                # with open("dump.json", "a", encoding='utf8') as file:
                #     file.write(json.dumps(response, indent=2) + '\n\n')

                message = Message.from_response(response['d'])
                print(message)

    @staticmethod
    def message(response: dict):
        """
        Processes the message
        """

        message_timestamp = datetime.fromisoformat(response["d"]["timestamp"])
        message_author = response["d"]["author"]
        message_content = response["d"]["content"]

        if response["d"]["mentions"]:
            mentions = re.findall(r"<(.*?)>", message_content)
            for mention_id in mentions:
                mention_username = None
                for user in response["d"]["mentions"]:
                    if user["id"] == mention_id:
                        mention_username = user["username"]
                        break

                message_content = message_content.replace(f"<@{mention_id}>", mention_username)

        return f"[{message_timestamp.strftime('%H:%M:%S')}] {message_author['username']}> {message_content}"

    async def process_heartbeat(self) -> None:
        """
        Sends heartbeat event to opened gateway, to notify it that the app is running.
        Ran only once, when the connection is opened
        """

        # send heartbeat
        # wait `heartbeat_interval * jitter` as per discord docs
        await asyncio.sleep(self._heartbeat_interval * random() / 1000)
        await self.send_request({"op": 1, "d": None})

        # continue the heartbeat
        while self._socket.open:
            await asyncio.sleep(self._heartbeat_interval)
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


def main():
    cli = Client()
    cli.run(args.auth)


if __name__ == '__main__':
    main()
