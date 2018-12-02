#!/usr/bin/env python

"""
Bot's facade. Part which is resposible for initial user conversation.
"""

import logging

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
from . import langsdb
from . import botutils


logger = logging.getLogger("wtb")


ACCEPT_COMMAND = "accept"
DECLINE_COMMAND = "decline"

# any unique (per converstaion handler) string
SET_NATIVE_LANGUAGE_STATE = "SET_NATIVE_LANGUAGE_STATE"
SEARCH_LANGUAGE_STATE = "SEARCH_LANGUAGE_STATE"


class TextCommands:
    SET_NATIVE_LANGUAGE = "Set native language"
    SEARCH_LANGUAGE = "Search language"


def get_wtb_user(user):
    """get wanna talk bot user"""
    return db.get_users_collection().find_one({"user_id": user.id})


def get_actions_keyboard(wtb_user):
    lang_key = "language"
    if wtb_user and wtb_user.get(lang_key):  # there is no users without set native lang
        lang = wtb_user[lang_key]

        search_lang_text = TextCommands.SEARCH_LANGUAGE
        if wtb_user.get("search_language"):
            search_lang = wtb_user["search_language"]
            search_lang_text = f"{search_lang_text} ({search_lang})"

        return ReplyKeyboardMarkup(
            [
                [f"{TextCommands.SET_NATIVE_LANGUAGE} ({lang})"],
                [search_lang_text],
            ],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
    else:
        return ReplyKeyboardMarkup(
            [[TextCommands.SET_NATIVE_LANGUAGE]],
            resize_keyboard=True,
            one_time_keyboard=True,
        )


def default_handler(bot, update):
    """
    Find user in DB.
    If it's missing ask him to enter his language.
    """
    user = update.message.from_user
    wtb_user = get_wtb_user(user)

    if wtb_user is None:
        update.message.reply_text(
            (
                "Hi! This is WannaTalkBot!"
                "\n\n"
                "Bot for those who want to practice foreign languages."
                " But it's a p2p service, so this means you should not "
                "only get help from other participants but also provide it."
                "\n\n"
                "P.S. This project is in early access stage so there is many "
                "missing features (like non-English interface, for example ;) ). "
                "I hope that some of them would appear soon, but "
                "despite on feature lack this service would be still useful."
            ),
            reply_markup=get_actions_keyboard(wtb_user),
        )
        return
    else:
        lang = wtb_user["language"]
        update.message.reply_text(
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


def set_native_language(bot, update):
    if update.message.text and not update.message.text.startswith(TextCommands.SET_NATIVE_LANGUAGE):
        lang = get_lang_from_udpate(update)

        if lang:
            wtb_user = db.update_wtb_user(update.message.from_user, {"language": lang})
            update.message.reply_text(
                f"Your native language is set to {lang}.",
                reply_markup=get_actions_keyboard(wtb_user),
            )
            return ConversationHandler.END
        else:
            update.message.reply_text(
                (
                    "Sorry, failed to recognize language. Maybe you'd misspelled it?"
                    "\n\n"
                    "Please, try to enter it again:"
                ),
                reply_markup=ReplyKeyboardRemove(),
            )
            return SET_NATIVE_LANGUAGE_STATE
    else:
        update.message.reply_text(
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


def search_language(bot, update):
    """
    Search users with specified language and send them request to talk
    """
    if not update.message.text or update.message.text.startswith(TextCommands.SEARCH_LANGUAGE):
        update.message.reply_text(
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
            db.update_wtb_user(
                update.message.from_user,
                {
                    "search_language": lang,
                    "pause": False,
                }
            )
            counter = db.count_language(lang)

            update.message.reply_text(
                (
                    "We would try to find someone who is ready to help you, just wait for it. "
                    "When it happen you'll get each other contacts."
                    "\n\n"
                    "Right now we have {language_counter}"
                    " users who specified {language} as their native language."
                    "\n\n"
                    "Also other people can send you requests to practice your native language."
                ).format(
                    language=lang,
                    language_counter=counter,
                ),
                reply_markup=ReplyKeyboardRemove(),
            )
            return ConversationHandler.END
        else:
            update.message.reply_text(
                (
                    "Sorry, failed to recognize language. Maybe you'd misspelled it?"
                    "\n\n"
                    "Please, try to enter it again:"
                ),
                reply_markup=ReplyKeyboardRemove(),
            )
            return SEARCH_LANGUAGE_STATE


def request_callback(bot, update):
    """
    if request accepted:
      1 - send contact info to vis-a-vis
      2 - update match state
      3 - remove incoming request
      4 - edit message with contact info
    if request declined:
      1 - pause incoming requests
      2 - update match state
      3 - remove incoming request
      4 - edit message with update that requests are paused and could
          be resumed through starting search
    """
    query = update.callback_query

    logger.info("Processing callback for data: %s", query.data)

    splitted = query.data.split("_", 1)
    if len(splitted) != 2:
        raise RuntimeError("unexpected query: %s" % query)

    command, args = splitted

    wtb_user = get_wtb_user(query.from_user)

    match = db.get_match(args)
    ################# FIXME: check only paired user
    if match["user"]["_id"] != wtb_user["_id"] or match["pair"]["_id"] != wtb_user["_id"]:
        logger.error(
            "User %s tried to change foreign match %s, looks suspicious",
            wtb_user["_id"],
            match["_id"],
        )
        raise RuntimeError("specified match isn't related to the given user")

    pair = match["pair"]

    if command == ACCEPT_COMMAND:
        bot.send_message(
            text=(
                "Good news! We'd found someone who is ready to talk with "
                "you: [{}](tg://user?id={}), write something in {}."
            ).format(
                get_user_display_name(wtb_user),
                wtb_user["user_id"],
                match["user"]["search_language"],
            ),
            parse_mode=telegram.ParseMode.MARKDOWN,
            chat_id=pair["user_id"],
        )

        db.update_match(match, {"state": "accepted"})
        db.update_wtb_user(wtb_user, {"incoming_request": None})

        bot.edit_message_text(
            text=(
                "Cool! Here is link to he/she: [{}](tg://user?id={}), write "
                "something in {}!"
            ).format(
                get_user_display_name(pair),
                pair["user_id"],
                # could differs from our current search_language, so
                # historical value from match
                pair["language"],
            ),
            parse_mode=telegram.ParseMode.MARKDOWN,
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
        )
    elif command == DECLINE_COMMAND:
        db.update_match(match, {"state": "declined"})
        db.update_wtb_user(wtb_user, {"incoming_request": None, "pause": True})

        bot.edit_message_text(
            text=(
                "Ok, request was declined."
                "\n\n"

                "We'd marked your account as paused "
                "to prevent you from being spammed with requests. If you want "
                "to continue search companions and receive requests just re-set "
                "your search language again."
            ),
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
        )
    else:
        raise RuntimeError("unexpected command in query: %s", query)


def get_user_display_name(wtb_user):
    if wtb_user.get("username"):
        return wtb_user["username"]
    else:
        return " ".join(wtb_user[f] for f in ("first_name", "last_name") if wtb_user.get(f))


def fallback_command(bot, update):
    logger.error("Catched fallback on update: %s", update)
    update.message.reply_text(
        "Something went wrong, can't recognize what you want."
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

    updater.dispatcher.add_handler(CallbackQueryHandler(request_callback))

    handler = MessageHandler(Filters.all, default_handler)
    updater.dispatcher.add_handler(handler)

    # log all errors
    updater.dispatcher.add_error_handler(log_error)

    # Start the Bot
    updater.start_polling(
        # TODO: if this will help to prevent timeouts, move values to
        # constants, either delete it
        poll_interval=5.0,
        timeout=120,
    )

    logger.info("Started")

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()
