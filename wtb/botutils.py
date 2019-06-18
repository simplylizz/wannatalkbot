"""
Common staff for bot interaction
"""

import os
import functools
import datetime

import telegram

from . import logconfig
from . import db

logger = logconfig.logger


TELEGRAM_API_TOKEN = os.environ["TELEGRAM_API_TOKEN"]


def get_updater():
    """
    Create the EventHandler and pass it your bot's token.
    """
    return telegram.ext.Updater(TELEGRAM_API_TOKEN)


def get_bot():
    return telegram.Bot(TELEGRAM_API_TOKEN)


def log_message(wrapped):
    @functools.wraps(wrapped)
    def wrapper(bot, update):
        try:
            return wrapped(bot, update)
        finally:
            try:
                message = update.message.to_dict()
                message["date"] = datetime.datetime.utcnow()
                db.get_messages_collection().insert_one(message)
            except Exception:
                logger.exception("Failed to log message:\n%s", update.message)

    return wrapper
