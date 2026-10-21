from fastapi.responses import JSONResponse

from ..models.case_details_model import NegotiationFailRequest
from ..services.negotiation_fail_service import (
    CaseNotFoundError,
    NegotiationFailService,
    NegotiationFailValidationError,
)
from utils.logger import logger


class NegotiationFailController:
    def __init__(self, service=None):
        self.service = service or NegotiationFailService()

    async def process_negotiation_fail(
        self,
        request: NegotiationFailRequest,
    ):
        try:
            result = self.service.process(request.Case_Id)
        except NegotiationFailValidationError as exc:
            logger.warning("Negotiation fail validation failed: %s", exc)
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": str(exc),
                },
            )
        except CaseNotFoundError as exc:
            logger.warning("Negotiation fail case lookup failed: %s", exc)
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": str(exc),
                },
            )
        except Exception as exc:
            logger.exception("Negotiation fail process failed")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "Unexpected exception",
                },
            )

        return result
