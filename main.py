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


class User:
    """
    User class
    """

    def __init__(self, **kwargs):
        # general info
        self.id: str = kwargs.get('id')
        self.name: str = kwargs.get('name')

        # guild member
        self.nick: str = kwargs.get('nick')
        self.roles: list[str] = kwargs.get('roles')
        self.muted: bool = kwargs.get('muted')
        self.deafen: bool = kwargs.get('deafen')
        self.joined_at: datetime = datetime.fromisoformat(kwargs['joined_at']) if kwargs.get('joined_at') else None

    @staticmethod
    def from_mention(response: dict):
        """
        Creates user instance from response
        :return: User
        """

        user = User(
            id=response['id'],
            name=response['username'])
        if response['member']:
            user.roles = response['member']['roles']
            user.nick = response['member']['nick']
            user.joined_at = response['member']['joined_at']
            user.muted = response['member']['mute']
            user.deafen = response['member']['deaf']

        return user


class Message:
    """
    Message class
    """

    def __init__(self, **kwargs):
        self.id: str = kwargs.get('id')
        self.guild_id: str = kwargs.get('guild_id')
        self.channel_id: str = kwargs.get('channel_id')
        self.timestamp: datetime = datetime.fromisoformat(kwargs.get('timestamp')) if kwargs.get('timestamp') else None
        self.reference: int = kwargs.get('reference')
        self.content: str = kwargs.get('content')
        self.mentions: list[User] = kwargs.get('mentions')
        self.author: User = kwargs.get('author')

    @staticmethod
    def from_response(response: dict):
        """
        Creates message instance from discord response
        :return: Message
        """

        author = User(
            id=response['author']['id'],
            name=response['author']['username'],
            nick=response['member']['nick'],
            roles=response['member']['roles'],
            joined_at=response['member']['joined_at'],
            muted=response['member']['mute'],
            deafen=response['member']['deaf']
        )

        return Message(
            id=response['id'],
            guild_id=response['guild_id'],
            channel_id=response['channel_id'],
            timestamp=response['timestamp'],
            reference=response['referenced_message'],
            content=response['content'],
            author=author
        )

    def __str__(self):
        return f"[{self.timestamp.strftime('%H:%M:%S')}] {self.author.nick}> {self.content}"


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
                message = Message.from_response(response['d'])
                print(message)

                with open("dump.json", "a", encoding='utf8') as file:
                    file.write(json.dumps(response, indent=2) + '\n\n')

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
