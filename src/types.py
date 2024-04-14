import re
from enum import Enum, IntFlag, auto

from .constants import *
from datetime import datetime


class Permissions(IntFlag):
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
        """
        :key id: role id
        :key name: role name
        :key color: role color
        :key position: role position
        :key permissions: role's permissions value
        """

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
        """
        :key id: attachment id
        :key filename: attachment's filename
        :key size: size in bytes
        :key url: url to attachment
        """

        self.id: str = kwargs.get("id")
        self.filename: str = kwargs.get("filename")
        self.size: int = kwargs.get("size")
        self.url: str = kwargs.get("url")


class Member:
    """
    Member class
    """

    def __init__(self, **kwargs):
        """
        :key user: user reference
        :key guild_id: member guild id
        :key guild: member guild
        :key nick: member's nickname
        :key roles: member's roles
        :key permissions: member's permissions
        """

        self.user: User = kwargs.get("user")
        self.guild: Guild | None = None
        self.nick: str | None = kwargs.get("nick")
        self.roles: list[Role] = kwargs.get("roles", list())
        self.permissions: Permissions | None = Permissions(
            int(kwargs.get("permissions"))) if "permissions" in kwargs else None

        if kwargs.get("guild"):
            self.guild = kwargs["guild"]
        elif kwargs.get("guild_id"):
            self.guild: Guild = ClientUser.known_guilds.get(kwargs.get("guild_id"))
        else:
            self.guild = None


class User:
    """
    Generic user class
    """

    def __init__(self, **kwargs):
        """
        :key id: user id
        :key username: user's username
        :key global_name: global name
        :key bot: is user a bot
        """

        self.id: str = kwargs.get("id")
        self.username: str = kwargs.get("username")
        self.global_name: str | None = kwargs.get("global_name")
        self.bot: bool = kwargs.get("bot", False)


class Channel:
    """
    Channel class
    """

    def __init__(self, **kwargs):
        """
        :key id: channel id
        :key guild: guild id (if present)
        :key type: channel type
        :key name: channel name (if present)
        :key position: channel position (if present)
        :key permissions: channels permissions (if present)
        :key recipients: list of recipients (users)
        """

        self.id: str = kwargs.get("id")
        self.guild: Guild | None = ClientUser.get_guild(kwargs.get("guild_id"))
        self.type: ChannelType = ChannelType(kwargs.get("type"))
        self.name: str | None = kwargs.get("name")
        self.position: int = kwargs.get("position", 0)
        self.parent_id: str | None = kwargs.get("parent_id")
        self.permissions: Permissions | None = Permissions(
            int(kwargs.get("permissions"))) if "permissions" in kwargs else None
        self.recipients: list[User] = kwargs.get("recipients", list())

    @staticmethod
    def from_response(response: dict):
        """
        Make channel object from any response
        """

        recipients = [
            User(**x) for x in response.get("recipients", [])
        ]

        return Channel(
            id=response["id"],  # always present
            type=response["type"],  # always present
            name=response.get("name"),  # may be present, nullable
            position=response.get("position", 0),  # may be present
            parent_id=response.get("parent_id"),  # may be present, nullable
            permissions=response.get("permissions"),  # may be present
            recipients=recipients
        )


class Guild:
    """
    Guild class
    """

    def __init__(self, **kwargs):
        """
        :key id: guild id
        :key name: guild name
        :key description: guild's description (nullable)
        :key roles: guild's role list
        :key channels: list of guild's channels
        :key members: guild's members
        """

        self.id: str = kwargs.get("id")
        self.name: str = kwargs.get("name")
        self.description: str | None = kwargs.get("description")
        self.roles: list[Role] = kwargs.get("roles", list())
        self.channels: list[Channel] = kwargs.get("channels", list())
        self.members: list[Member] = kwargs.get("members", list())

        self._annoying_sort()

    def _annoying_sort(self):
        """
        Sorts the channels properly (keeping in mind GUILD_CATEGORY)
        """

        # tree of categories
        categories = []

        # append all categories
        for channel in self.channels:
            if channel.type == ChannelType.GUILD_CATEGORY:
                categories.append(
                    {
                        "category": channel,
                        "items": []})

        # append channels to categories
        for channel in self.channels:
            # skip category channels
            if channel.type == ChannelType.GUILD_CATEGORY:
                continue

            # if channels doesn't belong to any category
            if channel.parent_id is None:
                categories.append(channel)

            # if it does, find category and append
            else:
                for cat in categories:
                    if not isinstance(cat, dict):
                        continue
                    if cat["category"].id == channel.parent_id:
                        cat["items"].append(channel)
                        break

        # sort channels inside categories
        for cat in categories:
            # skip default channels
            if isinstance(cat, Channel):
                continue

            # sort channels inside category
            cat["items"].sort(key=lambda x: x.position)

        # sort everything
        categories.sort(key=lambda x: x.position if isinstance(x, Channel) else x["category"].position)

        # make new channel list and assign as a new one
        new_channels = []
        for cat in categories:
            # append channel
            if isinstance(cat, Channel):
                new_channels.append(cat)

            # append channels within a category
            else:
                new_channels.append(cat["category"])
                new_channels += cat["items"]
        self.channels = new_channels

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

    known_users: list[User] = []
    known_guilds: list[Guild] = []
    known_channels: list[Channel] = []
    private_channels: list[Channel] = []
    focus_channel: Channel | None = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @classmethod
    def get_user(cls, uid: str) -> User | None:
        """
        Returns a user by ID. None if that user doesn't exist
        """

        for user in cls.known_users:
            if user.id == uid:
                return user
        return None

    @classmethod
    def get_guild(cls, gid: str) -> Guild | None:
        """
        Returns a guild by ID. None if that guild doesn't exist
        """

        for guild in cls.known_guilds:
            if guild.id == gid:
                return guild
        return None


class Message:
    """
    Message class
    """

    def __init__(self, **kwargs):
        """
        :key id: message id
        :key channel: message channel
        :key author: message's author
        :key content: message's content
        :key type: message type
        :key timestamp: message creation time
        :key edited_timestamp: message edit time
        :key mention_everyone: @everyone
        :key mentions: list of user mentioned
        :key mention_roles: list of roles mentioned
        :key attachments: list of attachments
        """

        self.id: str = kwargs.get("id")
        self.channel: Channel | None = ClientUser.get_channel(kwargs.get("channel_id"))
        self.author: User | Member = kwargs.get("author")
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

    @staticmethod
    def from_create_event(event_data):
        """
        Makes message instance from MESSAGE_CREATE discord gateway event
        """

        # fetch some of the arguments
        message = Message(
            id=event_data["id"],
            channel_id=event_data["channel_id"],
            content=event_data["content"],
            type=event_data["type"],
            timestamp=event_data["timestamp"],
            mention_everyone=event_data["mention_everyone"])

        # check if author is already known
        if event_data["author"]["id"] in ClientUser.known_users:
            author = ClientUser.get_user(event_data["author"]["id"])

        # otherwise make new user
        else:
            author = User(
                id=event_data["author"]["id"],
                username=event_data["author"]["username"],
                global_name=event_data["author"]["global_name"],
                bot=event_data["author"].get("bot"))
            ClientUser.known_users.append(author)

        # if this is in a guild
        if event_data.get("member"):
            # fetch guild
            guild = ClientUser.get_guild(event_data["guild_id"])

            # fetch roles
            roles = []
            # go through all guild roles
            for role in guild.roles:
                # if that role is present => add to the list
                if role.id in event_data["member"]["roles"]:
                    roles.append(role)

            message.author = Member(
                user=author,
                guild=guild,
                nick=event_data["member"]["nick"],
                roles=roles)

        else:
            message.author = author

        return message

        # TODO: add mentions
        # TODO: add mention roles
        # TODO: add attachments
