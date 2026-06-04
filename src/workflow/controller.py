from typing import Dict, Any

from src.workflow.logger import AppLogger
from src.document_fetchers.gmail_fetcher import GmailFetcher
from src.document_fetchers.drive_fetcher import DriveFetcher
from src.document_fetchers.freshdesk_fetcher import FreshdeskFetcher
from src.document_fetchers.photos_fetcher import PhotosFetcher
from src.document_processors.processor_pipeline import ProcessorPipeline
from src.categorizers.hybrid_categorizer import HybridCategorizer
from src.data_entry.mijngeldzaken_handler import MijngeldzakenHandler
from src.data_entry.waveapps_business_handler import WaveappsBusinessHandler
from src.data_entry.waveapps_personal_handler import WaveappsPersonalHandler
from src.learning.learning_manager import LearningManager
from src.error_handling.enhanced_error_recovery import EnhancedErrorRecovery
from src.validation.validation_manager import ValidationManager
from src.budget.budget_manager import BudgetManager
from src.banking.banking_api import BankingAPI
from src.reconciliation.automated_reconciliation import AutomatedReconciliation
from src.manual_review.manual_review_interface import ManualReviewInterface
from src.backup.backup_manager import BackupManager
from src.security.security_manager import SecurityManager
from src.performance.performance_optimizer import PerformanceOptimizer
from src.routing.bookkeeping_router import BookkeepingRouter


class WorkflowController:
    """Orchestrates the automated bookkeeping workflow."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = AppLogger(log_file=self.config.get("log_file")).get_logger()

        self.fetchers = {
            "gmail": GmailFetcher(config),
            "drive": DriveFetcher(config),
            "freshdesk": FreshdeskFetcher(config),
            "photos": PhotosFetcher(config),
        }
        self.processor_pipeline = ProcessorPipeline(config)
        self.categorizer = HybridCategorizer(config)
        self.router = BookkeepingRouter(config)
        self.data_entry_handlers = {
            "mijngeldzaken": MijngeldzakenHandler(config),
            "waveapps_business": WaveappsBusinessHandler(config),
            "waveapps_personal": WaveappsPersonalHandler(config),
        }
        self.learning_manager = LearningManager(config)
        self.error_recovery = EnhancedErrorRecovery(config)
        self.validation_manager = ValidationManager(config)
        self.budget_manager = BudgetManager(config)
        self.banking_api = BankingAPI(config)
        self.reconciliation_manager = AutomatedReconciliation(config)
        self.manual_review_interface = ManualReviewInterface(config)
        self.backup_manager = BackupManager(config)
        self.security_manager = SecurityManager(config)
        self.performance_optimizer = PerformanceOptimizer(config)

    def run_workflow(self):
        self.logger.info("Starting automated bookkeeping workflow...")

        all_documents = []
        for source, fetcher in self.fetchers.items():
            try:
                self.logger.info("Fetching documents from %s...", source)
                documents = fetcher.fetch_documents()
                all_documents.extend(documents)
                self.logger.info("Fetched %s documents from %s.", len(documents), source)
            except Exception as exc:
                self.logger.error("Error fetching from %s: %s", source, exc)
                self.error_recovery.handle_error(exc, f"fetch_{source}")

        if not all_documents:
            self.logger.info("No new documents to process. Workflow finished.")
            return

        processed_documents = []
        for doc in all_documents:
            document_id = doc.get("id")
            original_filename = doc.get("original_filename", "unknown")
            try:
                self.logger.info("Processing document: %s", original_filename)
                processed_data = self.processor_pipeline.process_document(doc["local_path"])
                processed_data["document_id"] = document_id
                processed_data["source_document"] = doc
                processed_documents.append(processed_data)
            except Exception as exc:
                self.logger.error("Error processing %s: %s", original_filename, exc)
                self.error_recovery.handle_error(exc, f"process_{document_id}", document_id=document_id)
                self.manual_review_interface.add_to_review_queue(document_id, "processing_failed", str(exc))

        categorized_documents = []
        for doc_data in processed_documents:
            document_id = doc_data.get("document_id")
            try:
                self.logger.info("Categorizing document: %s", document_id)
                category_result = self.categorizer.categorize(doc_data)
                doc_data.update(category_result)
                categorized_documents.append(doc_data)
            except Exception as exc:
                self.logger.error("Error categorizing %s: %s", document_id, exc)
                self.error_recovery.handle_error(exc, f"categorize_{document_id}", document_id=document_id)
                self.manual_review_interface.add_to_review_queue(document_id, "categorization_failed", str(exc))

        validated_and_budgeted_docs = []
        for doc_data in categorized_documents:
            document_id = doc_data.get("document_id")
            try:
                self.logger.info("Validating and budget checking document: %s", document_id)
                validation_result = self.validation_manager.validate_receipt(doc_data)
                if not validation_result.get("is_valid"):
                    reason = validation_result.get("reason", "Validation failed")
                    self.logger.warning("Validation failed for %s: %s", document_id, reason)
                    self.manual_review_interface.add_to_review_queue(document_id, "validation_failed", reason)
                    continue

                budget_check_result = self.budget_manager.check_budget(doc_data)
                if not budget_check_result.get("is_within_budget", True):
                    message = budget_check_result.get("message", "Budget check failed")
                    self.logger.warning("Budget exceeded for %s: %s", document_id, message)
                    self.manual_review_interface.add_to_review_queue(document_id, "budget_exceeded", message)

                validated_and_budgeted_docs.append(doc_data)
            except Exception as exc:
                self.logger.error("Error during validation/budget check for %s: %s", document_id, exc)
                self.error_recovery.handle_error(exc, f"validate_budget_{document_id}", document_id=document_id)
                self.manual_review_interface.add_to_review_queue(document_id, "validation_budget_error", str(exc))

        for doc_data in validated_and_budgeted_docs:
            document_id = doc_data.get("document_id")
            route_result = self.router.route(doc_data)
            target_system = route_result.get("target_system")
            doc_data.update(route_result)

            if not target_system:
                category = doc_data.get("category", "unknown")
                message = f"Category {category} has no defined target system."
                self.logger.warning("No target system for category %s for document %s.", category, document_id)
                self.manual_review_interface.add_to_review_queue(document_id, "no_target_system", message)
                continue

            try:
                self.logger.info("Entering data for %s into %s...", document_id, target_system)
                handler = self.data_entry_handlers[target_system]
                entry_result = handler.enter_data(doc_data)
                if entry_result.get("status") == "success":
                    self.logger.info("Successfully entered %s into %s.", document_id, target_system)
                    self.learning_manager.provide_feedback(document_id, doc_data.get("category"), True)
                else:
                    message = entry_result.get("message", "Data entry failed")
                    self.logger.warning("Failed to enter %s into %s: %s", document_id, target_system, message)
                    self.error_recovery.handle_error(Exception(message), f"data_entry_{document_id}", document_id=document_id)
                    if entry_result.get("requires_manual_review", False):
                        self.manual_review_interface.add_to_review_queue(document_id, "data_entry_failed", message)
            except Exception as exc:
                self.logger.error("Error during data entry for %s into %s: %s", document_id, target_system, exc)
                self.error_recovery.handle_error(exc, f"data_entry_{document_id}", document_id=document_id)
                self.manual_review_interface.add_to_review_queue(document_id, "data_entry_error", str(exc))

        try:
            self.logger.info("Starting automated reconciliation...")
            bank_transactions = self.banking_api.fetch_transactions(self.config.get("banking_api_credentials"))
            reconciliation_results = self.reconciliation_manager.reconcile(bank_transactions, processed_documents)
            for result in reconciliation_results:
                if not result.get("matched"):
                    review_id = result.get("id") or result.get("transaction", {}).get("id") or "unknown_reconciliation_item"
                    self.logger.warning("Unmatched transaction/document: %s", result)
                    self.manual_review_interface.add_to_review_queue(review_id, "unmatched_reconciliation", str(result))
        except Exception as exc:
            self.logger.error("Error during reconciliation: %s", exc)
            self.error_recovery.handle_error(exc, "reconciliation_workflow")

        try:
            self.logger.info("Performing backup...")
            self.backup_manager.perform_backup(self.config.get("backup_paths"), self.config.get("backup_config"))
            self.logger.info("Backup completed.")
        except Exception as exc:
            self.logger.error("Error during backup: %s", exc)
            self.error_recovery.handle_error(exc, "backup_workflow")

        self.logger.info("Automated bookkeeping workflow finished.")
