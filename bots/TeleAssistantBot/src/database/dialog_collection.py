import config as cfg
from . import mongoDB

from typing import Optional, Any, final
from datetime import datetime

class DialogCollection:
    collection = mongoDB["dialog"]

    @classmethod
    def exists(cls, thread_id: str) -> bool:
        return cls.collection.count_documents({"thread_id": thread_id}) > 0

    @classmethod
    def add(cls, thread_id: str, message: dict):
        if cls.exists(thread_id):
            cls.collection.update_one(
                {"thread_id": thread_id}, {"$push": {"messages": {"message": message}}}
            )
        else:
            dialog = {"thread_id": thread_id, "messages": [{"message": message}]}
            cls.collection.insert_one(dialog)
    
    @classmethod
    def get(cls, thread_id: str) -> list:
        if not cls.exists(thread_id):
            return []
        cursor = cls.collection.find_one({"thread_id": thread_id})
        messages = cursor['messages']
        
        return [] if messages is None else messages