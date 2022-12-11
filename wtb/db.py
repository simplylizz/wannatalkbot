import datetime

import pymongo
import bson

from . import models

# TODO: add indices... someday.


_MONGO_CLIENT = None


def get_mongo_db():
    global _MONGO_CLIENT

    if _MONGO_CLIENT is None:
        _MONGO_CLIENT = pymongo.MongoClient("mongodb")

    return _MONGO_CLIENT.wannatalk


def get_users_collection():
    return get_mongo_db().users


def count_language(lang):
    return get_users_collection().count_documents({
        "pause": False,
        "language": lang,
    })


def update_wtb_user(user, extra):
    """
    Updates user with fresh info and additionally sets extra values
    """
    to_set = {}

    if isinstance(user, dict):
        def get_user_attr(name):
            return user.get(name)
    else:
        def get_user_attr(name):
            return getattr(user, name, None)

    for attr in ("first_name", "last_name", "username", "language_code"):
        value = get_user_attr(attr)
        if value:
            to_set[attr] = value

    try:
        user_id = user.id
    except AttributeError:
        user_id = user["user_id"]

    # could use $currentDate, but why?
    to_set["last_updated"] = datetime.datetime.utcnow()

    to_set.update(extra)

    result = get_users_collection().find_one_and_update(
        {"user_id": user_id},
        {
            "$set": to_set,
            "$setOnInsert": {
                "user_id": user_id,
                "created_at": to_set["last_updated"],
            },
        },
        upsert=True,
        new=True,
    )

    return models.User(**result)


def get_messages_collection():
    return get_mongo_db().messages


def get_user_from_telegram_obj(user):
    """get wanna talk bot user"""

    db_user = get_users_collection().find_one({"user_id": user.id})

    if db_user:
        return models.User(**db_user)

    return None


def get_pair(skip_users, language):
    pipeline = [
        {
            "$match": {
                "pause": False,
                "language": language,
                "user_id": {
                    "$nin": skip_users,
                },
            },
        },
        {"$sample": {"size": 1}},
    ]
    sample = list(get_users_collection().aggregate(pipeline))

    return sample[0] if sample else None


def get_user_count():
    return get_users_collection().count_documents()


def get_active_user_count():
    return get_users_collection().count_documents({"pause": {"$ne": True}})


def get_recent_user_count(days):
    return get_users_collection().count_documents(
        {"created_at": {"$gte": datetime.datetime.now() - datetime.timedelta(days=days)}},
    )


def get_top_wanted_languages(limit):
    return get_users_collection().aggregate([
        {"$match": {"search_language": {"$ne": None}}},
        {"$sortByCount": "$search_language"},
        {"$limit": limit},
    ])


def get_top_known_languages(limit):
    return get_users_collection().aggregate([
        {"$match": {"language": {"$ne": None}}},
        {"$sortByCount": "$language"},
        {"$limit": limit},
    ])


def get_top_language_pairs(limit):
    return get_users_collection().aggregate([
        {"$match": {"$and": [
            {"language": {"$ne": None}},
            {"search_language": {"$ne": None}},
        ]}},
        {"$project": {"langs": ["$search_language", "$language"]}},
        {"$unwind": "$langs"},
        {"$sort": {"langs": 1}},
        {"$group": {
            "_id": '$_id',
            "langs": {"$push": "$langs"},
        }},
        {"$sortByCount": "$langs"},
        {"$limit": limit},
    ])
