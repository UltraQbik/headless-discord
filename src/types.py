import re

from .constants import *
from datetime import datetime


class Member:
    """
    Guild member class
    """

    def __init__(self, **kwargs):
        self.guild_id: str | None = kwargs.get("guild_id")
        self.nick: str | None = kwargs.get("nick")
        self.mute: bool | None = kwargs.get("mute")
        self.deaf: bool | None = kwargs.get("deaf")
        self.joined_at: datetime = datetime.fromisoformat(kwargs.get("joined_at")) if "joined_at" in kwargs else None
        self.roles: list[str] | None = kwargs.get("roles")


class User:
    """
    Broad user class
    """

    def __init__(self, **kwargs):
        # general data
        self.id: str | None = kwargs.get("id")
        self.username: str | None = kwargs.get("username")
        self.global_name: str | None = kwargs.get("global_name")

        # guild data
        self.member: Member | None = Member(**(kwargs["member"])) if "member" in kwargs else None

        # fix annoying nickname thing
        if self.member and self.member.nick is None:
            self.member.nick = self.username

    @property
    def nickname(self) -> str:
        """
        Returns user's guild name, if present, otherwise global_name, otherwise username
        """

        if self.member is not None:
            return self.member.nick
        elif self.global_name is not None:
            return self.global_name
        return self.username

    @staticmethod
    def from_response(response: dict):
        """
        Generates user instance from discord response
        :return: User
        """

        user = User(
            **(response["author"]),
            member=response.get("member", {}))
        if "guild_id" in response:
            user.member.guild_id = response["guild_id"]

        return user

    @staticmethod
    def from_response_mention(mention: dict):
        """
        Generates user instance from discord mention response
        :return: User
        """

        return User(**mention)


class Message:
    """
    Message class
    """

    def __init__(self, **kwargs):
        # general data
        self.id: str | None = kwargs.get("id")
        self.channel_id: str | None = kwargs.get("channel_id")
        self.timestamp: datetime | None = datetime.fromisoformat(
            kwargs.get("timestamp")) if "timestamp" in kwargs else None
        self.author: User | None = User.from_response(kwargs)
        self.mentions: list[User] = [User.from_response_mention(x) for x in kwargs["mentions"]]
        self.mention_everyone: bool = kwargs.get("mention_everyone", False)
        self.content: str = kwargs.get("content")

        # guild data
        self.guild_id: str | None = kwargs.get("guild_id")

    @staticmethod
    def from_response(response: dict):
        """
        Generates message instance from discord response
        :return: Message
        """

        return Message(**response)

    def format_for_user(self, user: User):
        """
        Cleans content for client (TEMP FIX)
        """

        # clean content up
        content_mentions = re.findall(r"<(.*?)>", self.content)
        for content_mention in content_mentions:
            if content_mention[:2] != "@&":
                for mention in self.mentions:
                    if content_mention[1:] == mention.id:
                        username = mention.member.nick if mention.member else mention.username

                        # if user mentioned is the client
                        if mention.id == user.id:
                            username = f"{PING_ME_HIGHLIGHT}@{username}{CS_RESET}"
                        else:
                            username = f"{PING_HIGHLIGHT}@{username}{CS_RESET}"

                        self.content = self.content.replace(f"<{content_mention}>", username)
                        break

        # when @everyone is pinged
        if self.mention_everyone:
            self.content = self.content.replace("@everyone", f"{PING_ME_HIGHLIGHT}@everyone{CS_RESET}")

        # when @everyone is pinged, but not really (aka user doesn't have permission to)
        else:
            self.content = self.content.replace("@everyone", f"{PING_HIGHLIGHT}@everyone{CS_RESET}")

        # when @here is pinged
        self.content = self.content.replace("@here", f"{PING_ME_HIGHLIGHT}@here{CS_RESET}")

    def __str__(self):
        timestamp = self.timestamp.strftime('%H:%M:%S')
        username = self.author.member.nick if self.guild_id else self.author.username
        return f"\33[90m[{timestamp}]\33[0m {username}> {self.content}"


class Channel:
    """
    Channel class
    """

    def __init__(self, **kwargs):
        self.id: str = kwargs.get("id")
        self.name: str = kwargs.get("name")
        self.nsfw: bool = kwargs.get("nsfw")
        self.position: int = kwargs.get("position")
        self.type: int = kwargs.get("type")


class Guild:
    """
    Guild class
    """

    def __init__(self, **kwargs):
        self.id: str = kwargs.get("id")
        self.name: str = kwargs.get("name")
        self.channels: list[Channel] = []
        self.member_count: int = kwargs.get("member_count")
        # TODO: add threads

        # append channels
        for channel in kwargs.get("channels", []):
            # skip any non-channel channels (categories are in channels for some reason)
            if channel["type"] == 4:
                continue
            self.channels.append(Channel(**channel))

        # sort them, because discord gives them in random order
        self.channels.sort(key=lambda x: x.position)

    @staticmethod
    def from_response(response):
        """
        Generates guild instance from discord response
        """

        return Guild(
            id=response["id"],
            name=response["properties"]["name"],
            channels=response["channels"],
            member_count=response["member_count"]
        )
