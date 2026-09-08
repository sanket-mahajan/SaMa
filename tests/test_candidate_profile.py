import json
from pathlib import Path
import unittest

from app.profile import ProfileValidationError, validate_candidate_profile


EXAMPLE_PATH = Path(__file__).parents[1] / "data" / "examples" / "candidate-profile.json"


class CandidateProfileValidationTests(unittest.TestCase):
    def example(self):
        return json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))

    def test_example_profile_is_valid_and_normalized(self):
        profile = validate_candidate_profile(self.example())

        self.assertEqual(str(profile.candidate_id), "2f6f594a-f7de-4b11-9f64-6baa78bf5ab1")
        self.assertEqual(profile.skills[1].years_experience, 3.5)
        self.assertTrue(profile.experience[0].is_current)

    def test_validation_reports_multiple_actionable_issues(self):
        payload = self.example()
        payload["email"] = "not-an-email"
        payload["skills"] = [{"name": "Python"}, {"name": " python "}]
        payload["experience"][0]["is_current"] = False

        with self.assertRaises(ProfileValidationError) as raised:
            validate_candidate_profile(payload)

        message = str(raised.exception)
        self.assertIn("email", message)
        self.assertIn("duplicates another skill", message)
        self.assertIn("end_date is required", message)

    def test_rejects_invalid_role_date_range(self):
        payload = self.example()
        role = payload["experience"][0]
        role.update({"is_current": False, "end_date": "2021-01-01"})

        with self.assertRaisesRegex(ProfileValidationError, "cannot be before"):
            validate_candidate_profile(payload)

    def test_rejects_current_role_with_end_date(self):
        payload = self.example()
        payload["experience"][0]["end_date"] = "2025-01-01"

        with self.assertRaisesRegex(ProfileValidationError, "must be omitted"):
            validate_candidate_profile(payload)


if __name__ == "__main__":
    unittest.main()
