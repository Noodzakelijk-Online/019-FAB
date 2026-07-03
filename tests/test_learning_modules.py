import unittest
from unittest.mock import MagicMock, patch
import os
import json
import tempfile

from src.learning.waveapps_analyzer import WaveappsAnalyzer
from src.learning.mijngeldzaken_analyzer import MijngeldzakenAnalyzer
from src.learning.feedback_learner import FeedbackLearner
from src.learning.learning_manager import LearningManager
from src.learning.enhanced_learning_system import EnhancedLearningSystem

class TestLearningModules(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.config = {
            "waveapps_business_access_token": "dummy_token",
            "waveapps_business_id": "dummy_business_id",
            "mijngeldzaken_username": "dummy_user",
            "mijngeldzaken_password": "dummy_pass",
            "mijngeldzaken_export_file_path": os.path.join(self.temp_dir.name, "mijngeldzaken_export.csv"),
            "feedback_log_file": os.path.join(self.temp_dir.name, "feedback_log.json"),
            "learned_patterns_file": os.path.join(self.temp_dir.name, "learned_patterns.json"),
            "ml_model_path": os.path.join(self.temp_dir.name, "ml_categorizer_model.joblib"),
            "ml_vectorizer_path": os.path.join(self.temp_dir.name, "tfidf_vectorizer.joblib")
        }
        # Create dummy files for testing
        os.makedirs(os.path.dirname(self.config["feedback_log_file"]), exist_ok=True)
        os.makedirs(os.path.dirname(self.config["learned_patterns_file"]), exist_ok=True)
        os.makedirs(os.path.dirname(self.config["ml_model_path"]), exist_ok=True)

        with open(self.config["mijngeldzaken_export_file_path"], "w", newline="") as f:
            f.write("Date,Description,Amount,Category\n")
            f.write("2025-01-01,Groceries,50.00,Food\n")
            f.write("2025-01-02,Electricity Bill,100.00,Utilities\n")

    @patch("src.learning.waveapps_analyzer.requests.post")
    def test_waveapps_analyzer(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "data": {
                "business": {
                    "expenses": {
                        "edges": [
                            {"node": {"id": "exp1", "description": "Coffee", "amount": {"value": 5.0, "currency": "CAD"}, "incurredAt": "2025-01-01", "category": {"name": "Food"}, "vendor": {"name": "Starbucks"}}},
                            {"node": {"id": "exp2", "description": "Software License", "amount": {"value": 50.0, "currency": "CAD"}, "incurredAt": "2025-01-02", "category": {"name": "Software"}, "vendor": {"name": "Microsoft"}}}
                        ]
                    }
                }
            }
        }
        mock_post.return_value = mock_response

        analyzer = WaveappsAnalyzer(self.config)
        transactions = analyzer.analyze_transactions()
        self.assertEqual(len(transactions), 2)
        self.assertEqual(transactions[0]["category"], "Food")

        patterns = analyzer.learn_patterns(transactions)
        self.assertIn("Starbucks", patterns["vendor_category_map"])
        self.assertEqual(patterns["vendor_category_map"]["Starbucks"], "Food")

    def test_mijngeldzaken_analyzer(self):
        analyzer = MijngeldzakenAnalyzer(self.config)
        patterns = analyzer.analyze_data(self.config["mijngeldzaken_export_file_path"])
        self.assertIn("groceries", patterns["description_keywords_map"])
        self.assertEqual(patterns["description_keywords_map"]["groceries"], "Food")

    def test_feedback_learner(self):
        learner = FeedbackLearner(self.config)
        learner.record_feedback("doc123", "OldCategory", "NewCategory")
        feedback = learner.get_all_feedback()
        self.assertEqual(len(feedback), 1)
        self.assertEqual(feedback[0]["document_id"], "doc123")

    @patch("src.learning.learning_manager.WaveappsAnalyzer")
    @patch("src.learning.learning_manager.MijngeldzakenAnalyzer")
    @patch("src.learning.learning_manager.FeedbackLearner")
    def test_learning_manager(self, MockFeedbackLearner, MockMijngeldzakenAnalyzer, MockWaveappsAnalyzer):
        mock_waveapps_analyzer_instance = MagicMock()
        mock_waveapps_analyzer_instance.analyze_transactions.return_value = [
            {"vendor": "TestVendor", "category": "TestCategory", "description": "test description"}
        ]
        mock_waveapps_analyzer_instance.learn_patterns.return_value = {"vendor_category_map": {"TestVendor": "TestCategory"}}
        MockWaveappsAnalyzer.return_value = mock_waveapps_analyzer_instance

        mock_mijngeldzaken_analyzer_instance = MagicMock()
        mock_mijngeldzaken_analyzer_instance.analyze_data.return_value = {"description_keywords_map": {"groceries": "Food"}}
        MockMijngeldzakenAnalyzer.return_value = mock_mijngeldzaken_analyzer_instance

        manager = LearningManager(self.config)
        manager.learn_from_existing_data()
        
        learned_patterns = manager.get_learned_patterns("waveapps_business")
        self.assertIn("TestVendor", learned_patterns["vendor_category_map"])

        manager.provide_feedback("doc456", "Original", "Corrected")
        MockFeedbackLearner.return_value.record_feedback.assert_called_once_with("doc456", "Original", "Corrected")

    @patch("src.learning.enhanced_learning_system.LearningManager")
    @patch("src.learning.enhanced_learning_system.FeedbackLearner")
    @patch("src.learning.enhanced_learning_system.MLCategorizer")
    def test_enhanced_learning_system(self, MockMLCategorizer, MockFeedbackLearner, MockLearningManager):
        mock_feedback_learner_instance = MagicMock()
        mock_feedback_learner_instance.get_all_feedback.return_value = [
            {"document_id": "doc1", "original_category": "A", "corrected_category": "B"}
        ]
        MockFeedbackLearner.return_value = mock_feedback_learner_instance

        mock_ml_categorizer_instance = MagicMock()
        MockMLCategorizer.return_value = mock_ml_categorizer_instance

        system = EnhancedLearningSystem(self.config)
        system.run_initial_learning()
        MockLearningManager.return_value.learn_from_existing_data.assert_called_once()

        system.process_feedback()
        mock_ml_categorizer_instance.train_model.assert_called_once()

    def tearDown(self):
        # Clean up dummy files
        if os.path.exists(self.config["mijngeldzaken_export_file_path"]):
            os.remove(self.config["mijngeldzaken_export_file_path"])
        if os.path.exists(self.config["feedback_log_file"]):
            os.remove(self.config["feedback_log_file"])
        if os.path.exists(self.config["learned_patterns_file"]):
            os.remove(self.config["learned_patterns_file"])
        if os.path.exists(self.config["ml_model_path"]):
            os.remove(self.config["ml_model_path"])
        if os.path.exists(self.config["ml_vectorizer_path"]):
            os.remove(self.config["ml_vectorizer_path"])

if __name__ == "__main__":
    unittest.main()


