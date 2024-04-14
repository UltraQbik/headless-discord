# terminal
TERM_CURSOR = "\33[42m"
TERM_INPUT_FIELD = "\33[48;5;236m"

# API links
GATEWAY = r"wss://gateway.discord.gg/?v=9&encoding=json"
API = r"https://discord.com/api/v9"

# pings
PING_HIGHLIGHT = "\33[36m"
PING_ME_HIGHLIGHT = "\33[96m"
STYLE_DARKEN = "\33[90m"
CODE_BLOCK = "\33[48;5;234m"

# styles
CS_RESET = "\33[0m"
STYLE_BOLD = "\33[1m"
STYLE_ITALICS = "\33[3m"
STYLE_UNDERLINE = "\33[4m"
STYLE_STRIKETHROUGH = "\33[9m"

# client
CLIENT_COL = [
    "\33[38;5;93m",
    "\33[38;5;135m",
    "\33[38;5;177m",
    "\33[38;5;219m"]
CLIENT_HELP = [
    {
        "cmd": ["lg", "list_g"],
        "args": [],
        "text": "lists all known to user guilds"
    },
    {
        "cmd": ["lc", "list_c"],
        "args": ["guild"],
        "text": "lists all channels in a guild"
    },
    {
        "cmd": ["lpc", "list_pc"],
        "args": [],
        "text": "lists all private channels (dms)"
    },
    {
        "cmd": ["pc", "pick_c"],
        "args": ["guild/channel", "channel"],
        "text": "pick channel to focus on. Private channel is arg 1"
    },
    {
        "cmd": ["e", "exit"],
        "args": [],
        "text": "close connection and exit"
    }
]
