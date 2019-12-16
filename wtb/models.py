import datetime
import dataclasses
import typing


@dataclasses.dataclass
class User:
    """
    username - telegram username
    user_id - telegram user id
    last_updated - utc datetime obj
    created_at - utc datetime obj
    sent_requests: [<users._id>]
    """

    _id: str
    user_id: str
    last_updated: datetime.datetime
    created_at: datetime.datetime
    language: str
    search_language: str = dataclasses.field(default='')
    sent_requests: typing.List = dataclasses.field(default_factory=lambda: [])

    first_name: typing.Optional[str] = None
    last_name: typing.Optional[str] = None
    username: typing.Optional[str] = None
    language_code: typing.Optional[str] = None

    pause: bool = dataclasses.field(default=False)

    def __getitem__(self, key):
        return getattr(self, key)

    def get(self, key, default=None):
        return getattr(self, key, default)
