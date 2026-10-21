from pymongo import MongoClient

from utils.core_utils import get_setting


class MongoConnection:
    _client = None

    def __init__(self, uri=None, db_name=None):
        self.uri = uri or get_setting(
            "database",
            "mongo_uri",
            "mongodb://localhost:27017",
            env_name="MONGO_URI",
        )
        self.db_name = db_name or get_setting(
            "database",
            "db_name",
            "negotiation",
            env_name="DB_NAME",
        )

    def get_client(self):
        if MongoConnection._client is None:
            MongoConnection._client = MongoClient(self.uri)
        return MongoConnection._client

    def get_db(self):
        return self.get_client()[self.db_name]
