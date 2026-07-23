import unittest

from src.operations.local_category_suggestions import (
    normalize_vendor_name,
    suggest_category_intent,
    trusted_category_automation_candidate,
)


class TestLocalCategorySuggestions(unittest.TestCase):
    def test_exact_known_vendor_gets_explainable_suggestion(self):
        suggestion = suggest_category_intent({
            "vendor_name": "Hornbach Bouwmarkt Bv",
            "category": "Manual Review",
        })

        self.assertEqual(suggestion["category"], "Construction Materials & Tools")
        self.assertEqual(suggestion["matchPolicy"], "exact_normalized_vendor")
        self.assertTrue(suggestion["requiresApproval"])
        self.assertGreaterEqual(suggestion["confidenceScore"], 0.95)

    def test_ocr_punctuation_does_not_break_exact_normalized_match(self):
        suggestion = suggest_category_intent({
            "vendor_name": "***T-Mobile",
            "category": "Uncategorized",
        })

        self.assertEqual(suggestion["category"], "Telecommunications")
        self.assertEqual(normalize_vendor_name("***T-Mobile"), "t mobile")

    def test_unknown_or_already_classified_vendor_is_not_suggested(self):
        self.assertIsNone(suggest_category_intent({
            "vendor_name": "Unknown Shop",
            "category": "Manual Review",
        }))
        self.assertIsNone(suggest_category_intent({
            "vendor_name": "Slack",
            "category": "Software & Subscriptions",
        }))

    def test_trusted_automation_accepts_only_enabled_exact_builtin_policy(self):
        document = {
            "vendor_name": "Praxis",
            "category": "Manual Review",
        }

        candidate = trusted_category_automation_candidate(document)
        disabled = trusted_category_automation_candidate(
            document,
            {"fab_auto_apply_trusted_category_suggestions": False},
        )
        raised_floor = trusted_category_automation_candidate(
            document,
            {"fab_trusted_category_suggestion_min_confidence": 0.99},
        )

        self.assertEqual(candidate["category"], "Construction Materials & Tools")
        self.assertEqual(candidate["automationPolicy"], "builtin_exact_vendor_taxonomy_v1")
        self.assertEqual(candidate["automationThreshold"], 0.95)
        self.assertFalse(candidate["requiresApproval"])
        self.assertEqual(candidate["approvalMode"], "trusted_bounded_policy")
        self.assertIsNone(disabled)
        self.assertIsNone(raised_floor)


if __name__ == "__main__":
    unittest.main()
