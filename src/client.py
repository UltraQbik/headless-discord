import json
import asyncio
import requests
import websockets
from typing import Any
from random import random
from .types import *
from .terminal import Term


class Client:
    """
    Running client class
    """

    # connection
    auth: str | None = None
    sock: websockets.WebSocketClientProtocol | None = None

    # keep alive
    heartbeat_interval: int = 41250
    sequence: int | None = None

    # terminal
    term: Term = Term()

    # discord
    user: ClientUser | None = None

    @classmethod
    async def get_request(cls) -> Any:
        """
        Gets request from connected socket
        """

        response = await cls.sock.recv()
        if response:
            return json.loads(response)

    @classmethod
    async def send_request(cls, request: Any):
        """
        Sends a request to connected socket
        """

        await cls.sock.send(json.dumps(request))

    @classmethod
    def run(cls, token: str) -> None:
        """
        Connects the client
        """

        async def coro():
            async with websockets.connect(GATEWAY) as websock:
                cls.sock = websock
                cls.heartbeat_interval = (await cls.get_request())['d']['heartbeat_interval']
                cls.term.log("connection successful")
                await cls.send_request(
                    {
                        "op": 2,
                        "d": {
                            "token": cls.auth,
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
                cls.term.log("authentication successful")
                await asyncio.gather(
                    cls.keep_alive(),
                    cls.process_events(),
                    cls.term.start_listening()
                )
        cls.auth = token
        cls.term.clear_terminal()
        cls.term.log("attempting connection")
        try:
            asyncio.run(coro())
        except KeyboardInterrupt:
            pass
        except websockets.exceptions.ConnectionClosedOK:
            pass
        except OSError:
            cls.term.log("connection failed")
        cls.term.log("connection closed")

    @classmethod
    async def process_events(cls):
        """
        Processes discord gateway sent events
        """

        while True:
            response = await cls.get_request()
            cls.sequence = response["s"] if response["s"] else cls.sequence

    @classmethod
    async def keep_alive(cls):
        """
        Keeps the connection alive
        """

        # send first heartbeat
        await asyncio.sleep(cls.heartbeat_interval * random() / 1000)
        await cls.send_heartbeat()

        # keep alive
        while cls.sock.open:
            await asyncio.sleep(cls.heartbeat_interval / 1000)
            await cls.send_heartbeat()

    @classmethod
    async def send_heartbeat(cls):
        """
        Sends heartbeat to gateway
        """

        await cls.send_request({"op": 1, "d": cls.sequence})
