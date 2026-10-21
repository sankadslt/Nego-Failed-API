import unittest

from pydantic import ValidationError

from openAPI.Negotiation_fail.models.case_details_model import (
    CaseDetailsModel,
    NegotiationFailRequest,
    NegotiationFailResponse,
)


class TestCaseDetailsModels(unittest.TestCase):
    def test_request_accepts_integer_case_id(self):
        self.assertEqual(NegotiationFailRequest(Case_Id=123456).Case_Id, 123456)

    def test_request_rejects_missing_case_id(self):
        with self.assertRaises(ValidationError):
            NegotiationFailRequest()

    def test_request_rejects_invalid_case_id(self):
        with self.assertRaises(ValidationError):
            NegotiationFailRequest(Case_Id="ABC")

        with self.assertRaises(ValidationError):
            NegotiationFailRequest(Case_Id="123456")

    def test_case_details_allows_extra_mongo_fields(self):
        model = CaseDetailsModel(
            case_id=123456,
            case_current_phase="Negotiation",
            case_current_status="RO Negotiation",
            extra_field="kept",
        )

        self.assertEqual(model.extra_field, "kept")

    def test_response_shape(self):
        response = NegotiationFailResponse(
            success=False,
            message="Case not found",
        )

        self.assertFalse(response.success)
        self.assertEqual(response.message, "Case not found")
        self.assertIsNone(response.data)


if __name__ == "__main__":
    unittest.main()
