"""
Common staff for bot interaction
"""

import os
import functools
import datetime
import typing as T

import telegram
import telegram.ext

from . import logconfig
from . import db

logger = logconfig.logger


TELEGRAM_API_TOKEN = os.environ["TELEGRAM_API_TOKEN"]


def get_application() -> telegram.ext.Application:
    """
    Initialize and return telegram application
    """
    return (
        telegram.ext.ApplicationBuilder()
        .token(TELEGRAM_API_TOKEN)
        .build()
    )


_HANDLER_RETURN_VAR = T.TypeVar("_HANDLER_RETURN_VAR")
_HANDLER_TYPE = T.Callable[
    [
        telegram.Update,
        telegram.ext.ContextTypes.DEFAULT_TYPE,
    ],
    _HANDLER_RETURN_VAR,
]


def log_message(wrapped: _HANDLER_TYPE) -> _HANDLER_TYPE:
    @functools.wraps(wrapped)
    def wrapper(
            update: telegram.Update,
            context: telegram.ext.ContextTypes.DEFAULT_TYPE,
    ) -> _HANDLER_RETURN_VAR:
        try:
            return wrapped(update, context)
        finally:
            try:
                message = update.message.to_dict()
                message["date"] = datetime.datetime.utcnow()
                db.get_messages_collection().insert_one(message)
            except Exception:
                logger.exception("Failed to log message:\n%s", update.message)

    return wrapper
