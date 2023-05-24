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
from telegram.ext import filters
from telegram.ext import ContextTypes
from telegram.ext import MessageHandler
from telegram.ext import ConversationHandler

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
STATS = "/stats"


class TextCommands:
    SET_NATIVE_LANGUAGE = "Set native language"
    SEARCH_LANGUAGE = "Set search language"
    FIND = "Send request to chat with someone"
    STATS = "Show bot statistics"


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
    else:
        actions = [[TextCommands.SET_NATIVE_LANGUAGE]]

    actions.append([TextCommands.STATS])

    return ReplyKeyboardMarkup(
        actions,
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def get_wtb_user_from_update(update: telegram.Update) -> models.User | None:
    return db.get_user(update.message.from_user.id)


@botutils.log_message
async def default_handler(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Find user in DB.
    If it's missing ask him to enter his language.
    """
    wtb_user = get_wtb_user_from_update(update)

    if wtb_user is None:
        await update.message.reply_markdown(
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
                "You can get some bot usage stats with /stats command."
                "\n\n"
                "P.S. This project is in it's early stage, so there are not too "
                "much users and not too much features. Also some bugs are "
                "possible."
            ),
            reply_markup=get_actions_keyboard(wtb_user),
        )
        return

    lang = wtb_user.language
    await update.message.reply_markdown(
        (
            f"Your native language is currently set to {lang}."
            f"\n\n"
            # SEARCH MESSAGE
            f"You could change it or just set which language you are interested in."
        ),
        reply_markup=get_actions_keyboard(wtb_user),
    )


async def stats(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Print usage statistics.
    """
    wtb_user = get_wtb_user_from_update(update)

    await update.message.reply_markdown(
        (
            "Total users: {}\n"
            "Active users: {}\n"
            "New users within last 30 days: {}\n"
            "\n"
            "Top 5 searched languages:\n"
            "{}\n"
            "\n"
            "Top 5 known languages:\n"
            "{}\n"
            "\n"
            "Top 5 most popular language pairs:\n"
            "{}\n"
        ).format(
            db.get_user_count(),
            db.get_active_user_count(),
            db.get_recent_user_count(30),
            "\n".join(f"{i['_id']}: {i['count']}" for i in db.get_top_wanted_languages(5)),
            "\n".join(f"{i['_id']}: {i['count']}" for i in db.get_top_known_languages(5)),
            "\n".join(', '.join(i['_id']) + ': ' + str(i['count']) for i in db.get_top_language_pairs(5)),
        ),
        reply_markup=get_actions_keyboard(wtb_user),
    )


def get_lang_from_udpate(update):
    return langsdb.guess_lang(update.message.text.strip(), full=True)


@botutils.log_message
async def set_native_language(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE) -> int | str:
    if update.message.text and not update.message.text.startswith(TextCommands.SET_NATIVE_LANGUAGE):
        lang = get_lang_from_udpate(update)

        if lang:
            wtb_user = db.update_wtb_user(update.message.from_user, {"language": lang})
            await update.message.reply_markdown(
                f"Your native language is set to {lang}.",
                reply_markup=get_actions_keyboard(wtb_user),
            )
            return ConversationHandler.END
        else:
            await update.message.reply_markdown(
                (
                    "Sorry, failed to recognize language. Maybe you'd misspelled it?"
                    "\n\n"
                    "Please, try to enter your native language again."
                ),
                reply_markup=ReplyKeyboardRemove(),
            )
            return SET_NATIVE_LANGUAGE_STATE

    await update.message.reply_markdown(
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
async def search_language(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE) -> int | str:
    """
    Search users with specified language and send them request to talk
    """
    if not update.message.text or update.message.text.startswith(TextCommands.SEARCH_LANGUAGE):
        await update.message.reply_markdown(
            (
                "Specify language which you want to practice (in English, 2 or 3 "
                "letters or full name):"
            ),
            reply_markup=ReplyKeyboardRemove(),
        )
        return SEARCH_LANGUAGE_STATE

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

        await update.message.reply_markdown(
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

    await update.message.reply_markdown(
        (
            "Sorry, failed to recognize language. Maybe you'd misspelled it?"
            "\n\n"
            "Please, try to enter language which you wish to practice again."
        ),
        reply_markup=ReplyKeyboardRemove(),
    )
    return SEARCH_LANGUAGE_STATE


@botutils.log_message
async def find_pair(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Find user to practice language with.

    TODO: limit requests frequency rate
    """

    wtb_user = get_wtb_user_from_update(update)

    # should be rather a telemetry event, but we don't have telemetry events :)
    logger.info(
        "User %s is trying to pair: %s -> %s",
        wtb_user.user_id,
        wtb_user.language,
        wtb_user.search_language,
    )

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
            await update.message.reply_markdown(
                (
                    "Unfortunately we can't find anyone right now. Please, "
                    "try later."
                ),
                reply_markup=get_actions_keyboard(wtb_user),
            )
            break

        try:
            # NOTE: tagging a user could not work depending on user's privacy settings
            await context.bot.send_message(
                text=(
                    r"Hey\! Someone needs your help\. Just drop a message to "
                    r"[{name}](tg://user?id={user_id}) in {language} when it's "
                    r"convenient to you, but please, don't make them wait too "
                    r"long\."
                ).format(
                    name=get_user_display_name(wtb_user),
                    user_id=wtb_user.user_id,
                    language=wtb_user.search_language,
                ),
                parse_mode=telegram.constants.ParseMode.MARKDOWN_V2,
                chat_id=pair["user_id"],
            )
        except telegram.error.Forbidden:  # bot is blocked by user
            db.update_wtb_user(pair, {"pause": True})
            continue

        # FIXME: overriding whole list of requests is inefficient
        sent_requests = wtb_user.sent_requests
        sent_requests.append({
            "user_id": pair["user_id"],
            "language": wtb_user.search_language,
            "created_at": datetime.datetime.utcnow(),
        })
        db.update_wtb_user(wtb_user, {"sent_requests": sent_requests})

        await update.message.reply_markdown(
            (
                "We have found someone and sent your contacts. Just wait "
                "for \\*hello\\* from this user."
                "\n\n"
                "You could also send more requests."
            ),
            reply_markup=get_actions_keyboard(wtb_user),
        )

        logger.info("%s sent request to %s", wtb_user.user_id, pair["user_id"])

        break


def get_user_display_name(wtb_user: models.User) -> str:
    if wtb_user.get("username"):
        name = wtb_user.username
    else:
        name = " ".join(
            wtb_user[f] for f in ("first_name", "last_name") if wtb_user.get(f))

    return name.strip() or "no_name"


@botutils.log_message
async def fallback_command(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Caught fallback on update: %s", update)
    await update.message.reply_markdown(
        "Something went wrong, can't handle your request."
    )


async def log_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log Errors caused by Updates"""
    logger.error('Update "%s" caused error "%s"', update, context.error, exc_info=True)


def main() -> None:
    logger.info("Starting WannaTalkBot...")

    app = botutils.get_application()

    handler = ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Regex(rf"^{TextCommands.SET_NATIVE_LANGUAGE}.*"),
                set_native_language,
            ),
        ],
        states={
            # state key doesn't matter, there is only one state
            SET_NATIVE_LANGUAGE_STATE: [
                MessageHandler(filters.TEXT, set_native_language),
            ],
        },

        fallbacks=[
            MessageHandler(filters.ALL, fallback_command),
        ],
    )
    app.add_handler(handler)

    handler = ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Regex(rf"^{TextCommands.SEARCH_LANGUAGE}.*"),
                search_language,
            ),
        ],
        states={
            # state key doesn't matter, there is only one state
            SEARCH_LANGUAGE_STATE: [
                MessageHandler(filters.TEXT, search_language),
            ],
        },

        fallbacks=[
            MessageHandler(filters.ALL, fallback_command),
        ],
    )
    app.add_handler(handler)

    handler = ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Regex(rf"^{TextCommands.FIND}.*"),
                find_pair,
            ),
        ],
        states={
            # state key doesn't matter, there is only one state
            FIND_STATE: [
                MessageHandler(filters.TEXT, find_pair),
            ],
        },

        fallbacks=[
            MessageHandler(filters.ALL, fallback_command),
        ],
    )
    app.add_handler(handler)

    handler = MessageHandler(
        filters.Text([STATS]),
        stats,
    )
    app.add_handler(handler)

    handler = MessageHandler(
        filters.Text([TextCommands.STATS]),
        stats,
    )
    app.add_handler(handler)

    handler = MessageHandler(filters.ALL, default_handler)
    app.add_handler(handler)

    # log all errors
    app.add_error_handler(log_error)

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    app.run_polling()
