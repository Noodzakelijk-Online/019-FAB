import unittest

from src.operations.local_category_suggestions import (
    normalize_vendor_name,
    suggest_category_intent,
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


if __name__ == "__main__":
    unittest.main()
