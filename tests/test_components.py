import unittest
from unittest.mock import MagicMock, patch

from src.config_loader import ConfigLoader
from src.workflow.logger import AppLogger
from src.security.security_manager import SecurityManager
from src.performance.batch_processor import BatchProcessor
from src.performance.cache_manager import CacheManager
from src.performance.performance_optimizer import PerformanceOptimizer
from src.error_handling.enhanced_error_recovery import EnhancedErrorRecovery
from src.compliance.regulatory_compliance import RegulatoryCompliance
from src.mobile_capture.mobile_document_capture import MobileDocumentCapture
from src.reconciliation.automated_reconciliation import AutomatedReconciliation
from src.migration.data_migration import DataMigration
from src.migration.migration_wizard import MigrationWizard
from src.budget.budget_manager import BudgetManager
from src.banking.banking_api import BankingAPI
from src.financial_analysis.financial_analyzer import FinancialAnalyzer
from src.manual_review.manual_review_interface import ManualReviewInterface
from src.backup.backup_manager import BackupManager

class TestComponents(unittest.TestCase):

    def setUp(self):
        self.config = {
            "log_file": "/tmp/test_app.log",
            "security_key": "a_very_secret_key_for_testing_1234567890",
            "cache_dir": "/tmp/cache",
            "error_recovery_max_retries": 3,
            "error_recovery_retry_delay_seconds": 1,
            "compliance_rules_file": "/tmp/compliance_rules.json",
            "mobile_capture_upload_dir": "/tmp/mobile_uploads",
            "reconciliation_threshold": 0.05,
            "migration_source_db": "sqlite:///tmp/source.db",
            "migration_target_db": "sqlite:///tmp/target.db",
            "budget_file": "/tmp/budgets.json",
            "banking_api_endpoint": "http://banking.api/",
            "banking_api_credentials": {"client_id": "test", "client_secret": "test"},
            "backup_base_dir": "/tmp/backups",
            "backup_paths": [],
            "backup_config": {"type": "zip"},
            "manual_review_queue_file": "/tmp/manual_review_queue.json"
        }

    def test_config_loader(self):
        # Create a dummy config file
        with open("config/test_config.ini", "w") as f:
            f.write("[app]\nkey=value\n[section2]\nkey2=value2")
        
        loader = ConfigLoader(config_file="config/test_config.ini")
        config = loader.get_all_config()
        self.assertEqual(config["app"]["key"], "value")
        self.assertEqual(loader.get("section2", "key2"), "value2")
        os.remove("config/test_config.ini")

    def test_app_logger(self):
        logger = AppLogger(log_file=self.config["log_file"]).get_logger()
        logger.info("Test log message")
        with open(self.config["log_file"], "r") as f:
            content = f.read()
            self.assertIn("Test log message", content)
        os.remove(self.config["log_file"])

    def test_security_manager(self):
        manager = SecurityManager(self.config)
        encrypted_data = manager.encrypt_data("sensitive_info")
        decrypted_data = manager.decrypt_data(encrypted_data)
        self.assertEqual(decrypted_data, "sensitive_info")

    def test_batch_processor(self):
        processor = BatchProcessor(self.config)
        mock_process_func = MagicMock(return_value="processed")
        results = processor.process_batch(["item1", "item2"], mock_process_func)
        self.assertEqual(results, ["processed", "processed"])
        mock_process_func.assert_called_with("item2")

    def test_cache_manager(self):
        manager = CacheManager(self.config)
        manager.set("test_key", {"data": "value"})
        cached_data = manager.get("test_key")
        self.assertEqual(cached_data["data"], "value")
        manager.clear("test_key")
        self.assertIsNone(manager.get("test_key"))
        shutil.rmtree(self.config["cache_dir"])

    def test_performance_optimizer(self):
        optimizer = PerformanceOptimizer(self.config)
        # This is a placeholder test, actual optimization would be complex
        result = optimizer.optimize_processing_pipeline(MagicMock())
        self.assertIsNotNone(result)

    def test_enhanced_error_recovery(self):
        recovery = EnhancedErrorRecovery(self.config)
        mock_action = MagicMock(side_effect=Exception("Test Error"))
        result = recovery.execute_with_retry(mock_action, "test_operation")
        self.assertFalse(result)
        self.assertEqual(mock_action.call_count, self.config["error_recovery_max_retries"] + 1)

    def test_regulatory_compliance(self):
        # Create a dummy compliance rules file
        with open(self.config["compliance_rules_file"], "w") as f:
            f.write("{\"rules\": [{\"id\": \"rule1\", \"description\": \"Test Rule\", \"criteria\": {\"category\": \"Business\"}}]}")
        
        compliance = RegulatoryCompliance(self.config)
        document = {"category": "Business", "amount": 100}
        result = compliance.check_compliance(document)
        self.assertTrue(result["is_compliant"])
        self.assertIn("rule1", result["compliant_rules"])
        os.remove(self.config["compliance_rules_file"])

    def test_mobile_document_capture(self):
        capture = MobileDocumentCapture(self.config)
        # This test would involve simulating an upload, which is complex
        # For now, just test initialization
        self.assertIsNotNone(capture)

    def test_automated_reconciliation(self):
        reconciliation = AutomatedReconciliation(self.config)
        # Dummy data for reconciliation
        transaction1 = {"id": "t1", "amount": 100.0, "date": "2025-01-01"}
        transaction2 = {"id": "t2", "amount": 100.01, "date": "2025-01-01"}
        transactions = [transaction1, transaction2]
        receipt = {"id": "r1", "total_amount": 100.0, "transaction_date": "2025-01-01"}
        
        matches = reconciliation.reconcile(transactions, [receipt])
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["receipt_id"], "r1")

    def test_data_migration(self):
        migration = DataMigration(self.config)
        # This test would involve actual database interactions
        # For now, just test initialization
        self.assertIsNotNone(migration)

    def test_migration_wizard(self):
        wizard = MigrationWizard(self.config)
        # This test would involve user interaction simulation
        # For now, just test initialization
        self.assertIsNotNone(wizard)

    def test_budget_manager(self):
        # Create a dummy budget file
        with open(self.config["budget_file"], "w") as f:
            f.write("{\"categories\": {\"Food\": {\"limit\": 200, \"spent\": 50}}}")
        
        manager = BudgetManager(self.config)
        status = manager.check_budget("Food", 100)
        self.assertFalse(status["is_within_budget"])
        self.assertEqual(status["remaining"], 50)
        os.remove(self.config["budget_file"])

    @patch("src.banking.banking_api.requests.post")
    def test_banking_api(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"transactions": [{"id": "tx1", "amount": 50.0}]}
        mock_post.return_value = mock_response

        api = BankingAPI(self.config)
        transactions = api.fetch_transactions("2025-01-01", "2025-01-31")
        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0]["amount"], 50.0)

    def test_financial_analyzer(self):
        analyzer = FinancialAnalyzer(self.config)
        # Dummy data for analysis
        transactions = [
            {"date": "2025-01-01", "amount": 100, "category": "Income"},
            {"date": "2025-01-05", "amount": -50, "category": "Food"}
        ]
        report = analyzer.generate_report(transactions)
        self.assertIn("total_income", report)
        self.assertEqual(report["total_income"], 100)

    def test_manual_review_interface(self):
        interface = ManualReviewInterface(self.config)
        interface.add_to_review_queue("doc_test", "Test Reason")
        pending = interface.get_pending_reviews()
        self.assertEqual(len(pending), 1)
        interface.mark_reviewed("doc_test")
        pending = interface.get_pending_reviews()
        self.assertEqual(len(pending), 0)
        os.remove(self.config["manual_review_queue_file"])

    def test_backup_manager(self):
        manager = BackupManager(self.config)
        # Create a dummy file to backup
        with open("/tmp/test_file.txt", "w") as f:
            f.write("This is a test file.")
        
        backup_result = manager.perform_backup(["/tmp/test_file.txt"], {"type": "zip"})
        self.assertEqual(backup_result["status"], "success")
        self.assertTrue(os.path.exists(backup_result["path"]))

        restore_dir = "/tmp/restore_test"
        restore_result = manager.restore_backup(backup_result["path"], restore_dir)
        self.assertEqual(restore_result["status"], "success")
        self.assertTrue(os.path.exists(os.path.join(restore_dir, "test_file.txt")))

        os.remove("/tmp/test_file.txt")
        os.remove(backup_result["path"])
        shutil.rmtree(restore_dir)
        shutil.rmtree(self.config["backup_base_dir"])

if __name__ == "__main__":
    unittest.main()


