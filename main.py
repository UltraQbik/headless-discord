import json
import asyncio
import argparse


parser = argparse.ArgumentParser(
    prog="HeadlessDiscord",
    description="Terminal version of discord",
    epilog="I think it breaks discord's TOS")
parser.add_argument("auth", help="authentication token (your discord token)")
args = parser.parse_args()


class Client:
    def __init__(self):
        self._auth_token: str | None = None
        self._socket: None = None
        self._hb_interval = None

    def run(self, token: str) -> None:
        """
        Connects the client
        """

        self._auth_token = token

    async def send_request(self, request: object) -> None:
        """
        Sends a request to connected socket
        """

        pass

    async def get_request(self) -> object:
        """
        Gets request from connected socket
        """

        pass


def main():
    cli = Client()
    cli.run(args.auth)


if __name__ == '__main__':
    main()
