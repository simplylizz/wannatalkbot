#!/usr/bin/env python

"""
Bot's facade. Part which is responsible for initial user conversation.
"""

import typing
import datetime

import telegram
from telegram import (
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    MessageHandler,
    Filters,
    RegexHandler,
    ConversationHandler,
    CallbackQueryHandler,
)

from . import logconfig
from . import db
from . import models
from . import langsdb
from . import botutils


logger = logconfig.logger

ADMIN_USER_ID = 167820551
PAIR_ATTEMPTS = 5

# any unique (per conversation handler) string
SET_NATIVE_LANGUAGE_STATE = "SET_NATIVE_LANGUAGE_STATE"
SEARCH_LANGUAGE_STATE = "SEARCH_LANGUAGE_STATE"
FIND_STATE = "FIND"


class TextCommands:
    SET_NATIVE_LANGUAGE = "Set native language"
    SEARCH_LANGUAGE = "Set search language"
    FIND = "Send request to chat with someone"


def get_actions_keyboard(wtb_user: typing.Optional[models.User]):
    if wtb_user:  # there is no users without set native lang
        lang = wtb_user.language

        actions = [
            [f"{TextCommands.SET_NATIVE_LANGUAGE} (current: {lang})"],
        ]

        if wtb_user.search_language:
            search_lang = wtb_user.search_language
            actions.append([f"{TextCommands.SEARCH_LANGUAGE} (current: {search_lang})"])
            actions.append([TextCommands.FIND])
        else:
            actions.append([TextCommands.SEARCH_LANGUAGE])

        return ReplyKeyboardMarkup(
            actions,
            resize_keyboard=True,
            one_time_keyboard=True,
        )
    else:
        return ReplyKeyboardMarkup(
            [[TextCommands.SET_NATIVE_LANGUAGE]],
            resize_keyboard=True,
            one_time_keyboard=True,
        )


def get_wtb_user_from_update(update) -> models.User:
    return db.get_user_from_telegram_obj(update.message.from_user)


@botutils.log_message
def default_handler(bot, update):
    """
    Find user in DB.
    If it's missing ask him to enter his language.
    """
    wtb_user = get_wtb_user_from_update(update)

    if wtb_user is None:
        update.message.reply_markdown(
            (
                "Hello, this is WannaTalkBot!"
                "\n\n"
                "Bot for those who want to practice foreign languages."
                " It's a p2p service, so this means you should not "
                "only receive help from other participants but also provide it."
                "\n\n"
                "If you want to send your feedback or just say **hi**, "
                f"don't hesitate to [tg me](tg://user?id={ADMIN_USER_ID})."
                "\n\n"
                "P.S. This project is in it's early stage, so there are not too "
                "much users and not too much features. Also some bugs are "
                "possible."
            ),
            reply_markup=get_actions_keyboard(wtb_user),
        )
        return
    else:
        lang = wtb_user.language
        update.message.reply_markdown(
            (
                f"Your native language is currently set to {lang}."
                f"\n\n"
                # SEARCH MESSAGE
                f"You could change it or just set which language you are interested in."
            ),
            reply_markup=get_actions_keyboard(wtb_user),
        )
        return


def get_lang_from_udpate(update):
    return langsdb.guess_lang(update.message.text.strip(), full=True)


@botutils.log_message
def set_native_language(bot, update):
    if update.message.text and not update.message.text.startswith(TextCommands.SET_NATIVE_LANGUAGE):
        lang = get_lang_from_udpate(update)

        if lang:
            wtb_user = db.update_wtb_user(update.message.from_user, {"language": lang})
            update.message.reply_markdown(
                f"Your native language is set to {lang}.",
                reply_markup=get_actions_keyboard(wtb_user),
            )
            return ConversationHandler.END
        else:
            update.message.reply_markdown(
                (
                    "Sorry, failed to recognize language. Maybe you'd misspelled it?"
                    "\n\n"
                    "Please, try to enter your native language again."
                ),
                reply_markup=ReplyKeyboardRemove(),
            )
            return SET_NATIVE_LANGUAGE_STATE
    else:
        update.message.reply_markdown(
            (
                "Specify your native language. People who "
                "want to practice it would be able to send you requests to talk."
                "\n\n"
                "Please enter language name in english: 2 or 3 letters or full name."
                "\n\n"
                "For example: en, eng or English, ru, rus or Russian, etc."
            ),
            reply_markup=ReplyKeyboardRemove(),
        )
        return SET_NATIVE_LANGUAGE_STATE


@botutils.log_message
def search_language(bot, update):
    """
    Search users with specified language and send them request to talk
    """
    if not update.message.text or update.message.text.startswith(TextCommands.SEARCH_LANGUAGE):
        update.message.reply_markdown(
            (
                "Specify language which you want to practice (in English, 2 or 3 "
                "letters or full name):"
            ),
            reply_markup=ReplyKeyboardRemove(),
        )
        return SEARCH_LANGUAGE_STATE
    else:
        lang = get_lang_from_udpate(update)
        if lang:
            wtb_user = db.update_wtb_user(
                update.message.from_user,
                {
                    "search_language": lang,
                    "pause": False,
                }
            )
            counter = db.count_language(lang)

            update.message.reply_markdown(
                (
                    "Right now we have {language_counter}"
                    " active users who specified {language} as their native "
                    "language."
                    "\n\n"
                    "You could search them through this bot and send request "
                    "to talk. Your contacts would be exposed to them."
                    "\n\n"
                    "Also other people can send you requests to practice your"
                    " native language."
                ).format(
                    language=lang,
                    language_counter=counter,
                ),
                reply_markup=get_actions_keyboard(wtb_user),
            )
            return ConversationHandler.END
        else:
            update.message.reply_markdown(
                (
                    "Sorry, failed to recognize language. Maybe you'd misspelled it?"
                    "\n\n"
                    "Please, try to enter language which you wish to practice again."
                ),
                reply_markup=ReplyKeyboardRemove(),
            )
            return SEARCH_LANGUAGE_STATE


@botutils.log_message
def find_pair(bot, update):
    """
    Find user to practice language with.

    TODO: limit requests frequency rate
    """

    wtb_user = get_wtb_user_from_update(update)

    skip_users = [wtb_user.user_id]
    skip_users.extend(
        r["user_id"]
        for r in wtb_user.sent_requests
        if r["language"] == wtb_user.search_language
    )

    attempts = PAIR_ATTEMPTS
    while attempts > 0:
        attempts -= 1

        pair = db.get_pair(skip_users, wtb_user.search_language)

        if not pair:
            update.message.reply_markdown(
                (
                    "Unfortunately we can't find anyone right now. Please, "
                    "try later."
                ),
                reply_markup=get_actions_keyboard(wtb_user),
            )
            break

        try:
            bot.send_message(
                text=(
                    "Hey! Someone needs your help. Just drop a message to "
                    "[{name}](tg://user?id={user_id}) in {language} when it's "
                    "convenient to you, but please, don't make him/her wait too "
                    "long."
                ).format(
                    name=get_user_display_name(wtb_user),
                    user_id=wtb_user["user_id"],
                    language=wtb_user.search_language,
                ),
                parse_mode=telegram.ParseMode.MARKDOWN,
                chat_id=pair["user_id"],
            )
        except telegram.error.Unauthorized:  # bot is blocked by user
            db.update_wtb_user(pair, {"pause": True})
            continue

        # FIXME: overriding whole list of requests is inneficient
        sent_requests = wtb_user.sent_requests
        sent_requests.append({
            "user_id": pair["user_id"],
            "language": wtb_user.search_language,
            "created_at": datetime.datetime.utcnow(),
        })
        db.update_wtb_user(wtb_user, {"sent_requests": sent_requests})

        update.message.reply_markdown(
            (
                "We have found someone and sent your contacts. Just wait "
                "for \\*hello\\* from this user."
                "\n\n"
                "You could also send more requests."
            ),
            reply_markup=get_actions_keyboard(wtb_user),
        )

        break


def get_user_display_name(wtb_user):
    if wtb_user.get("username"):
        return wtb_user["username"]
    else:
        return " ".join(wtb_user[f] for f in ("first_name", "last_name") if wtb_user.get(f))


@botutils.log_message
def fallback_command(bot, update):
    logger.error("Catched fallback on update: %s", update)
    update.message.reply_markdown(
        "Something went wrong, can't handle your request."
    )


def log_error(bot, update, error):
    """Log Errors caused by Updates"""
    logger.error('Update "%s" caused error "%s"', update, error, exc_info=True)


def main():
    logger.info("Starting WannaTalkBot...")

    updater = botutils.get_updater()

    handler = ConversationHandler(
        entry_points=[
            RegexHandler(
                rf"^{TextCommands.SET_NATIVE_LANGUAGE}.*",
                set_native_language,
            ),
        ],
        states={
            # state key doesn't matter, there is only one state
            SET_NATIVE_LANGUAGE_STATE: [
                MessageHandler(Filters.text, set_native_language),
            ],
        },

        fallbacks=[
            MessageHandler(Filters.all, fallback_command),
        ],
    )
    updater.dispatcher.add_handler(handler)

    handler = ConversationHandler(
        entry_points=[
            RegexHandler(
                rf"^{TextCommands.SEARCH_LANGUAGE}.*",
                search_language,
            ),
        ],
        states={
            # state key doesn't matter, there is only one state
            SEARCH_LANGUAGE_STATE: [
                MessageHandler(Filters.text, search_language),
            ],
        },

        fallbacks=[
            MessageHandler(Filters.all, fallback_command),
        ],
    )
    updater.dispatcher.add_handler(handler)

    handler = ConversationHandler(
        entry_points=[
            RegexHandler(
                rf"^{TextCommands.FIND}.*",
                find_pair,
            ),
        ],
        states={
            # state key doesn't matter, there is only one state
            FIND_STATE: [
                MessageHandler(Filters.text, find_pair),
            ],
        },

        fallbacks=[
            MessageHandler(Filters.all, fallback_command),
        ],
    )
    updater.dispatcher.add_handler(handler)

    handler = MessageHandler(Filters.all, default_handler)
    updater.dispatcher.add_handler(handler)

    # log all errors
    updater.dispatcher.add_error_handler(log_error)

    # Start the Bot
    updater.start_polling()

    logger.info("Started")

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()
