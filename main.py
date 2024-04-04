import json
import asyncio
import argparse
import re

import websockets
from typing import Any
from random import random
from datetime import datetime


parser = argparse.ArgumentParser(
    prog="HeadlessDiscord",
    description="Terminal version of discord",
    epilog="I think it breaks discord's TOS")
parser.add_argument("auth", help="authentication token (your discord token)")
args = parser.parse_args()


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
                print(self.message(response))

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
