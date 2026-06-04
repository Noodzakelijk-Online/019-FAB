from typing import Any, Dict, Iterable, List

from src.workflow.logger import AppLogger
from src.document_fetchers.gmail_fetcher import GmailFetcher
from src.document_fetchers.drive_fetcher import DriveFetcher
from src.document_fetchers.freshdesk_fetcher import FreshdeskFetcher
from src.document_fetchers.photos_fetcher import PhotosFetcher
from src.document_fetchers.local_folder_fetcher import LocalFolderFetcher
from src.document_processors.processor_pipeline import ProcessorPipeline
from src.categorizers.hybrid_categorizer import HybridCategorizer
from src.data_entry.mijngeldzaken_handler import MijngeldzakenHandler
from src.data_entry.waveapps_business_handler import WaveappsBusinessHandler
from src.data_entry.waveapps_personal_handler import WaveappsPersonalHandler
from src.data_entry.safe_posting import SafePostingService
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
from src.storage.database import Database
from src.document_handling.duplicate_detector import DuplicateDetector
from src.workflow.safety_engine import SafetyEngine


class WorkflowController:
    """Orchestrates the automated bookkeeping workflow with safety gates."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = AppLogger(log_file=self.config.get("log_file")).get_logger()
        self.database = Database(config)
        self.duplicate_detector = DuplicateDetector(config)
        self.safety_engine = SafetyEngine(config)
        self.safe_posting = SafePostingService(config)
        self.live_posting_enabled = bool(self.config.get("live_posting_enabled", False))

        self.fetchers = self._build_enabled_fetchers(config)
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

    def _build_enabled_fetchers(self, config: Dict[str, Any]):
        enabled_sources = config.get("enabled_fetchers", "local_folder")
        if isinstance(enabled_sources, str):
            enabled_sources = [source.strip() for source in enabled_sources.split(",") if source.strip()]

        fetcher_factories = {
            "local_folder": LocalFolderFetcher,
            "gmail": GmailFetcher,
            "drive": DriveFetcher,
            "freshdesk": FreshdeskFetcher,
            "photos": PhotosFetcher,
        }
        fetchers = {}
        for source in enabled_sources:
            factory = fetcher_factories.get(source)
            if not factory:
                self.logger.warning("Unknown fetcher configured: %s", source)
                continue
            try:
                fetchers[source] = factory(config)
            except Exception as exc:
                self.logger.error("Could not initialize %s fetcher: %s", source, exc)
                self.database.add_manual_review_item(None, f"fetcher_init_failed_{source}", str(exc), severity="high")
        return fetchers

    def run_workflow(self):
        self.logger.info("Starting automated bookkeeping workflow...")
        all_documents = self._fetch_and_persist_documents()
        if not all_documents:
            self.logger.info("No new documents to process. Workflow finished.")
            return

        processed_documents = []
        for doc in all_documents:
            processed = self._process_document(doc)
            if processed:
                processed_documents.append(processed)

        for processed in processed_documents:
            categorized = self._categorize_document(processed)
            if not categorized:
                continue
            duplicate_clear = self._check_duplicate(categorized)
            if not duplicate_clear:
                continue
            validated = self._validate_and_budget(categorized)
            if not validated:
                continue
            routed = self._route_document(validated)
            if not routed:
                continue
            self._create_dry_run_or_post(routed)

        self._run_reconciliation(processed_documents)
        self._run_backup()
        self.logger.info("Automated bookkeeping workflow finished.")

    def _fetch_and_persist_documents(self) -> List[Dict[str, Any]]:
        all_documents: List[Dict[str, Any]] = []
        for source, fetcher in self.fetchers.items():
            try:
                self.logger.info("Fetching documents from %s...", source)
                documents = fetcher.fetch_documents()
                for doc in documents:
                    self.database.upsert_document(doc, state="received")
                    current = self.database.fetch_one("SELECT current_state FROM documents WHERE id = ?", (doc["id"],))
                    if current and current.get("current_state") == "received":
                        self.database.set_document_state(doc["id"], "stored", "Document fetched and stored")
                all_documents.extend(documents)
                self.logger.info("Fetched %s documents from %s.", len(documents), source)
            except Exception as exc:
                self.logger.error("Error fetching from %s: %s", source, exc)
                self.error_recovery.handle_error(exc, f"fetch_{source}")
                self.database.add_manual_review_item(None, f"fetch_{source}", str(exc), severity="high")
        return all_documents

    def _process_document(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        document_id = doc.get("id")
        original_filename = doc.get("original_filename", "unknown")
        try:
            self._safe_state(document_id, "ocr_pending", "Starting OCR/document processing")
            self.logger.info("Processing document: %s", original_filename)
            processed_data = self.processor_pipeline.process_document(doc["local_path"])
            processed_data["document_id"] = document_id
            processed_data["source_document"] = doc
            self._persist_ocr_and_fields(processed_data)
            self._safe_state(document_id, "ocr_completed", "OCR/document processing completed")
            self._safe_state(document_id, "extraction_pending", "Starting extraction review")
            self._safe_state(document_id, "extraction_completed", "Initial extraction completed")

            safety_result = self.safety_engine.evaluate_extraction(processed_data)
            processed_data["extraction_safety_result"] = safety_result
            if safety_result["decision"] == "manual_review":
                self._require_manual_review(document_id, "extraction_safety_block", str(safety_result))
                return None
            return processed_data
        except Exception as exc:
            self.logger.error("Error processing %s: %s", original_filename, exc)
            self.error_recovery.handle_error(exc, f"process_{document_id}", document_id=document_id)
            self._safe_state(document_id, "ocr_failed", str(exc))
            self._require_manual_review(document_id, "processing_failed", str(exc))
            return None

    def _persist_ocr_and_fields(self, processed_data: Dict[str, Any]) -> None:
        document_id = processed_data.get("document_id")
        now = self.database.now()
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO ocr_results (document_id, ocr_engine, language, ocr_text, confidence_score, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    document_id,
                    self.config.get("primary_ocr_method", "unknown"),
                    processed_data.get("language"),
                    processed_data.get("ocr_text", ""),
                    processed_data.get("ocr_confidence"),
                    now,
                ),
            )
            for field_name, field_value in processed_data.get("extracted_data", {}).items():
                if isinstance(field_value, (list, dict)):
                    field_value = self.database.json_dumps(field_value)
                connection.execute(
                    "INSERT INTO extracted_fields (document_id, field_name, field_value, confidence_score, source, requires_review, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        document_id,
                        field_name,
                        str(field_value) if field_value is not None else None,
                        processed_data.get("field_confidences", {}).get(field_name),
                        "processor_pipeline",
                        0,
                        now,
                    ),
                )

    def _categorize_document(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        document_id = processed_data.get("document_id")
        try:
            self._safe_state(document_id, "vendor_matching_pending", "Starting vendor/category matching")
            self.logger.info("Categorizing document: %s", document_id)
            category_result = self.categorizer.categorize(processed_data)
            processed_data.update(category_result)
            if category_result.get("category") in {None, "Uncategorized", "Manual Review"}:
                self._safe_state(document_id, "category_uncertain", "Categorization did not produce a safe category")
                self._require_manual_review(document_id, "category_uncertain", str(category_result))
                return None
            self._safe_state(document_id, "vendor_matched", "Vendor/category matching completed")
            self._safe_state(document_id, "categorization_pending", "Preparing category decision")
            self._safe_state(document_id, "categorized", f"Category: {category_result.get('category')}")
            return processed_data
        except Exception as exc:
            self.logger.error("Error categorizing %s: %s", document_id, exc)
            self.error_recovery.handle_error(exc, f"categorize_{document_id}", document_id=document_id)
            self._require_manual_review(document_id, "categorization_failed", str(exc))
            return None

    def _check_duplicate(self, doc_data: Dict[str, Any]) -> bool:
        document_id = doc_data.get("document_id")
        self._safe_state(document_id, "duplicate_check_pending", "Checking duplicate fingerprints")
        existing = self.database.fetch_all("SELECT document_id, fingerprint AS duplicate_fingerprint FROM duplicate_fingerprints WHERE document_id != ?", (document_id,))
        duplicate_result = self.duplicate_detector.is_duplicate(doc_data, existing)
        doc_data["duplicate_result"] = duplicate_result
        if duplicate_result.get("is_duplicate"):
            self._safe_state(document_id, "suspected_duplicate", str(duplicate_result))
            self._require_manual_review(document_id, "suspected_duplicate", str(duplicate_result), severity="high")
            return False

        fingerprint = duplicate_result.get("duplicate_fingerprint") or self.duplicate_detector.build_fingerprint(doc_data)
        with self.database.connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO duplicate_fingerprints (fingerprint, document_id, created_at) VALUES (?, ?, ?)",
                (fingerprint, document_id, self.database.now()),
            )
        self._safe_state(document_id, "duplicate_clear", "No duplicate detected")
        return True

    def _validate_and_budget(self, doc_data: Dict[str, Any]) -> Dict[str, Any]:
        document_id = doc_data.get("document_id")
        try:
            self._safe_state(document_id, "validation_pending", "Starting validation and budget checks")
            validation_result = self.validation_manager.validate_receipt(doc_data)
            if not validation_result.get("is_valid"):
                reason = validation_result.get("reason", "Validation failed")
                self._safe_state(document_id, "validation_failed", reason)
                self._require_manual_review(document_id, "validation_failed", reason)
                return None

            budget_check_result = self.budget_manager.check_budget(doc_data)
            if not budget_check_result.get("is_within_budget", True):
                message = budget_check_result.get("message", "Budget check failed")
                self._require_manual_review(document_id, "budget_exceeded", message)
                return None

            self._safe_state(document_id, "validated", "Validation and budget checks passed")
            return doc_data
        except Exception as exc:
            self.logger.error("Error during validation/budget check for %s: %s", document_id, exc)
            self.error_recovery.handle_error(exc, f"validate_budget_{document_id}", document_id=document_id)
            self._require_manual_review(document_id, "validation_budget_error", str(exc))
            return None

    def _route_document(self, doc_data: Dict[str, Any]) -> Dict[str, Any]:
        document_id = doc_data.get("document_id")
        self._safe_state(document_id, "routing_pending", "Resolving bookkeeping route")
        route_result = self.router.route(doc_data)
        doc_data.update(route_result)
        if not route_result.get("target_system"):
            self._require_manual_review(document_id, "no_target_system", str(route_result))
            return None
        self._safe_state(document_id, "routed", str(route_result))
        return doc_data

    def _create_dry_run_or_post(self, doc_data: Dict[str, Any]) -> None:
        document_id = doc_data.get("document_id")
        target_system = doc_data.get("target_system")
        target_account = doc_data.get("target_account")
        self._safe_state(document_id, "dry_run_pending", "Creating dry-run posting payload")
        dry_run = self.safe_posting.create_dry_run(doc_data, target_system, target_account)
        self._safe_state(document_id, "dry_run_completed", str(dry_run))

        safety_result = dry_run.get("safety_result", {})
        if not safety_result.get("may_post"):
            self._require_manual_review(document_id, "posting_not_safe", str(safety_result), severity="high")
            return

        if not self.live_posting_enabled:
            self._require_manual_review(document_id, "approval_required_before_live_posting", "Dry-run created; live posting is disabled by default.")
            return

        self._safe_state(document_id, "approved_for_posting", "Safety checks passed and live posting enabled")
        self._safe_state(document_id, "posting_pending", f"Posting to {target_system}")
        handler = self.data_entry_handlers[target_system]
        entry_result = handler.enter_data(doc_data)
        if entry_result.get("status") == "success":
            self._safe_state(document_id, "posted", str(entry_result))
            self.learning_manager.provide_feedback(document_id, doc_data.get("category"), True)
        else:
            message = entry_result.get("message", "Data entry failed")
            self._safe_state(document_id, "posting_failed", message)
            self._require_manual_review(document_id, "data_entry_failed", message, severity="high")

    def _run_reconciliation(self, processed_documents: Iterable[Dict[str, Any]]) -> None:
        try:
            self.logger.info("Starting automated reconciliation...")
            bank_transactions = self.banking_api.fetch_transactions(self.config.get("banking_api_credentials"))
            reconciliation_results = self.reconciliation_manager.reconcile(bank_transactions, list(processed_documents))
            for result in reconciliation_results:
                if not result.get("matched"):
                    review_id = result.get("id") or result.get("transaction", {}).get("id") or result.get("bank_transaction", {}).get("id") or "unknown_reconciliation_item"
                    self.logger.warning("Unmatched transaction/document: %s", result)
                    self.database.add_manual_review_item(review_id, "unmatched_reconciliation", str(result))
        except Exception as exc:
            self.logger.error("Error during reconciliation: %s", exc)
            self.error_recovery.handle_error(exc, "reconciliation_workflow")

    def _run_backup(self) -> None:
        try:
            self.logger.info("Performing backup...")
            self.backup_manager.perform_backup(self.config.get("backup_paths"), self.config.get("backup_config"))
            self.logger.info("Backup completed.")
        except Exception as exc:
            self.logger.error("Error during backup: %s", exc)
            self.error_recovery.handle_error(exc, "backup_workflow")

    def _require_manual_review(self, document_id: str, reason: str, details: str = "", severity: str = "normal") -> None:
        self.database.add_manual_review_item(document_id, reason, details, severity=severity)
        self._safe_state(document_id, "manual_review_required", reason)
        self.manual_review_interface.add_to_review_queue(document_id, reason, details)

    def _safe_state(self, document_id: str, new_state: str, reason: str = "") -> None:
        if not document_id:
            return
        try:
            self.database.set_document_state(document_id, new_state, reason)
        except Exception as exc:
            self.logger.warning("Could not transition document %s to %s: %s", document_id, new_state, exc)
            self.database.add_audit_log("document", document_id, "state_transition_warning", None, {"attempted_state": new_state}, str(exc))
