from datetime import datetime
from typing import Any, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from utils.core_utils import get_setting
from utils.mongo_connection import MongoConnection


class UserInteractionStatusEntry(BaseModel):
    User_Interaction_Status: str
    created_dtm: datetime


class UserInteractionLogModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    doc_version: int = 1
    Interaction_Log_ID: int
    Interaction_ID: Optional[Union[int, str]] = None
    initiated_reference_id: Optional[Union[int, str]] = None
    User_Interaction_Type: str
    delegate_user_id: Optional[Union[int, str]] = None
    Created_By: str
    User_Interaction_Status: list[UserInteractionStatusEntry]
    parameters: dict[str, Any] = Field(default_factory=dict)
    Rejected_Reason: Optional[str] = None
    Rejected_By: Optional[str] = None
    created_dtm: datetime


class UserInteractionLogRepository:

    def __init__(self, db=None):
        self.db = db or MongoConnection().get_db()
        self.collection = self.db[
            get_setting(
                "collections",
                "user_interaction_log",
                "User_Interaction_Log",
            )
        ]

    def get_next_interaction_log_id(self) -> int:
        last_record = self.collection.find_one(
            sort=[("Interaction_Log_ID", -1)]
        )

        if not last_record:
            return 1

        return int(last_record.get("Interaction_Log_ID", 0)) + 1

    def insert(self, document: dict):
        return self.collection.insert_one(document)
