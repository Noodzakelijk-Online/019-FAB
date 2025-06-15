from typing import Dict, Any, List
import os

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

class WorkflowController:
    """Orchestrates the entire automated bookkeeping workflow."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = AppLogger(log_file=self.config.get("log_file")).get_logger()

        self.fetchers = {
            "gmail": GmailFetcher(config),
            "drive": DriveFetcher(config),
            "freshdesk": FreshdeskFetcher(config),
            "photos": PhotosFetcher(config)
        }
        self.processor_pipeline = ProcessorPipeline(config)
        self.categorizer = HybridCategorizer(config)
        self.data_entry_handlers = {
            "mijngeldzaken": MijngeldzakenHandler(config),
            "waveapps_business": WaveappsBusinessHandler(config),
            "waveapps_personal": WaveappsPersonalHandler(config)
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
        
        # 1. Fetch Documents
        all_documents = []
        for source, fetcher in self.fetchers.items():
            try:
                self.logger.info(f"Fetching documents from {source}...")
                documents = fetcher.fetch_documents()
                all_documents.extend(documents)
                self.logger.info(f"Fetched {len(documents)} documents from {source}.")
            except Exception as e:
                self.logger.error(f"Error fetching from {source}: {e}")
                self.error_recovery.handle_error(e, f"fetch_{source}")

        if not all_documents:
            self.logger.info("No new documents to process. Workflow finished.")
            return

        # 2. Process Documents
        processed_documents = []
        for doc in all_documents:
            try:
                self.logger.info(f"Processing document: {doc['original_filename']}")
                processed_data = self.processor_pipeline.process_document(doc["local_path"])
                processed_data["document_id"] = doc["id"]
                processed_documents.append(processed_data)
            except Exception as e:
                self.logger.error(f"Error processing {doc['original_filenam']}: {e}")
                self.error_recovery.handle_error(e, f"process_{doc['id']}")
                self.manual_review_interface.add_to_review_queue(doc["id"], "processing_failed", str(e))

        # 3. Categorize Documents
        categorized_documents = []
        for doc_data in processed_documents:
            try:
                self.logger.info(f"Categorizing document: {doc_data['document_id']}")
                category_result = self.categorizer.categorize(doc_data)
                doc_data.update(category_result) # Add category and confidence
                categorized_documents.append(doc_data)
            except Exception as e:
                self.logger.error(f"Error categorizing {doc_data["document_id"]}: {e}")
                self.error_recovery.handle_error(e, f"categorize_{doc_data["document_id"]}")
                self.manual_review_interface.add_to_review_queue(doc_data["document_id"], "categorization_failed", str(e))

        # 4. Validate and Budget Check
        validated_and_budgeted_docs = []
        for doc_data in categorized_documents:
            try:
                self.logger.info(f"Validating and budget checking document: {doc_data["document_id"]}")
                validation_result = self.validation_manager.validate_receipt(doc_data)
                if not validation_result["is_valid"]:
                    self.logger.warning(f"Validation failed for {doc_data["document_id"]}: {validation_result["reason"]}")
                    self.manual_review_interface.add_to_review_queue(doc_data["document_id"], "validation_failed", validation_result["reason"])
                    continue # Skip data entry for invalid documents
                
                budget_check_result = self.budget_manager.check_budget(doc_data)
                if not budget_check_result["is_within_budget"]:
                    self.logger.warning(f"Budget exceeded for {doc_data["document_id"]}: {budget_check_result["message"]}")
                    self.manual_review_interface.add_to_review_queue(doc_data["document_id"], "budget_exceeded", budget_check_result["message"])
                    # Decide whether to proceed with data entry or not based on config

                validated_and_budgeted_docs.append(doc_data)
            except Exception as e:
                self.logger.error(f"Error during validation/budget check for {doc_data["document_id"]}: {e}")
                self.error_recovery.handle_error(e, f"validate_budget_{doc_data["document_id"]}")
                self.manual_review_interface.add_to_review_queue(doc_data["document_id"], "validation_budget_error", str(e))

        # 5. Data Entry
        for doc_data in validated_and_budgeted_docs:
            target_system = None
            if doc_data["category"] == "Personal":
                target_system = "mijngeldzaken"
            elif doc_data["category"] == "Business":
                target_system = "waveapps_business"
            elif doc_data["category"] == "Handicaps":
                target_system = "waveapps_personal"
            
            if target_system:
                try:
                    self.logger.info(f"Entering data for {doc_data["document_id"]} into {target_system}...")
                    handler = self.data_entry_handlers[target_system]
                    entry_result = handler.enter_data(doc_data)
                    if entry_result["status"] == "success":
                        self.logger.info(f"Successfully entered {doc_data["document_id"]} into {target_system}.")
                        # Trigger learning manager feedback
                        self.learning_manager.provide_feedback(doc_data["document_id"], doc_data["category"], True)
                    else:
                        self.logger.warning(f"Failed to enter {doc_data["document_id"]} into {target_system}: {entry_result["message"]}")
                        self.error_recovery.handle_error(Exception(entry_result["message"]), f"data_entry_{doc_data["document_id"]}")
                        if entry_result.get("requires_manual_review", False):
                            self.manual_review_interface.add_to_review_queue(doc_data["document_id"], "data_entry_failed", entry_result["message"])
                except Exception as e:
                    self.logger.error(f"Error during data entry for {doc_data["document_id"]} into {target_system}: {e}")
                    self.error_recovery.handle_error(e, f"data_entry_{doc_data["document_id"]}")
                    self.manual_review_interface.add_to_review_queue(doc_data["document_id"], "data_entry_error", str(e))
            else:
                self.logger.warning(f"No target system for category {doc_data["category"]} for document {doc_data["document_id"]}. Requires manual review.")
                self.manual_review_interface.add_to_review_queue(doc_data["document_id"], "no_target_system", f"Category {doc_data["category"]} has no defined target system.")

        # 6. Reconciliation (after data entry, or as a separate scheduled task)
        try:
            self.logger.info("Starting automated reconciliation...")
            bank_transactions = self.banking_api.fetch_transactions(self.config.get("banking_api_credentials"))
            reconciliation_results = self.reconciliation_manager.reconcile(bank_transactions, processed_documents) # This needs refinement
            for result in reconciliation_results:
                if not result["matched"]:
                    self.logger.warning(f"Unmatched transaction/document: {result}")
                    self.manual_review_interface.add_to_review_queue(result["id"], "unmatched_reconciliation", str(result))
        except Exception as e:
            self.logger.error(f"Error during reconciliation: {e}")
            self.error_recovery.handle_error(e, "reconciliation_workflow")

        # 7. Backup
        try:
            self.logger.info("Performing backup...")
            self.backup_manager.perform_backup(self.config.get("backup_paths"), self.config.get("backup_config"))
            self.logger.info("Backup completed.")
        except Exception as e:
            self.logger.error(f"Error during backup: {e}")
            self.error_recovery.handle_error(e, "backup_workflow")

        self.logger.info("Automated bookkeeping workflow finished.")



