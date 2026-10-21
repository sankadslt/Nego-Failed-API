from copy import deepcopy
from datetime import date, datetime
from typing import Any, Optional

from ..models.case_details_model import (
    CaseDetailsRepository,
)
from ..models.rtom_model import (
    RTOMRepository,
)
from ..models.user_interaction_log_model import (
    UserInteractionLogModel,
    UserInteractionLogRepository,
    UserInteractionStatusEntry,
)
from ..models.user_interaction_progress_model import (
    UserInteractionProgressRepository,
)
from utils.constants import (
    CASE_PHASE_NEGOTIATION,
    CASE_STATUS_RO_NEGOTIATION,
    CREATED_BY,
    FINAL_REMINDER_CREDIT_CASES,
    FINAL_REMINDER_CUSTOMER_TYPES,
    FINAL_REMINDER_MANAGER_CODES,
    INTERACTION_TYPE_MEDIATION_BOARD,
    METRO,
    PHASE_F2,
    PHASE_F3,
    PHASE_LETTER_OF_DEMAND,
    REASON_FAILED_DRC,
    REASON_FTL_LOD,
    REGION,
    STATUS_PENDING_FTL_LOD,
    STATUS_PENDING_LOD,
    USER_INTERACTION_PENDING,
)
from utils.logger import logger
from utils.timezone import get_local_now


class NegotiationFailValidationError(Exception):
    pass


class CaseNotFoundError(Exception):
    pass


class NegotiationFailService:

    def __init__(
        self,
        case_repository=None,
        rtom_repository=None,
        interaction_log_repository=None,
        interaction_progress_repository=None,
    ):
        self.case_repository = case_repository or CaseDetailsRepository()
        self.rtom_repository = rtom_repository or RTOMRepository()
        self.interaction_log_repository = (
            interaction_log_repository or UserInteractionLogRepository()
        )
        self.interaction_progress_repository = (
            interaction_progress_repository or UserInteractionProgressRepository()
        )

    def process(self, case_id: int) -> dict[str, Any]:

        logger.info(
            "Processing negotiation fail flow for case_id: %s",
            case_id,
        )

        self.validate_request(case_id)

        case = self.find_case(case_id)

        current_phase = case.get("case_current_phase")
        current_status = case.get("case_current_status")

        logger.info("Current Phase: %s", current_phase)
        logger.info("Current Status: %s", current_status)

        # DRC validity period expire wela nathnam kisima update/insert ekak karanne na.
        if not self.is_drc_expired(case):
            logger.info(
                "Case %s skipped. DRC validity period has not expired.",
                case_id,
            )

            return {
                "success": True,
                "message": "DRC validity period has not expired. No action taken.",
                "data": {
                    "Case_Id": case_id,
                    "case_current_status": current_status,
                    "case_current_phase": current_phase,
                    "reason": "DRC validity period has not expired.",
                    "interaction_created": False,
                },
            }

        self.validate_negotiation_conditions(case)

        result = self.process_arrears_logic(case)

        logger.info(
            "Negotiation fail API completed. Case_Id=%s",
            case_id,
        )

        return result

    def validate_request(self, case_id: int):

        if type(case_id) is not int:
            logger.warning("Invalid Case_Id received: %s", case_id)
            raise NegotiationFailValidationError(
                "Invalid request: Case_Id is mandatory and must be an integer"
            )

    def find_case(self, case_id: int) -> dict[str, Any]:

        logger.info(
            "Looking up case_details document. Case_Id=%s",
            case_id,
        )

        case = self.case_repository.find_by_case_id(case_id)

        if not case:
            logger.warning("Case not found. Case_Id=%s", case_id)
            raise CaseNotFoundError("Case not found")

        return case

    def validate_negotiation_conditions(self, case: dict[str, Any]):

        case_id = case.get("case_id")
        current_status = case.get("case_current_status")
        current_phase = case.get("case_current_phase")

        if (
            current_phase != CASE_PHASE_NEGOTIATION
            or current_status != CASE_STATUS_RO_NEGOTIATION
        ):
            logger.info(
                "Case %s skipped. Phase: %s | Status: %s",
                case_id,
                current_phase,
                current_status,
            )

            raise NegotiationFailValidationError(
                "Only cases with "
                "case_current_phase='Negotiation' and "
                "case_current_status='RO Negotiation' are allowed."
            )

    def process_arrears_logic(
        self,
        case: dict[str, Any],
    ) -> dict[str, Any]:

        case_id = case.get("case_id")
        amount = self.get_current_arrears_amount(case)

        logger.info("Current arrears amount: %s", amount)

        # Amount below 50,000 -> F2 process.
        if amount < 50000:
            logger.info("Amount below 50,000")
            return self.process_f2(case, case_id)

        # Amount above 1,000,000 -> Pending FTL LOD / Letter of Demand.
        if amount > 1000000:
            self.case_repository.update_status_and_phase(
                case_id,
                STATUS_PENDING_FTL_LOD,
                PHASE_LETTER_OF_DEMAND,
                REASON_FTL_LOD,
            )

            logger.info(
                "Case %s moved to %s / %s",
                case_id,
                STATUS_PENDING_FTL_LOD,
                PHASE_LETTER_OF_DEMAND,
            )

            return self.build_success_response(
                message="Case moved to Pending FTL LOD",
                case_id=case_id,
                status=STATUS_PENDING_FTL_LOD,
                phase=PHASE_LETTER_OF_DEMAND,
                reason=REASON_FTL_LOD,
            )

        rtom_name = case.get("rtom")
        logger.info("RTOM: %s", rtom_name)

        if not rtom_name:
            raise NegotiationFailValidationError("RTOM not found")

        region_type = self.get_region_metro(case)
        logger.info("Region Type: %s", region_type)

        if region_type == METRO:

            # IMPORTANT:
            # Case current status, phase and case_status history are NOT changed here.
            interaction_created = self.process_proceed_by(case, case_id)

            return self.build_no_case_update_response(
                message="Metro case processed",
                case=case,
                reason="Metro case",
                region_metro=region_type,
                interaction_created=interaction_created,
                result_phase=PHASE_F3,
            )

        if region_type == REGION:

            if amount > 100000:

                # IMPORTANT:
                # Case current status, phase and case_status history are NOT changed here.
                interaction_created = self.process_proceed_by(case, case_id)

                return self.build_no_case_update_response(
                    message="Region above 100,000 processed",
                    case=case,
                    reason="Region above 100,000",
                    region_metro=region_type,
                    interaction_created=interaction_created,
                    result_phase=PHASE_F3,
                )

            logger.info(
                "Region case at or below 100,000. Moving to F2 process."
            )

            return self.process_f2(case, case_id)

        logger.warning("Invalid RTOM Type: %s", region_type)
        raise NegotiationFailValidationError("Invalid RTOM")

    def process_proceed_by(
        self,
        case: dict[str, Any],
        case_id: int,
    ) -> bool:

        proceed_by = case.get("Proceed_By") or case.get("proceed_by")

        if not proceed_by:
            logger.info(
                "Proceed_By not available. User interaction not created for case %s",
                case_id,
            )
            return False

        document = self.build_user_interaction_document(
            case=case,
            proceed_by=proceed_by,
        )

        logger.info(
            "Inserting User_Interaction_Log. Case_Id=%s",
            case_id,
        )
        self.interaction_log_repository.insert(document)

        logger.info(
            "Inserting User_Interaction_Progress_Log. Case_Id=%s",
            case_id,
        )
        self.interaction_progress_repository.insert(
            deepcopy(document)
        )

        logger.info(
            "User interaction created for case %s",
            case_id,
        )

        return True

    def process_f2(
        self,
        case: dict[str, Any],
        case_id: int,
    ) -> dict[str, Any]:

        amount = self.get_current_arrears_amount(case)

        credit_case_no = (
            case.get("credit_case_No")
            or case.get("credit_case_no")
        )
        account_manager_code = (
            case.get("Account_Manager_code")
            or case.get("account_manager_code")
        )
        customer_type_name = (
            case.get("Customer_Type_Name")
            or case.get("customer_type_name")
        )

        is_final_reminder = (
            amount < 3000
            or credit_case_no in FINAL_REMINDER_CREDIT_CASES
            or account_manager_code in FINAL_REMINDER_MANAGER_CODES
            or customer_type_name in FINAL_REMINDER_CUSTOMER_TYPES
        )

        logger.info(
            "F2 process started. Case_Id=%s FinalReminderCondition=%s",
            case_id,
            is_final_reminder,
        )

        # Current agreed logic:
        # Both F2 branches update to Pending LOD / Letter of Demand / Failed DRC.
        self.case_repository.update_status_and_phase(
            case_id,
            STATUS_PENDING_LOD,
            PHASE_LETTER_OF_DEMAND,
            REASON_FAILED_DRC,
        )

        self.case_repository.update_lod_final_reminder(
            case_id,
            PHASE_LETTER_OF_DEMAND,
            REASON_FAILED_DRC,
        )

        logger.info(
            "Case %s moved to Pending LOD / Letter of Demand",
            case_id,
        )

        return self.build_success_response(
            message="Case moved to Pending LOD",
            case_id=case_id,
            status=STATUS_PENDING_LOD,
            phase=PHASE_LETTER_OF_DEMAND,
            reason=REASON_FAILED_DRC,
            result_phase=PHASE_F2 if is_final_reminder else PHASE_LETTER_OF_DEMAND,
        )

    def get_region_metro(
        self,
        case: dict[str, Any],
    ) -> Optional[str]:

        rtom_name = case.get("rtom")

        if not rtom_name:
            return None

        # Case_details RTOM value normalized to uppercase before lookup.
        normalized_rtom_name = str(rtom_name).strip().upper()

        logger.info(
            "Looking up Rtom document. rtom=%s",
            normalized_rtom_name,
        )

        rtom = self.rtom_repository.find_by_rtom_name(
            normalized_rtom_name
        )

        if not rtom:
            logger.warning(
                "Rtom not found. rtom=%s",
                normalized_rtom_name,
            )
            return None

        metro_region = (
            rtom.get("metro_region")
            or rtom.get("region_metro")
        )

        if not metro_region:
            return None

        metro_region = str(metro_region).strip().upper()

        if metro_region == "METRO":
            return METRO

        if metro_region == "REGION":
            return REGION

        return None

    def build_user_interaction_document(
        self,
        case: dict[str, Any],
        proceed_by,
    ) -> dict[str, Any]:

        now = get_local_now()
        case_id = case.get("case_id")

        interaction_log_id = (
            self.interaction_log_repository.get_next_interaction_log_id()
        )

        return UserInteractionLogModel(
            doc_version=1,
            Interaction_Log_ID=interaction_log_id,
            Interaction_ID=case_id,
            initiated_reference_id=case_id,
            User_Interaction_Type=INTERACTION_TYPE_MEDIATION_BOARD,
            delegate_user_id=proceed_by,
            Created_By=CREATED_BY,
            User_Interaction_Status=[
                UserInteractionStatusEntry(
                    User_Interaction_Status=USER_INTERACTION_PENDING,
                    created_dtm=now,
                )
            ],
            parameters={
                "case_id": case_id,
            },
            Rejected_Reason=None,
            Rejected_By=None,
            created_dtm=now,
        ).model_dump()

    def is_drc_expired(
        self,
        case: dict[str, Any],
    ) -> bool:

        drc_list = case.get("drc", [])

        if not drc_list:
            return False

        latest_drc = drc_list[-1]

        expire_date = self.parse_datetime(
            latest_drc.get("expire_dtm")
        )

        if not expire_date:
            return False

        now = get_local_now()

        if expire_date.tzinfo is None:
            now = now.replace(tzinfo=None)

        return expire_date < now

    def get_current_arrears_amount(
        self,
        case: dict[str, Any],
    ) -> float:

        value = case.get("current_arrears_amount")

        return self.to_number(value)

    def build_success_response(
        self,
        message: str,
        case_id: int,
        status: str,
        phase: str,
        reason: str,
        region_metro: Optional[str] = None,
        interaction_created: bool = False,
        result_phase: Optional[str] = None,
    ) -> dict[str, Any]:

        data = {
            "Case_Id": case_id,
            "case_current_status": status,
            "case_current_phase": phase,
            "phase": result_phase or phase,
            "reason": reason,
            "interaction_created": interaction_created,
        }

        if region_metro:
            data["region_metro"] = region_metro

        return {
            "success": True,
            "message": message,
            "data": data,
        }

    def build_no_case_update_response(
        self,
        message: str,
        case: dict[str, Any],
        reason: str,
        region_metro: str,
        interaction_created: bool,
        result_phase: str,
    ) -> dict[str, Any]:

        return {
            "success": True,
            "message": message,
            "data": {
                "Case_Id": case.get("case_id"),
                "case_current_status": case.get("case_current_status"),
                "case_current_phase": case.get("case_current_phase"),
                "phase": result_phase,
                "reason": reason,
                "region_metro": region_metro,
                "interaction_created": interaction_created,
            },
        }

    def parse_datetime(
        self,
        value,
    ) -> Optional[datetime]:

        if value is None:
            return None

        if isinstance(value, datetime):
            return value

        if isinstance(value, date):
            return datetime.combine(
                value,
                datetime.min.time(),
            )

        if isinstance(value, str):
            normalized = value.replace("Z", "+00:00")

            try:
                return datetime.fromisoformat(normalized)
            except ValueError:
                logger.warning(
                    "Invalid expire_dtm value received: %s",
                    value,
                )
                return None

        return None

    def to_number(
        self,
        value,
    ) -> float:

        if value is None:
            return 0

        try:
            return float(value)
        except (TypeError, ValueError):
            return 0
