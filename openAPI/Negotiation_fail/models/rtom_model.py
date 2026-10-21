# import re
# from typing import Optional

# from pydantic import BaseModel, ConfigDict

# from utils.core_utils import get_setting
# from utils.mongo_connection import MongoConnection


# class RTOMModel(BaseModel):
#     model_config = ConfigDict(extra="allow")

#     rtom_name: Optional[str] = None
#     metro_region: Optional[str] = None


# class RTOMRepository:

#     def __init__(self, db=None):
#         self.db = db or MongoConnection().get_db()
#         self.collection = self.db[
#             get_setting("collections", "rtom", "rtom")
#         ]

#     def find_by_rtom_name(self, rtom_name: str):

#         if not rtom_name:
#             return None

#         rtom_name = rtom_name.strip().upper()

#         return self.collection.find_one(
#             {
#                 "rtom_name": {
#                     "$regex": f"^{re.escape(rtom_name)}$",
#                     "$options": "i",
#                 }
#             }
#         )




import re
from typing import Optional

from pydantic import BaseModel, ConfigDict

from utils.mongo_connection import MongoConnection


class RTOMModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    rtom_name: Optional[str] = None
    metro_region: Optional[str] = None


class RTOMRepository:

    def __init__(self, db=None):
        self.db = db or MongoConnection().get_db()
        self.collection = self.db["rtom"]

    def find_by_rtom_name(self, rtom_name: str):

        if not rtom_name:
            return None

        rtom_name = rtom_name.strip().upper()

        return self.collection.find_one(
            {
                "rtom_name": {
                    "$regex": f"^{re.escape(rtom_name)}$",
                    "$options": "i",
                }
            }
        )