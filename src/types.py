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
        pass


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
            id=response["id"],
            name=response["name"],
            description=response["description"],
            roles=roles
        )
