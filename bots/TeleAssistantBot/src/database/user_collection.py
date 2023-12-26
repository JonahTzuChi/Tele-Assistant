import config as cfg
from . import mongoDB

from typing import Optional, Any, final
from datetime import datetime


class UserCollection:
    collection = mongoDB["user"]

    @classmethod
    def exists(cls, user_id: int) -> bool:
        return cls.collection.count_documents({"telegram_id": user_id}) > 0

    @classmethod
    def create(cls, params: dict):
        expectedKeys = [
            "telegram_id",
            "chat_id",
            "username",
            "assistant_id",
            "assistant_name",
            "thread_id"
        ]
        assert all(key in params.keys() for key in expectedKeys)

        if cls.exists(params["telegram_id"]):
            return None

        dtnow = str(datetime.now()).split(".")[0]
        user = {
            "telegram_id": params["telegram_id"],
            "chat_id": params["chat_id"],
            "username": params["username"],
            "last_interaction": dtnow,
            "first_interaction": dtnow,
            "current_assistant": {
                "id": params["assistant_id"],
                "name": params["assistant_name"],
            },
            "current_thread_id": params["thread_id"],
            "current_file_ids": []
        }

        cls.collection.insert_one(user)

    @classmethod
    def get(cls, user_id: int):
        user = cls.collection.find_one({"telegram_id": user_id})
        return user

    @classmethod
    def get_attribute(cls, user_id: int, colkey: str) -> Any:
        assert cls.exists(user_id), f"{user_id} not found"
        user = cls.collection.find_one({"telegram_id": user_id})
        if colkey not in user:
            return None
        return user[colkey]

    @classmethod
    def update_attribute(cls, user_id: int, colkey: str, value: Any):
        assert cls.exists(user_id), f"{user_id} not found"
        cls.collection.update_one({"telegram_id": user_id}, {"$set": {colkey: value}})

    @classmethod
    def tick(cls, user_id: int):
        assert cls.exists(user_id), f"{user_id} not found"
        cls.update_attribute(user_id, "last_interaction", str(datetime.now()).split(".")[0])