import json
import asyncio
import requests
import websockets
from typing import Any
from random import random
from .types import *
from .terminal import Term


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

                self.terminal.log("connection successful!")
                await asyncio.gather(
                    self.process_heartbeat(),
                    self.process_input(),
                    self.terminal.start_listening()
                )

        self.terminal.clear_terminal()
        self.terminal.log("attempting connection")
        try:
            asyncio.run(coro())
        except KeyboardInterrupt:
            pass
        except websockets.exceptions.ConnectionClosedOK:
            pass
        except OSError:
            self.terminal.log("connection failed")

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
                    self.terminal.update_onscreen()

            # opcode 1
            elif response["op"] == 1:
                await self.send_heartbeat()

            elif response["op"] == 9:
                self.terminal.print(f"{CLIENT_LOG} disconnected...")

            # anything else
            else:
                with open("big2.json", "a", encoding="utf8") as file:
                    file.write(json.dumps(response, indent=2) + "\n\n")

    async def process_user_commands(self, user_input: list[str]) -> None:
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
                self.terminal.log(f"here's a list of instructions:")
                for help_msg in CLIENT_HELP:
                    self.terminal.log(f"\t{help_msg}")

            # list guilds command
            elif command[0] == "list_g":
                self.terminal.log(f"list of guilds:")
                for idx, guild in enumerate(Client.guilds):
                    self.terminal.log(f"\t[{idx}] {guild.name}")

            # list channels in guild command
            elif command[0] == "list_c" and len(command) >= 2:
                try:
                    index = int(command[1])
                except ValueError:
                    return
                if abs(index) > len(Client.guilds):
                    return

                self.terminal.log(f"list of channels:")
                for idx, channel in enumerate(Client.guilds[index].channels):
                    self.terminal.log(f"\t[{idx}] {channel.name}")

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

                # fetch channel messages
                try:
                    response = self.send_api_request(
                        rtype="GET", request=None,
                        http=f"{API}/channels/{Client.current_channel.id}/messages?limit=50")
                    messages = response.json()
                except requests.exceptions.JSONDecodeError:
                    self.terminal.log("error when loading messages")
                    messages = []
                messages.sort(key=lambda x: datetime.fromisoformat(x['timestamp']))

                # append them to terminal
                self.terminal.messages += [
                    Message.from_response(x) for x in messages
                ]

                self.terminal.log(f"now viewing:{STYLE_ITALICS}{Client.current_channel.name}")

            elif command[0] == "exit":
                await self._socket.close()
                self.terminal.log("connection closed")

        # otherwise it's text or something, so make an API request
        else:
            if Client.current_channel.id:
                self.send_api_request(
                    request={"content": user_input},
                    http=f"{API}/channels/{Client.current_channel.id}/messages"
                )
            else:
                self.terminal.log(f"you haven't chosen a channel! use '//help'")

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
