import re

from .constants import *
from datetime import datetime


class Role:
    """
    Role class
    """

    def __init__(self, **kwargs):
        self.id: str = kwargs.get("id")
        self.name: str = kwargs.get("name")
        self.color: int = kwargs.get("color")
        self.position: int = kwargs.get("position")
        self.permissions: str = kwargs.get("permissions")


class Member:
    """
    Member class
    """

    def __init__(self, **kwargs):
        self.user: User = kwargs.get("user")
        self.nick: str | None = kwargs.get("nick")
        self.roles: list[Role] = kwargs.get("roles", list())
        self.permissions: str | None = kwargs.get("permissions")


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
        self.permissions: str | None = kwargs.get("permissions")

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
