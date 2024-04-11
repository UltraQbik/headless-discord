import re
from enum import Enum, Flag, auto

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


class ChannelType(Enum):
    """
    Channel type enum
    """

    GUILD_TEXT = 0
    DM = 1
    GUILD_VOICE = 2
    GROUP_DM = 3
    GUILD_CATEGORY = 4
    GUILD_ANNOUNCEMENT = 5
    ANNOUNCEMENT_THREAD = 10
    PUBLIC_THREAD = 11
    PRIVATE_THREAD = 12
    GUILD_STAGE_VOICE = 13
    GUILD_DIRECTORY = 14
    GUILD_FORUM = 15
    GUILD_MEDIA = 16


class MessageType(Enum):
    """
    Message type enum
    """

    DEFAULT = 0
    RECIPIENT_ADD = 1
    RECIPIENT_REMOVE = 2
    CALL = 3
    CHANNEL_NAME_CHANGE = 4
    CHANNEL_ICON_CHANGE = 5
    CHANNEL_PINNED_MESSAGE = 6
    USER_JOIN = 7
    GUILD_BOOST = 8
    GUILD_BOOST_TIER_1 = 9
    GUILD_BOOST_TIER_2 = 10
    GUILD_BOOST_TIER_3 = 11
    CHANNEL_FOLLOW_ADD = 12
    GUILD_DISCOVERY_DISQUALIFIED = 14
    GUILD_DISCOVERY_REQUALIFIED = 15
    GUILD_DISCOVERY_GRACE_PERIOD_INITIAL_WARNING = 16
    GUILD_DISCOVERY_GRACE_PERIOD_FINAL_WARNING = 17
    THREAD_CREATED = 18
    REPLY = 19
    CHAT_INPUT_COMMAND = 20
    THREAD_STARTER_MESSAGE = 21
    GUILD_INVITE_REMINDER = 22
    CONTEXT_MENU_COMMAND = 23
    AUTO_MODERATION_ACTION = 24
    ROLE_SUBSCRIPTION_PURCHASE = 25
    INTERACTION_PREMIUM_UPSELL = 26
    STAGE_START = 27
    STAGE_END = 28
    STAGE_SPEAKER = 29
    STAGE_TOPIC = 31
    GUILD_APPLICATION_PREMIUM_SUBSCRIPTION = 32


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


class Attachment:
    """
    Attachment object class
    """

    def __init__(self, **kwargs):
        self.id: str = kwargs.get("id")
        self.filename: str = kwargs.get("filename")
        self.size: int = kwargs.get("size")
        self.url: str = kwargs.get("url")


class Member:
    """
    Member class
    """

    def __init__(self, **kwargs):
        self.user: User = kwargs.get("user")
        self.guild: Guild | None = ClientUser.known_guilds.get(kwargs.get("guild_id"))
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
        # self.discriminator: str = kwargs.get("discriminator")
        self.global_name: str | None = kwargs.get("global_name")
        self.bot: bool = kwargs.get("bot", False)

        # discriminator will not be added for now, as it's been basically deprecated by discord


class Channel:
    """
    Channel class
    """

    def __init__(self, **kwargs):
        self.id: str = kwargs.get("id")
        self.guild: Guild | None = ClientUser.known_guilds.get(kwargs.get("guild_id"))
        self.type: ChannelType = ChannelType(kwargs.get("type"))
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


class PrivateChannel(Channel):
    """
    Private channel class
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


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


class ClientUser(User):
    """
    Client user
    """

    known_guilds: dict[str, Guild] = {}
    known_channels: dict[str, Channel] = {}
    private_channels: dict[str, PrivateChannel] = {}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class Message:
    """
    Message class
    """

    def __init__(self, **kwargs):
        self.id: str = kwargs.get("id")
        self.channel: Channel | None = ClientUser.known_guilds.get(kwargs.get("channel_id"))
        self.author: User = kwargs.get("author")
        self.content: str = kwargs.get("content")
        self.type: MessageType = MessageType(int(kwargs.get("type")))
        self.timestamp: datetime = datetime.fromisoformat(kwargs.get("timestamp"))
        self.edited_timestamp: datetime = datetime.fromisoformat(
            kwargs.get("edited_timestamp")) if kwargs.get("edited_timestamp") else None
        self.mention_everyone: bool = kwargs.get("mention_everyone", False)
        self.mentions: list[User] = kwargs.get("mentions", list())
        self.mention_roles: list[Role] = kwargs.get("mention_roles", list())
        self.attachments: list[Attachment] = kwargs.get("attachments", list())
        # self.embeds: list = kwargs.get("embeds", list())  # e
