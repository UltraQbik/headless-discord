import re
from enum import Flag, auto

from .constants import *
from datetime import datetime


class Permissions(Flag):
    """
    Permissions flag enum. Oh god, there are so many
    """

    CREATE_INSTANT_INVITE = auto()
    KICK_MEMBERS = auto()
    BAN_MEMBERS = auto()
    ADMINISTRATOR = auto()
    MANAGE_CHANNELS = auto()
    MANAGE_GUILD = auto()
    ADD_REACTIONS = auto()
    VIEW_AUDIT_LOG = auto()
    PRIORITY_SPEAKER = auto()
    STREAM = auto()
    VIEW_CHANNEL = auto()
    SEND_MESSAGES = auto()
    SEND_TTS_MESSAGES = auto()
    MANAGE_MESSAGES = auto()
    EMBED_LINKS = auto()
    ATTACH_FILES = auto()
    READ_MESSAGE_HISTORY = auto()
    MENTION_EVERYONE = auto()
    USE_EXTERNAL_EMOJIS = auto()
    VIEW_GUILD_INSIGHTS = auto()
    CONNECT = auto()
    SPEAK = auto()
    MUTE_MEMBERS = auto()
    DEAFEN_MEMBERS = auto()
    MOVE_MEMBERS = auto()
    USE_VAD = auto()
    CHANGE_NICKNAME = auto()
    MANAGE_NICKNAMES = auto()
    MANAGE_ROLES = auto()
    MANAGE_WEBHOOKS = auto()
    MANAGE_GUILD_EXPRESSIONS = auto()
    USE_APPLICATION_COMMANDS = auto()
    REQUEST_TO_SPEAK = auto()
    MANAGE_EVENTS = auto()
    MANAGE_THREADS = auto()
    CREATE_PUBLIC_THREADS = auto()
    CREATE_PRIVATE_THREADS = auto()
    USE_EXTERNAL_STICKERS = auto()
    SEND_MESSAGES_IN_THREADS = auto()
    USE_EMBEDDED_ACTIVITIES = auto()
    MODERATE_MEMBERS = auto()
    VIEW_CREATOR_MONETIZATION_ANALYTICS = auto()
    USE_SOUNDBOARD = auto()
    CREATE_GUILD_EXPRESSIONS = auto()
    CREATE_EVENTS = auto()
    USE_EXTERNAL_SOUNDS = auto()
    SEND_VOICE_MESSAGES = auto()


class Role:
    """
    Role class
    """

    def __init__(self, **kwargs):
        self.id: str = kwargs.get("id")
        self.name: str = kwargs.get("name")
        self.color: int = kwargs.get("color")
        self.position: int = kwargs.get("position")
        self.permissions: Permissions = Permissions(int(kwargs.get("permissions")))


class Member:
    """
    Member class
    """

    def __init__(self, **kwargs):
        self.user: User = kwargs.get("user")
        self.nick: str | None = kwargs.get("nick")
        self.roles: list[Role] = kwargs.get("roles", list())
        self.permissions: Permissions | None = Permissions(
            int(kwargs.get("permissions"))) if "permissions" in kwargs else None


class User:
    """
    Generic user class
    """

    def __init__(self, **kwargs):
        self.id: str = kwargs.get("id")
        self.username: str = kwargs.get("username")
        self.global_name: str | None = kwargs.get("global_name")
        self.bot: bool = kwargs.get("bot", False)


class Channel:
    """
    Channel class
    """

    def __init__(self, **kwargs):
        self.id: str = kwargs.get("id")
        self.guild: Guild | None = Client.known_guilds.get(kwargs.get("guild_id"))
        self.type: int = kwargs.get("type")
        self.name: str | None = kwargs.get("name")
        self.position: int = kwargs.get("position", 0)
        self.permissions: Permissions | None = Permissions(
            int(kwargs.get("permissions"))) if "permissions" in kwargs else None

    @staticmethod
    def from_response(response: dict):
        """
        Make channel object from any response
        """

        return Channel(
            id=response["id"],  # always present
            type=response["type"],  # always present
            name=response.get("name"),  # may be present, nullable
            position=response.get("position", 0),  # may be present
            permissions=response.get("permissions")  # may be present
        )


class Guild:
    """
    Guild class
    """

    def __init__(self, **kwargs):
        self.id: str = kwargs.get("id")
        self.name: str = kwargs.get("name")
        self.description: str | None = kwargs.get("description")
        self.roles: list[Role] = kwargs.get("roles", list())
        self.channels: list[Channel] = kwargs.get("channels", list())
        self.members: list[Member] = kwargs.get("members", list())

    @staticmethod
    def from_response(response: dict):
        """
        Make guild object from GET response
        """

        roles = []
        for raw_role in response["roles"]:
            roles.append(Role(**raw_role))

        return Guild(
            id=response["id"],  # always present
            name=response["name"],  # always present
            description=response["description"],  # always present, nullable
            roles=roles  # always present
        )


class Client(User):
    """
    Client user
    """

    known_guilds: dict[str, Guild] = {}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
