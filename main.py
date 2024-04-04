import json
import asyncio
import argparse
import websockets


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

    def run(self, token: str) -> None:
        """
        Connects the client
        """

        self._auth_token = token

        async def coro():
            async with websockets.connect("wss://gateway.discord.gg/?v=10&encoding=json") as websocket:
                self._socket = websocket

                print(await self.get_request())
        asyncio.run(coro())

    async def send_request(self, request: object) -> None:
        """
        Sends a request to connected socket
        """

        pass

    async def get_request(self) -> object:
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
