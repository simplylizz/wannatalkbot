import datetime
import dataclasses


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
    user_id: int
    last_updated: datetime.datetime
    created_at: datetime.datetime
    language: str
    search_language: str = dataclasses.field(default='')
    sent_requests: list[dict] = dataclasses.field(default_factory=lambda: [])

    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None

    pause: bool = dataclasses.field(default=False)

    def __getitem__(self, key):
        return getattr(self, key)

    def get(self, key, default=None):
        return getattr(self, key, default)
