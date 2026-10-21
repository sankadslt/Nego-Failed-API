import asyncio
import json
import unittest
from datetime import timedelta

from openAPI.Negotiation_fail.controllers.negotiation_fail_controller import (
    NegotiationFailController,
)
from openAPI.Negotiation_fail.models.case_details_model import (
    NegotiationFailRequest,
)
from openAPI.Negotiation_fail.services.negotiation_fail_service import (
    CaseNotFoundError,
    NegotiationFailService,
    NegotiationFailValidationError,
)
from utils.constants import (
    CASE_PHASE_NEGOTIATION,
    CASE_STATUS_RO_NEGOTIATION,
    METRO,
    REGION,
    STATUS_PENDING_FTL_LOD,
    STATUS_PENDING_LOD,
)
from utils.timezone import get_local_now


class FakeCaseRepository:
    def __init__(self, case=None):
        self.case = case
        self.status_updates = []
        self.lod_updates = []

    def find_by_case_id(self, case_id):
        return self.case

    def update_status_and_phase(self, case_id, status, phase, reason):
        self.status_updates.append(
            {
                "case_id": case_id,
                "status": status,
                "phase": phase,
                "reason": reason,
            }
        )

    def update_lod_final_reminder(self, case_id, reason):
        self.lod_updates.append(
            {
                "case_id": case_id,
                "reason": reason,
            }
        )


class FailingCaseRepository(FakeCaseRepository):
    def find_by_case_id(self, case_id):
        raise RuntimeError("MongoDB down")


class FakeRTOMRepository:
    def __init__(self, region_metro=METRO):
        self.region_metro = region_metro

    def find_by_rtom_name(self, rtom_name):
        return {
            "rtom_name": rtom_name,
            "region_metro": self.region_metro,
        }


class FakeInteractionLogRepository:
    def __init__(self):
        self.documents = []

    def get_next_interaction_log_id(self):
        return len(self.documents) + 1

    def insert(self, document):
        self.documents.append(document)


class FakeInteractionProgressRepository:
    def __init__(self):
        self.documents = []

    def insert(self, document):
        self.documents.append(document)


def build_case(**overrides):
    case = {
        "case_id": 123456,
        "case_current_status": CASE_STATUS_RO_NEGOTIATION,
        "case_current_phase": CASE_PHASE_NEGOTIATION,
        "current_arreas_amount": 75000,
        "rtom": "Colombo",
        "Proceed_By": "agent-1",
        "drc": [
            {
                "expire_dtm": get_local_now() + timedelta(days=1),
            }
        ],
    }
    case.update(overrides)
    return case


class TestNegotiationFailService(unittest.TestCase):
    def make_service(self, case=None, region_metro=METRO):
        self.case_repository = FakeCaseRepository(case)
        self.rtom_repository = FakeRTOMRepository(region_metro)
        self.log_repository = FakeInteractionLogRepository()
        self.progress_repository = FakeInteractionProgressRepository()
        return NegotiationFailService(
            case_repository=self.case_repository,
            rtom_repository=self.rtom_repository,
            interaction_log_repository=self.log_repository,
            interaction_progress_repository=self.progress_repository,
        )

    def test_invalid_case_id(self):
        service = self.make_service()

        with self.assertRaises(NegotiationFailValidationError):
            service.process("123456")

    def test_case_not_found(self):
        service = self.make_service(case=None)

        with self.assertRaises(CaseNotFoundError):
            service.process(123456)

    def test_invalid_current_status(self):
        service = self.make_service(
            build_case(case_current_status="Pending LOD")
        )

        with self.assertRaisesRegex(
            NegotiationFailValidationError,
            "invalid current status",
        ):
            service.process(123456)

    def test_invalid_current_phase(self):
        service = self.make_service(
            build_case(case_current_phase="Letter of Demand")
        )

        with self.assertRaisesRegex(
            NegotiationFailValidationError,
            "invalid current phase",
        ):
            service.process(123456)

    def test_invalid_drc_expiry(self):
        service = self.make_service(
            build_case(
                drc=[
                    {
                        "expire_dtm": get_local_now() - timedelta(days=1),
                    }
                ]
            )
        )

        with self.assertRaisesRegex(
            NegotiationFailValidationError,
            "DRC expiry condition not satisfied",
        ):
            service.process(123456)

    def test_amount_below_50000(self):
        service = self.make_service(build_case(current_arreas_amount=49999))

        response = service.process(123456)

        self.assertTrue(response["success"])
        self.assertEqual(
            self.case_repository.status_updates[0]["status"],
            STATUS_PENDING_LOD,
        )
        self.assertEqual(len(self.case_repository.lod_updates), 1)

    def test_metro_path(self):
        service = self.make_service(
            build_case(current_arreas_amount=75000),
            region_metro=METRO,
        )

        response = service.process(123456)

        self.assertTrue(response["success"])
        self.assertEqual(
            self.case_repository.status_updates[0]["status"],
            STATUS_PENDING_FTL_LOD,
        )
        self.assertEqual(len(self.log_repository.documents), 1)
        self.assertEqual(len(self.progress_repository.documents), 1)

    def test_region_above_100000(self):
        service = self.make_service(
            build_case(current_arreas_amount=150000),
            region_metro=REGION,
        )

        response = service.process(123456)

        self.assertTrue(response["success"])
        self.assertEqual(
            self.case_repository.status_updates[0]["status"],
            STATUS_PENDING_FTL_LOD,
        )
        self.assertEqual(len(self.log_repository.documents), 1)
        self.assertEqual(len(self.progress_repository.documents), 1)

    def test_region_below_100000(self):
        service = self.make_service(
            build_case(current_arreas_amount=75000),
            region_metro=REGION,
        )

        response = service.process(123456)

        self.assertTrue(response["success"])
        self.assertEqual(
            self.case_repository.status_updates[0]["status"],
            STATUS_PENDING_LOD,
        )
        self.assertEqual(len(self.case_repository.lod_updates), 1)
        self.assertEqual(len(self.log_repository.documents), 0)

    def test_mongodb_exception_returns_500_from_controller(self):
        class FailingService:
            def process(self, case_id):
                raise RuntimeError("MongoDB down")

        controller = NegotiationFailController(service=FailingService())
        response = asyncio.run(
            controller.process_negotiation_fail(
                NegotiationFailRequest(Case_Id=123456)
            )
        )
        payload = json.loads(response.body)

        self.assertEqual(response.status_code, 500)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["message"], "Unexpected exception")


if __name__ == "__main__":
    unittest.main()
