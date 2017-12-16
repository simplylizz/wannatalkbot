"""
Language DB tools.

Works with the following standarts:
    * ISO 639-1 - 2-letter codes
    * ISO 639-2/B - 3-letter codes with eng names

TODO: add ISO 639-2/T support in gues_lang function with lowest priority?
"""

import logging
import os


logger = logging.getLogger(__name__)

_SHORT_LANGS = None
_LONG_LANGS = None


LANGS_PATH = os.path.join(
    os.path.abspath(__file__).rsplit(os.path.sep, 1)[0],
    "language-codes.csv",
)


def guess_lang(maybe_lang, full=False):
    """Returns short code for given *maybe lang* or None"""
    if len(maybe_lang) < 2:
        return None

    maybe_lang = maybe_lang.lower()

    short_langs = get_long_langs()

    if maybe_lang in short_langs:
        return short_langs[maybe_lang] if full else maybe_lang

    for key, value in short_langs.items():
        logger.debug("comparing %s vs %s", maybe_lang, value)
        if maybe_lang in value.lower():
            logger.debug("%s looks like %s", maybe_lang, value)
            return value if full else key

    return None


def get_long_langs():
    """
    Return the following dict:
        <short or long lang name in lower case>: <long lang name>
    """
    global _LONG_LANGS

    if _LONG_LANGS is None:
        langs = {}

        with open(LANGS_PATH) as in_:
            for line in in_:
                short_2, short_3, longs = line.split(',', 2)

                longs = longs.replace('"', '')
                main_long = longs.split(";", 1)[0].strip()

                langs[short_2] = langs[short_3] = main_long
                for long_ in longs.split(";"):
                    langs[long_.strip().lower()] = main_long

        _LONG_LANGS = langs

    return _LONG_LANGS


# to warm up cache or just fail early
get_long_langs()
