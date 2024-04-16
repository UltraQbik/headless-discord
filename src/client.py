import json
import asyncio
import requests
import websockets
from typing import Any
from random import random
from .types import *
from .terminal import Terminal


class Client:
    """
    Running client class
    """

    # connection
    _auth: str | None = None
    _sock: websockets.WebSocketClientProtocol | None = None

    # keep alive
    _heartbeat_interval: int = 41250
    _sequence: int | None = None

    # discord
    user: ClientUser | None = None

    @classmethod
    async def get_request(cls) -> Any:
        """
        Gets request from connected socket
        """

        response = await cls._sock.recv()
        if response:
            return json.loads(response)

    @classmethod
    async def send_request(cls, request: Any):
        """
        Sends a request to connected socket
        """

        await cls._sock.send(json.dumps(request))

    @classmethod
    async def send_post_request(cls, **kwargs):
        """
        Sends POST API request
        """

        # append authorization header is missing
        if "headers" not in kwargs:
            kwargs["headers"] = {}
        if "Authorization" not in kwargs["headers"]:
            kwargs["headers"]["Authorization"] = cls._auth

        return await asyncio.to_thread(requests.post, **kwargs)

    @classmethod
    def run(cls, token: str) -> None:
        """
        Connects the client
        """

        async def coro():
            async with websockets.connect(GATEWAY) as websock:
                cls._sock = websock
                cls._heartbeat_interval = (await cls.get_request())['d']['heartbeat_interval']
                Terminal.log("connection successful")
                await cls.send_request(
                    {
                        "op": 2,
                        "d": {
                            "token": cls._auth,
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
                Terminal.log("authentication successful")
                Terminal.input_callback = process_user_input
                await asyncio.gather(
                    cls._keep_alive(),
                    cls._event_handle(),
                    Terminal.start_listening()
                )
        cls._auth = token
        Terminal.clear_terminal()
        Terminal.log("attempting connection")
        try:
            asyncio.run(coro())
        except KeyboardInterrupt:
            pass
        except websockets.exceptions.ConnectionClosedOK:
            pass
        except OSError:
            Terminal.log("connection failed")
        Terminal.log("connection closed")

    @classmethod
    async def _event_handle(cls):
        """
        Processes discord gateway sent events
        """

        while True:
            response = await cls.get_request()
            cls._sequence = response["s"] if response["s"] else cls._sequence

            await cls._process_event(response)

    @classmethod
    async def _keep_alive(cls):
        """
        Keeps the connection alive
        """

        # send first heartbeat
        await asyncio.sleep(cls._heartbeat_interval * random() / 1000)
        await cls._send_heartbeat()

        # keep alive
        while cls._sock.open:
            await asyncio.sleep(cls._heartbeat_interval / 1000)
            await cls._send_heartbeat()

    @classmethod
    async def _send_heartbeat(cls):
        """
        Sends heartbeat to gateway
        """

        await cls.send_request({"op": 1, "d": cls._sequence})

    @classmethod
    async def close(cls):
        """
        Closes the connection
        """

        await cls._sock.close()

    @classmethod
    async def on_ready(cls):
        """
        Stuff that will happen after the READY event was processed
        """

        Terminal.log("ready!")

    @classmethod
    async def on_message_create(cls, message: Message):
        """
        Stuff that will happen when a message is received
        """

        if cls.user.focus_channel and message.channel.id == cls.user.focus_channel.id:
            Terminal.print_message(message)

    @classmethod
    async def _process_event(cls, event):
        """
        Processes the event
        """

        event_type = event["t"]
        event_data = event["d"]

        # READY event (when authorised)
        if event_type == "READY":
            # get current's user info
            cls.user = ClientUser(
                id=event_data["user"]["id"],
                username=event_data["user"]["username"])

            # get known users
            for user_raw in event_data["users"]:
                user = User(
                    id=user_raw["id"],
                    username=user_raw["username"],
                    global_name=user_raw["global_name"],
                    bot=user_raw.get("bot"))

                cls.user.known_users.append(user)

            # get all private channels
            for channel_raw in event_data["private_channels"]:
                # get recipients
                recipients = []
                for usr in cls.user.known_users:
                    if usr.id in channel_raw["recipient_ids"]:
                        recipients.append(usr)

                channel = Channel(
                    id=channel_raw["id"],
                    type=channel_raw["type"],
                    recipients=recipients)

                cls.user.private_channels.append(channel)

            # get some guilds
            for guild_raw in event_data["guilds"]:
                guild = Guild(
                    id=guild_raw["id"],
                    name=guild_raw["properties"]["name"],
                    description=guild_raw["properties"]["description"],
                    roles=[Role(**x) for x in guild_raw["roles"]],
                    channels=[Channel(**x) for x in guild_raw["channels"]])

                cls.user.known_guilds.append(guild)

            await cls.on_ready()

        # READY_SUPPLEMENTAL event (after READY event)
        elif event_type == "READY_SUPPLEMENTAL":
            # data here is not very useful (yet)
            pass

        # SESSIONS_REPLACE event (after READY_SUPPLEMENTAL event)
        elif event_type == "SESSIONS_REPLACE":
            # data here is not very useful (yet)
            pass

        # MESSAGE_CREATE
        elif event_type == "MESSAGE_CREATE":
            message = Message.from_create_event(event_data)
            await cls.on_message_create(message)


async def process_user_input(user_input: list[str]):
    """
    Processes user inputted text
    """

    string = "".join(user_input).rstrip(" ")

    # commands
    if string[:2] == "//":
        command = string[2:].split(" ")

        # help cmd
        if command[0] == "help":
            Terminal.log("list of commands")
            for cmd in CLIENT_HELP:
                aliases = f" {CLIENT_COL[2]}or{CLIENT_COL[3]} ".join(cmd['cmd'])
                aliases += " " if cmd['args'] else ""
                args = f" ".join(cmd['args'])
                Terminal.log(
                    f"\t{CLIENT_COL[3]}{aliases}{CLIENT_COL[2]}"
                    f"{STYLE_ITALICS}{args}{CS_RESET}"
                    f"{CLIENT_COL[2]} - {cmd['text']}"
                )

        # list guilds cmd
        elif command[0] == "lg" or command[0] == "list_g":
            Terminal.log("list of guilds")
            for idx, guild in enumerate(Client.user.known_guilds):
                Terminal.log(f"\t[{idx}] {guild.name}")

        # list channels cmd
        elif command[0] == "lc" or command[0] == "list_c":
            # check amount of arguments
            if len(command) < 2:
                Terminal.log(f"please enter the {STYLE_BOLD}guild{CS_RESET} field")
                return

            # check index
            try:
                index = int(command[1])
                if index > len(Client.user.known_guilds) or index < 0:
                    raise ValueError
            except ValueError:
                Terminal.log(f"incorrect guild index")
                return

            Terminal.log(f"list of channels for [{index}]")
            count = 0
            for channel in Client.user.known_guilds[index].channels:
                if channel.type != ChannelType.GUILD_CATEGORY:
                    Terminal.log(f"\t[{count}] {channel.name}")
                    count += 1
                else:
                    Terminal.log(f"\t[+] {channel.name}")

        # list private channels cmd
        elif command[0] == "lpc" or command[0] == "list_pc":
            Terminal.log("list of private channels")
            for idx, channel in enumerate(Client.user.private_channels):
                Terminal.log(f"\t[{idx}] {channel.recipients[0].username}")

        # pick channel cmd
        elif command[0] == "pc" or command[0] == "pick_c":
            # check amount of arguments
            if len(command) < 2:
                Terminal.log(f"use {STYLE_BOLD}//help{CS_RESET} to check command syntax")
                return

            # private channels
            if len(command) == 2:
                # check index
                try:
                    channel_idx = int(command[1])
                    if channel_idx > len(Client.user.private_channels) or channel_idx < 0:
                        raise ValueError
                except ValueError:
                    Terminal.log(f"incorrect channel index")
                    return

                Client.user.focus_channel = Client.user.private_channels[channel_idx]
                Terminal.log(f"now chatting with {Client.user.focus_channel.recipients[0].username}")

            # guild channels
            else:
                # check guild index
                try:
                    guild_idx = int(command[1])
                    if guild_idx > len(Client.user.known_guilds) or guild_idx < 0:
                        raise ValueError
                except ValueError:
                    Terminal.log(f"incorrect guild index")
                    return
                # check channel index
                try:
                    channel_idx = int(command[2])
                    count = 0
                    for channel in Client.user.known_guilds[guild_idx].channels:
                        if channel_idx == count and channel.type != ChannelType.GUILD_CATEGORY:
                            break
                        if channel.type != ChannelType.GUILD_CATEGORY:
                            count += 1
                    else:
                        raise ValueError
                except ValueError:
                    Terminal.log(f"incorrect channel index")
                    return

                Client.user.focus_channel = channel
                Terminal.log(f"now focused on {Client.user.focus_channel.name}")

        # exit cmd
        elif command[0] == "e" or command[0] == "exit":
            await Client.close()

    # just a message
    else:
        if Client.user.focus_channel:
            await Client.send_post_request(
                url=f"{API}/channels/{Client.user.focus_channel.id}/messages",
                json={"content": string})
        else:
            Terminal.log(
                f"please pick a channel first. Use {CLIENT_COL[3]}//help{CLIENT_COL[2]} to see all commands")
