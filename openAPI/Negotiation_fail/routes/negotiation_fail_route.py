from fastapi import APIRouter

from ..controllers.negotiation_fail_controller import (
    NegotiationFailController,
)
from ..models.case_details_model import (
    NegotiationFailRequest,
    NegotiationFailResponse,
)
from utils.core_utils import get_setting


router = APIRouter()
controller = NegotiationFailController()


@router.post(
    get_setting("app", "route", "/negotiation-fail"),
    response_model=NegotiationFailResponse,
)
async def process_negotiation_fail(request: NegotiationFailRequest):
    return await controller.process_negotiation_fail(request)
