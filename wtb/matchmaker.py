"""
Find users, send requests to talk.

TODO: rewrite in a tinder-like maneer. E.g. you clicks "search", view
some profiles and say "yes" or "no" to them. The same makes other
peoples. If you'd matched than you'll receive each others direct
contacts.

So no separate matchmaker daemon would be required.
"""

import logging
import time
import datetime
import os

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from . import logconfig
from . import botutils
from . import db


WTB_DEVELOPMENT_MODE = os.getenv("WTB_DEVELOPMENT_MODE", False) == "1"
LOOP_SLEEP_SECS_INTERVAL = 300  # secs, 300... what are you thinking about? -_-


logger = logging.getLogger(__name__)


def run_one_loop():
    """
    Process *all* users once

    1. Find users without requests, send them one.
    2. Find users with requests: mark them stale if they are it is (nope X_X).
    """
    bot = botutils.get_bot()

    users = db.get_users_collection()
    matches = db.get_matches_collection()

    logger.info("Running one iteration")

    for user in users.find({
            # equality shouldn't be considered as valid state
            "$where": "this.language != this.search_language",
            "pause": {"$ne": True},
    } if not WTB_DEVELOPMENT_MODE else {}):
        logger.info("Processing user %s", user["_id"])

        to_exclude = [user["_id"]]
        sent_requests = user.get("sent_requests", [])
        if user.get("sent_requests", []):
            to_exclude.extend(user["sent_requests"])

        pair = users.find_one({
            "_id": {"$nin": to_exclude},
            "language": user["search_language"],
            "current_request": None,
            "pause": {"$ne": True},
        } if not WTB_DEVELOPMENT_MODE else {})
        if pair:
            # 1 - create match
            # 2 - send match info to pair
            # 3 - set pair.current_request to match
            # 4 - add pair to user.sent_requests to prevent overspamming

            now = datetime.datetime.utcnow()
            match_id = matches.insert_one({
                "user": user,
                "pair": pair,
                "created_at": now,
                "updated_at": now,
            }).inserted_id

            bot.send_message(
                pair["user_id"],
                (
                    "Incoming request!"
                    "\n\n"
                    "Someone want to talk with you. His native language is {} and he want to practice {}."
                    "\n\n"
                    "Are you ready to help? If yes, you are both will receive each other contacts."
                ).format(
                    user["language"],
                    user["search_language"],
                ),
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "Accept",
                                callback_data="accept_{}".format(match_id),
                            ),
                            InlineKeyboardButton(
                                "Decline",
                                callback_data="decline_{}".format(match_id),
                            ),
                        ],
                    ],
                    resize_keyboard=True,
                    one_time_keyboard=True,
                ),
            )

            db.update_wtb_user(pair, {"current_request": match_id})

            sent_requests.append(pair["_id"])

            db.update_wtb_user(
                user,
                {"sent_requests": sent_requests},
            )
        else:
            logger.info("No pair for lang %s", user["search_language"])


def main():
    while True:
        run_one_loop()
        time.sleep(LOOP_SLEEP_SECS_INTERVAL)
