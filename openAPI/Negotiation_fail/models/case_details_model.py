from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, StrictInt

from utils.core_utils import get_setting
from utils.mongo_connection import MongoConnection
from utils.timezone import get_local_now


class NegotiationFailRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    Case_Id: StrictInt = Field(..., gt=0)


class NegotiationFailResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict[str, Any]] = None


class CaseDetailsModel(BaseModel):
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    case_id: Optional[int] = None
    case_current_phase: Optional[str] = None
    case_current_status: Optional[str] = None
    current_arrears_amount: Optional[float] = None
    rtom: Optional[str] = None
    drc: list[dict[str, Any]] = Field(default_factory=list)


class CaseDetailsRepository:

    # def __init__(self, db=None):
    #     self.db = db or MongoConnection().get_db()
    #     self.collection = self.db[
    #         get_setting("collections", "Case_details", "Case_details")
    #     ]
    
    
    def __init__(self, db=None):
        self.db = db or MongoConnection().get_db()
        self.collection = self.db["Case_details"]
    
    
    
    

    # def find_by_case_id(self, case_id: int):
    #     return self.collection.find_one({"case_id": case_id})
    
    
    def find_by_case_id(self, case_id: int):
        return self.collection.find_one(
            {"case_id": case_id}
        )
    
    
    

    def update_status_and_phase(
        self,
        case_id: int,
        status: str,
        phase: str,
        reason: str,
    ):
        status_record = {
            "case_phase": phase,
            "case_status": status,
            "status_reason": reason,
            "created_dtm": get_local_now(),
            "created_by": "mediation_board_service",
            "notified_dtm": None,
            "expire_dtm": None,
        }

        return self.collection.update_one(
            {"case_id": case_id},
            {
                "$set": {
                    "case_current_status": status,
                    "case_current_phase": phase,
                },
                "$push": {
                    "case_status": status_record,
                },
            },
        )

    def update_lod_final_reminder(
        self,
        case_id: int,
        document_type: str,
        remark: str,
    ):
        case = self.find_by_case_id(case_id)

        if not case:
            return None

        lod_data = case.get("lod_final_reminder") or {}
        document_history = lod_data.get("document_type") or []

        document_record = {
            "document_seq": len(document_history) + 1,
            "document_type": document_type,
            "change_by": "system",
            "changed_dtm": get_local_now(),
            "changed_type_remark": remark,
        }

        return self.collection.update_one(
            {"case_id": case_id},
            {
                "$set": {
                    "lod_final_reminder.current_document_type": document_type,
                },
                "$push": {
                    "lod_final_reminder.document_type": document_record,
                },
            },
        )
