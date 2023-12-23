__all__ = ['user_collection', 'dialog_collection', 'assistant_collection']

import config as cfg
import pymongo

mongoClient = pymongo.MongoClient(cfg.mongodb_uri)
mongoDB = mongoClient['tele-assistant']