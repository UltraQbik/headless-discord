import os
import argparse
import asyncio
from datetime import datetime

from src import Client
from src import Term
from src import format_message
from src import Message


# parser
parser = argparse.ArgumentParser(
    prog="HeadlessDiscord",
    description="Terminal version of discord")
parser.add_argument("--auth",
                    help="authentication token (your discord token)",
                    default=os.getenv("DISCORD_AUTH"), required=False)
parser.add_argument("-d", "--debug",
                    help="debug terminal", action="store_true")
args = parser.parse_args()


def main():
    cli = Client()
    if args.auth:
        cli.run(args.auth)
    else:
        raise Exception("No authentication token was given, use \33[1;31mpython3 main.py --help\33[0m to get help")


def debug():
    terminal = Term()

    async def while_true():
        while True:
            await asyncio.sleep(0.1)

    async def input_callback(user_input: list[str]):
        user_input = "".join(user_input).strip(" ")
        terminal.print(user_input)

    async def coro():
        terminal.clear_terminal()
        terminal.input_callback = input_callback

        for x in range(100):
            terminal.print(f"[{x}] text {x**3}")

        for _ in range(10):
            terminal.log("\t╭───┤𝐆𝐄𝐍𝐄𝐑𝐀𝐋├──────")

        await asyncio.gather(
            terminal.start_listening(),
            while_true())

    try:
        asyncio.run(coro())
    except KeyboardInterrupt:
        terminal.log("ded.")


if __name__ == '__main__':
    if args.debug:
        debug()
    else:
        main()
