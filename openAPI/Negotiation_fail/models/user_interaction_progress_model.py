from ..models.user_interaction_log_model import (
    UserInteractionLogModel,
)
from utils.core_utils import get_setting
from utils.mongo_connection import MongoConnection


class UserInteractionProgressModel(UserInteractionLogModel):
    pass


class UserInteractionProgressRepository:

    def __init__(self, db=None):
        self.db = db or MongoConnection().get_db()
        self.collection = self.db[
            get_setting(
                "collections",
                "user_interaction_progress_log",
                "User_Interaction_Progress_Log",
            )
        ]

    def insert(self, document: dict):
        return self.collection.insert_one(document)
