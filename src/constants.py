# terminal
TERM_WIDTH = 120
TERM_HEIGHT = 30
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
CLIENT_LOG = "\33[35m[CLIENT]\33[95m"
CLIENT_HELP = [
    "//help - prints out this message",
    "//list_g - prints out list of all guilds",
    f"//list_c {STYLE_ITALICS}guild{CS_RESET} - prints out channels in a guild",
    f"//pick_c {STYLE_ITALICS}guild{CS_RESET} {STYLE_ITALICS}channel{CS_RESET} - selects a channel to view",
    "//exit - closes the connection"
]
