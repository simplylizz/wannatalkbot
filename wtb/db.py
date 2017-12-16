import datetime

import pymongo
import bson


_MONGO_CLIENT = None


def get_mongo_db():
    global _MONGO_CLIENT

    if _MONGO_CLIENT is None:
        _MONGO_CLIENT = pymongo.MongoClient("mongodb")

    return _MONGO_CLIENT.wannatalk


def get_users_collection():
    return get_mongo_db().users


def get_matches_collection():
    return get_mongo_db().matches


def count_language(lang):
    # TODO: filter only active/not hidden profiles
    return get_users_collection().count({"language": lang})


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

    return get_users_collection().find_one_and_update(
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


def get_match(match_id):
    return get_matches_collection().find_one(
        {"_id": bson.ObjectId(match_id)},
    )


def update_match(match, extra):
    to_set = extra.copy()
    to_set["updated_at"] = datetime.datetime.utcnow()

    get_matches_collection().find_one_and_update(
        {"_id": match["_id"]},
        {"$set": to_set},
    )
