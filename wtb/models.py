import datetime
import dataclasses
import typing

from . import db


@dataclasses.dataclass
class User:
    """
    username - telegram username
    user_id - telegram user id
    last_updated - utc datetime obj
    created_at - utc datetime obj
    current_request: None or <matches._id>
    sent_requests: [<users._id>]
    """

    _id: str
    first_name: str
    last_name: str
    username: str
    language_code: str
    user_id: str
    last_updated: datetime.datetime
    created_at: datetime.datetime

    language: str
    search_language: str
    current_request: typing.Optional[typing.List]
    sent_requests: typing.Optional[typing.List]

    @classmethod
    def get_user_from_telegram_obj(csl, user):
        """get wanna talk bot user"""
        db_user = db.get_users_collection().find_one({"user_id": user.id})

        if db_user:
            return cls(**db_user)

        return None


@dataclasses.dataclass
class Match:
    """
    user: <obj from users> - request to match from this user
    pair: <obj from users> - request to match to this user
    created_at: <datetime>
    updated_at: <datetime>
    state: "accepted" | "declined" | not set
    """

    _id: str
    user: str
    pair: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    state: str
