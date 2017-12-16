"""
Common staff for bot interaction
"""

import os

import telegram


TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]


def get_updater():
    """
    Create the EventHandler and pass it your bot's token.
    """
    return telegram.ext.Updater(TELEGRAM_TOKEN)


def get_bot():
    return telegram.Bot(TELEGRAM_TOKEN)
