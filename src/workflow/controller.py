from typing import Dict, Any, List, Optional
import hashlib
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
from src.routing.bookkeeping_router import BookkeepingRouter
from src.operations.operations_client import OperationsClient
from src.document_handling import DuplicateDetector, DocumentPriorityResolver, DocumentVersionControl
from src.document_handling.source_identity import source_document_id
from src.workflow.checkpoint_store import WorkflowCheckpointStore

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
        self.bookkeeping_router = BookkeepingRouter(config)
        self.operations_client = OperationsClient(config, self.logger)
        self.duplicate_detector = DuplicateDetector(config)
        self.priority_resolver = DocumentPriorityResolver(config)
        self.version_control = DocumentVersionControl(config)
        self.checkpoint_store = WorkflowCheckpointStore(config)
        self._review_document_ids = set()
        self.categorization_review_confidence_threshold = float(
            self.config.get(
                "categorization_review_confidence_threshold",
                self.config.get(
                    "operations_categorization_review_confidence_threshold",
                    self.config.get("ml_confidence_threshold", 0.7),
                ),
            )
        )

    @staticmethod
    def _document_key(document: Dict[str, Any]) -> str:
        return str(
            document.get("id")
            or document.get("original_filename")
            or document.get("local_path")
            or "unknown"
        )

    @staticmethod
    def _normalize_fetched_document(
        source: str,
        document: Dict[str, Any],
        position: int,
    ) -> Dict[str, Any]:
        normalized = dict(document) if isinstance(document, dict) else {}
        identity = source_document_id(normalized)
        normalized["id"] = str(
            normalized.get("id")
            or identity
            or f"unidentified:{source}:{position}"
        )
        normalized["original_filename"] = str(
            normalized.get("original_filename")
            or normalized.get("filename")
            or (
                os.path.basename(str(normalized["local_path"]))
                if normalized.get("local_path")
                else ""
            )
            or f"{source}-document-{position + 1}"
        )
        normalized["_source"] = source
        return normalized

    @staticmethod
    def _operations_target(target_system: Optional[str]) -> str:
        allowed_targets = {"mijngeldzaken", "waveapps_business", "waveapps_personal", "manual_review", "none"}
        if not target_system:
            return "none"
        return target_system if target_system in allowed_targets else "none"

    @staticmethod
    def _external_entry_id(entry_result: Dict[str, Any]) -> Optional[str]:
        for key in ("external_id", "id", "entry_id", "transaction_id"):
            if entry_result.get(key):
                return str(entry_result[key])
        return None

    def _queue_manual_review(
        self,
        document_id: str,
        reason: str,
        details: str = "",
        operations_document_id: Optional[int] = None,
    ):
        self.manual_review_interface.add_to_review_queue(document_id, reason, details)
        self._review_document_ids.add(str(document_id))
        self.operations_client.create_review_item(operations_document_id, reason, details)
        self.operations_client.record_audit_event(
            "workflow.review_item.queued",
            "bookkeeping_document",
            str(operations_document_id or document_id),
            {
                "documentId": document_id,
                "reason": reason,
                "details": details,
            },
        )

    def _record_workflow_error(
        self,
        operation: str,
        error: Exception,
        workflow_run_id: Optional[int] = None,
        document_id: Optional[str] = None,
        operations_document_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        entity_type = "bookkeeping_document" if operations_document_id or document_id else "workflow_run"
        entity_id = operations_document_id or document_id or workflow_run_id
        self.operations_client.record_audit_event(
            "workflow.error",
            entity_type,
            str(entity_id) if entity_id is not None else None,
            {
                "operation": operation,
                "error": str(error),
                **(details or {}),
            },
        )

    def _mark_source_document(self, doc_data: Dict[str, Any], status: str):
        source_document = doc_data.get("_source_document", {})
        if not source_document:
            return
        source = source_document.get("_source", "unknown")
        self.checkpoint_store.mark_source_document(source, source_document, status)

    def _mark_fetched_document(self, document: Dict[str, Any], status: str):
        self.checkpoint_store.mark_source_document(
            document.get("_source", "unknown"),
            document,
            status,
        )

    @staticmethod
    def _confidence_score(document_data: Dict[str, Any]) -> float:
        try:
            return float(document_data.get("confidence_score", 0.0) or 0.0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _bank_transaction_id(transaction: Dict[str, Any]) -> str:
        for key in ("id", "transaction_id", "bank_transaction_id", "reference"):
            if transaction.get(key):
                return str(transaction[key])

        source = "|".join(
            str(transaction.get(key, ""))
            for key in ("date", "amount", "description", "counterparty", "iban")
        )
        return hashlib.sha256(source.encode("utf-8")).hexdigest()[:32]

    @staticmethod
    def _amount_difference(bank_transaction: Dict[str, Any], document: Optional[Dict[str, Any]]) -> Optional[float]:
        if not document:
            return None
        try:
            bank_amount = float(str(bank_transaction.get("amount")).replace(",", "."))
            doc_amount = float(str(document.get("extracted_data", {}).get("total_amount")).replace(",", "."))
            return round(bank_amount - doc_amount, 2)
        except (TypeError, ValueError):
            return None

    def _record_reconciliation_result(
        self,
        result: Dict[str, Any],
        workflow_run_id: Optional[int],
    ):
        result_type = result.get("type")
        bank_transaction = result.get("bank_transaction") or {}
        document = result.get("document")
        operations_document_id = document.get("_operations_document_id") if document else None
        bank_transaction_id = self._bank_transaction_id(bank_transaction)

        if result.get("matched"):
            self.operations_client.create_reconciliation_match(
                bank_transaction_id,
                "matched",
                document_id=operations_document_id,
                confidence_score=result.get("confidence_score", 1.0),
                amount_difference=result.get(
                    "amount_difference",
                    self._amount_difference(bank_transaction, document),
                ),
                metadata={"workflowRunId": workflow_run_id, "result": result},
            )
            self.operations_client.update_document(
                operations_document_id,
                document,
                processing_status="reconciled",
                metadata={"reconciliation": {"bankTransactionId": bank_transaction_id}},
            )
            self._mark_source_document(document, "reconciled")
            return

        if result_type == "unmatched_bank_transaction":
            message = "Possible missing receipt for unmatched bank transaction."
            self.operations_client.create_reconciliation_match(
                bank_transaction_id,
                "unmatched",
                metadata={"workflowRunId": workflow_run_id, "result": result},
            )
            self._queue_manual_review(bank_transaction_id, "missing_receipt", message)
            return

        if result_type == "unmatched_document" and document:
            document_id = document.get("document_id", "unknown")
            if not bank_transaction:
                bank_transaction_id = f"unmatched-document-{document_id}"
            message = "Document could not be matched to a bank transaction."
            self.operations_client.create_reconciliation_match(
                bank_transaction_id,
                "review",
                document_id=operations_document_id,
                metadata={"workflowRunId": workflow_run_id, "result": result},
            )
            self.operations_client.update_document(
                operations_document_id,
                document,
                processing_status="needs_review",
                metadata={"reconciliation": {"status": "unmatched_document"}},
            )
            self._queue_manual_review(document_id, "unmatched_reconciliation", message, operations_document_id)
            self._mark_source_document(document, "needs_review_unmatched_reconciliation")
            return

        self.operations_client.create_reconciliation_match(
            bank_transaction_id,
            "review",
            document_id=operations_document_id,
            metadata={"workflowRunId": workflow_run_id, "result": result},
        )

    def _skip_document(
        self,
        doc_data: Dict[str, Any],
        reason: str,
        message: str,
        workflow_run_id: Optional[int],
        metadata: Optional[Dict[str, Any]] = None,
    ):
        document_id = doc_data.get("document_id", "unknown")
        operations_document_id = doc_data.get("_operations_document_id")
        self.logger.info(f"Skipping document {document_id}: {message}")
        self.operations_client.create_routing_attempt(
            operations_document_id,
            "none",
            "skipped",
            workflow_run_id=workflow_run_id,
            message=message,
            metadata=metadata or {"reason": reason},
        )
        self.operations_client.update_document(
            operations_document_id,
            doc_data,
            processing_status="archived",
            duplicate_fingerprint=doc_data.get("duplicate_fingerprint"),
            duplicate_of_document_id=doc_data.get("duplicate_of_document_id"),
            metadata=metadata or {"reason": reason},
        )
        self.operations_client.record_audit_event(
            "workflow.document.skipped",
            "bookkeeping_document",
            str(operations_document_id or document_id),
            {
                "documentId": document_id,
                "reason": reason,
                "message": message,
                "metadata": metadata or {},
            },
        )

    def run_workflow(self):
        if not self.checkpoint_store.acquire_run_lock():
            self.logger.warning("Workflow execution skipped because another run holds the lock.")
            self.operations_client.record_audit_event(
                "workflow.run.skipped_already_running",
                "workflow_run",
                details={"lockPath": self.checkpoint_store.run_lock_path},
            )
            return

        try:
            return self._run_workflow()
        finally:
            if not self.checkpoint_store.release_run_lock():
                self.logger.error("Workflow run lock could not be released safely.")
                self.operations_client.record_audit_event(
                    "workflow.run_lock.release_failed",
                    "workflow_run",
                    details={"lockPath": self.checkpoint_store.run_lock_path},
                )

    def _run_workflow(self):
        self.logger.info("Starting automated bookkeeping workflow...")
        self._review_document_ids = set()
        documents_processed = 0
        workflow_had_failures = False
        operations_documents = {}
        workflow_run_id = self.operations_client.create_workflow_run(
            self.config.get("workflow_trigger_source", "manual"),
            metadata={"fetchers": list(self.fetchers.keys())},
        )
        self.operations_client.record_audit_event(
            "workflow.run.started",
            "workflow_run",
            str(workflow_run_id) if workflow_run_id is not None else None,
            {"triggerSource": self.config.get("workflow_trigger_source", "manual")},
        )

        if self.checkpoint_store.fail_closed and self.checkpoint_store.load_error:
            checkpoint_error = RuntimeError(self.checkpoint_store.load_error)
            self.logger.error(f"Workflow blocked by invalid checkpoint state: {checkpoint_error}")
            self._record_workflow_error(
                "checkpoint_load",
                checkpoint_error,
                workflow_run_id=workflow_run_id,
                details={"checkpointPath": self.checkpoint_store.path},
            )
            self.operations_client.update_workflow_run(
                workflow_run_id,
                status="failed",
                documentsImported=0,
                documentsProcessed=0,
                documentsNeedingReview=0,
            )
            self.operations_client.record_audit_event(
                "workflow.run.completed",
                "workflow_run",
                str(workflow_run_id) if workflow_run_id is not None else None,
                {
                    "status": "failed",
                    "documentsImported": 0,
                    "documentsProcessed": 0,
                    "documentsNeedingReview": 0,
                },
            )
            return
        
        # 1. Fetch Documents
        all_documents = []
        for source, fetcher in self.fetchers.items():
            try:
                self.logger.info(f"Fetching documents from {source}...")
                fetched_documents = fetcher.fetch_documents()
                normalized_documents = [
                    self._normalize_fetched_document(source, document, position)
                    for position, document in enumerate(fetched_documents)
                ]
                documents = self.checkpoint_store.filter_new_documents(source, normalized_documents)
                skipped_count = len(fetched_documents) - len(documents)
                if skipped_count:
                    self.logger.info(f"Skipped {skipped_count} previously completed documents from {source}.")
                    self.operations_client.record_audit_event(
                        "workflow.source_documents.skipped_previously_completed",
                        "workflow_run",
                        str(workflow_run_id) if workflow_run_id is not None else None,
                        {"source": source, "skippedCount": skipped_count},
                    )
                for doc in documents:
                    operations_document_id = self.operations_client.register_document(
                        source,
                        doc,
                        processing_status="imported",
                    )
                    if operations_document_id:
                        operations_documents[self._document_key(doc)] = operations_document_id
                all_documents.extend(documents)
                self.logger.info(f"Fetched {len(documents)} documents from {source}.")
            except Exception as e:
                workflow_had_failures = True
                self.logger.error(f"Error fetching from {source}: {e}")
                self.error_recovery.handle_error(e, f"fetch_{source}")
                self._record_workflow_error(
                    f"fetch_{source}",
                    e,
                    workflow_run_id=workflow_run_id,
                    details={"source": source},
                )

        if not all_documents:
            final_status = "failed" if workflow_had_failures else "completed"
            self.logger.info("No new documents to process. Workflow finished.")
            self.operations_client.update_workflow_run(
                workflow_run_id,
                status=final_status,
                documentsImported=0,
                documentsProcessed=0,
                documentsNeedingReview=0,
            )
            self.operations_client.record_audit_event(
                "workflow.run.completed",
                "workflow_run",
                str(workflow_run_id) if workflow_run_id is not None else None,
                {
                    "status": final_status,
                    "documentsImported": 0,
                    "documentsProcessed": 0,
                    "documentsNeedingReview": 0,
                },
            )
            return

        # 2. Process Documents
        processed_documents = []
        for doc in all_documents:
            document_key = self._document_key(doc)
            operations_document_id = operations_documents.get(document_key)
            document_id = str(doc["id"])
            document_name = doc["original_filename"]
            try:
                self.logger.info(f"Processing document: {document_name}")
                if not doc.get("local_path"):
                    raise ValueError("Fetched document has no local file path.")
                self.operations_client.update_document(operations_document_id, processing_status="processing")
                processed_data = self.processor_pipeline.process_document(doc["local_path"])
                processed_data["document_id"] = document_id
                processed_data["_source_document"] = doc
                processed_data["_operations_document_id"] = operations_document_id
                processed_data["document_type"] = self.priority_resolver.classify_document({
                    **processed_data,
                    "original_filename": doc.get("original_filename"),
                    "filename": doc.get("filename"),
                })
                processed_data["document_priority_score"] = self.priority_resolver.priority_score(processed_data)
                processed_documents.append(processed_data)
                self.version_control.register_version(
                    document_id,
                    doc["local_path"],
                    {
                        "source": doc.get("_source"),
                        "original_filename": doc.get("original_filename"),
                        "document_type": processed_data["document_type"],
                        "operations_document_id": operations_document_id,
                    },
                )
                documents_processed += 1
                self.operations_client.update_document(
                    operations_document_id,
                    processed_data,
                    processing_status="extracted",
                )
            except Exception as e:
                self.logger.error(f"Error processing {document_name}: {e}")
                self.error_recovery.handle_error(e, f"process_{document_id}")
                self.operations_client.update_document(operations_document_id, processing_status="failed")
                self._record_workflow_error(
                    f"process_{document_id}",
                    e,
                    workflow_run_id=workflow_run_id,
                    document_id=document_id,
                    operations_document_id=operations_document_id,
                )
                self._queue_manual_review(document_id, "processing_failed", str(e), operations_document_id)
                self._mark_fetched_document(doc, "needs_review_processing_failed")

        preferred_documents = self.priority_resolver.select_preferred_documents(processed_documents)
        preferred_ids = {doc.get("document_id") for doc in preferred_documents}
        eligible_documents = []
        existing_documents = list(self.config.get("known_documents", self.config.get("existing_documents", [])))
        existing_documents.extend(self.checkpoint_store.known_documents())

        for doc_data in processed_documents:
            document_id = doc_data["document_id"]
            if document_id not in preferred_ids:
                self._skip_document(
                    doc_data,
                    "lower_priority_document",
                    "A higher-priority document exists for the same order.",
                    workflow_run_id,
                    {
                        "document_type": doc_data.get("document_type"),
                        "document_priority_score": doc_data.get("document_priority_score"),
                    },
                )
                self.checkpoint_store.mark_source_document(doc_data.get("_source_document", {}).get("_source", "unknown"), doc_data.get("_source_document", {}), "skipped_lower_priority")
                continue

            doc_data["duplicate_fingerprint"] = self.duplicate_detector.build_fingerprint(doc_data)
            duplicate_result = self.duplicate_detector.is_duplicate(doc_data, existing_documents)
            if duplicate_result["is_duplicate"]:
                matched_document_id = duplicate_result.get("matched_document_id")
                doc_data["duplicate_of_document_id"] = matched_document_id if isinstance(matched_document_id, int) else None
                self._skip_document(
                    doc_data,
                    "duplicate_document",
                    f"Duplicate document detected: {duplicate_result['reason']}.",
                    workflow_run_id,
                    {
                        "duplicate": duplicate_result,
                        "duplicate_fingerprint": doc_data["duplicate_fingerprint"],
                    },
                )
                self.checkpoint_store.mark_source_document(doc_data.get("_source_document", {}).get("_source", "unknown"), doc_data.get("_source_document", {}), "skipped_duplicate")
                continue

            eligible_documents.append(doc_data)
            existing_documents.append(doc_data)

        # 3. Categorize Documents
        categorized_documents = []
        for doc_data in eligible_documents:
            operations_document_id = doc_data.get("_operations_document_id")
            try:
                self.logger.info(f"Categorizing document: {doc_data['document_id']}")
                category_result = self.categorizer.categorize(doc_data)
                doc_data.update(category_result) # Add category and confidence
                confidence_score = self._confidence_score(doc_data)
                if confidence_score < self.categorization_review_confidence_threshold:
                    document_id = doc_data["document_id"]
                    message = (
                        "Categorization confidence "
                        f"{confidence_score:.2f} is below review threshold "
                        f"{self.categorization_review_confidence_threshold:.2f}."
                    )
                    self.logger.warning(f"Low confidence categorization for {document_id}: {message}")
                    self.operations_client.update_document(
                        operations_document_id,
                        doc_data,
                        processing_status="needs_review",
                    )
                    self.operations_client.create_routing_attempt(
                        operations_document_id,
                        "manual_review",
                        "requires_review",
                        workflow_run_id=workflow_run_id,
                        message=message,
                        metadata={
                            "reason": "low_categorization_confidence",
                            "category": doc_data.get("category"),
                            "confidenceScore": confidence_score,
                            "threshold": self.categorization_review_confidence_threshold,
                        },
                    )
                    self._queue_manual_review(
                        document_id,
                        "low_categorization_confidence",
                        message,
                        operations_document_id,
                    )
                    self._mark_source_document(doc_data, "needs_review_low_confidence")
                    continue
                categorized_documents.append(doc_data)
                self.operations_client.update_document(
                    operations_document_id,
                    doc_data,
                    processing_status="extracted",
                )
            except Exception as e:
                document_id = doc_data["document_id"]
                self.logger.error(f"Error categorizing {document_id}: {e}")
                self.error_recovery.handle_error(e, f"categorize_{document_id}")
                self.operations_client.update_document(operations_document_id, doc_data, processing_status="needs_review")
                self._record_workflow_error(
                    f"categorize_{document_id}",
                    e,
                    workflow_run_id=workflow_run_id,
                    document_id=str(document_id),
                    operations_document_id=operations_document_id,
                )
                self._queue_manual_review(document_id, "categorization_failed", str(e), operations_document_id)
                self._mark_source_document(doc_data, "needs_review_categorization_failed")

        # 4. Validate and Budget Check
        validated_and_budgeted_docs = []
        budget_review_document_ids = set()
        for doc_data in categorized_documents:
            operations_document_id = doc_data.get("_operations_document_id")
            try:
                document_id = doc_data["document_id"]
                self.logger.info(f"Validating and budget checking document: {document_id}")
                validation_result = self.validation_manager.validate_receipt(doc_data)
                if not validation_result["is_valid"]:
                    self.logger.warning(f"Validation failed for {document_id}: {validation_result['reason']}")
                    self.operations_client.update_document(operations_document_id, doc_data, processing_status="needs_review")
                    self._queue_manual_review(
                        document_id,
                        "validation_failed",
                        validation_result["reason"],
                        operations_document_id,
                    )
                    self._mark_source_document(doc_data, "needs_review_validation_failed")
                    continue # Skip data entry for invalid documents
                self.operations_client.update_document(operations_document_id, doc_data, processing_status="validated")
                
                budget_check_result = self.budget_manager.check_budget(doc_data)
                if not budget_check_result["is_within_budget"]:
                    self.logger.warning(f"Budget exceeded for {document_id}: {budget_check_result['message']}")
                    self._queue_manual_review(
                        document_id,
                        "budget_exceeded",
                        budget_check_result["message"],
                        operations_document_id,
                    )
                    budget_review_document_ids.add(document_id)
                    # Decide whether to proceed with data entry or not based on config

                validated_and_budgeted_docs.append(doc_data)
            except Exception as e:
                document_id = doc_data["document_id"]
                self.logger.error(f"Error during validation/budget check for {document_id}: {e}")
                self.error_recovery.handle_error(e, f"validate_budget_{document_id}")
                self.operations_client.update_document(operations_document_id, doc_data, processing_status="needs_review")
                self._record_workflow_error(
                    f"validate_budget_{document_id}",
                    e,
                    workflow_run_id=workflow_run_id,
                    document_id=str(document_id),
                    operations_document_id=operations_document_id,
                )
                self._queue_manual_review(document_id, "validation_budget_error", str(e), operations_document_id)
                self._mark_source_document(doc_data, "needs_review_validation_budget_error")

        # 5. Data Entry
        routed_documents = []
        for doc_data in validated_and_budgeted_docs:
            operations_document_id = doc_data.get("_operations_document_id")
            document_id = doc_data["document_id"]
            try:
                route_result = self.bookkeeping_router.route(doc_data)
                if not isinstance(route_result, dict):
                    raise ValueError("Bookkeeping router returned an invalid result.")
                target_system = route_result.get("target_system")
            except Exception as e:
                self.logger.error(f"Error routing {document_id}: {e}")
                self.error_recovery.handle_error(e, f"route_{document_id}")
                self._record_workflow_error(
                    f"route_{document_id}",
                    e,
                    workflow_run_id=workflow_run_id,
                    document_id=str(document_id),
                    operations_document_id=operations_document_id,
                )
                self.operations_client.update_document(
                    operations_document_id,
                    doc_data,
                    processing_status="needs_review",
                )
                self.operations_client.create_routing_attempt(
                    operations_document_id,
                    "manual_review",
                    "requires_review",
                    workflow_run_id=workflow_run_id,
                    message=str(e),
                    metadata={"reason": "routing_failed"},
                )
                self._queue_manual_review(
                    document_id,
                    "routing_failed",
                    str(e),
                    operations_document_id,
                )
                self._mark_source_document(doc_data, "needs_review_routing_failed")
                continue
            
            if target_system:
                try:
                    self.logger.info(f"Entering data for {document_id} into {target_system}...")
                    handler = self.data_entry_handlers[target_system]
                    entry_result = handler.enter_data(doc_data)
                    if entry_result["status"] == "success":
                        self.logger.info(f"Successfully entered {document_id} into {target_system}.")
                        self.operations_client.create_routing_attempt(
                            operations_document_id,
                            self._operations_target(target_system),
                            "success",
                            workflow_run_id=workflow_run_id,
                            external_id=self._external_entry_id(entry_result),
                            metadata={"route": route_result},
                        )
                        self.operations_client.update_document(
                            operations_document_id,
                            doc_data,
                            processing_status="routed",
                        )
                        routed_documents.append(doc_data)
                        if document_id in budget_review_document_ids:
                            self._mark_source_document(doc_data, "needs_review_budget_exceeded")
                        else:
                            self.checkpoint_store.remember_processed_document(doc_data)
                            self._mark_source_document(doc_data, "processed")
                        # Trigger learning manager feedback
                        self.learning_manager.provide_feedback(document_id, doc_data["category"], True)
                        self.operations_client.record_audit_event(
                            "workflow.document.routed",
                            "bookkeeping_document",
                            str(operations_document_id or document_id),
                            {
                                "documentId": document_id,
                                "targetSystem": target_system,
                                "externalId": self._external_entry_id(entry_result),
                            },
                        )
                    else:
                        self.logger.warning(f"Failed to enter {document_id} into {target_system}: {entry_result['message']}")
                        if entry_result.get("status") in {"rate_limited", "quota_exhausted"}:
                            self.operations_client.create_routing_attempt(
                                operations_document_id,
                                self._operations_target(target_system),
                                "deferred",
                                workflow_run_id=workflow_run_id,
                                message=entry_result["message"],
                                metadata={"route": route_result, "entry_result": entry_result},
                            )
                            self.operations_client.update_document(
                                operations_document_id,
                                doc_data,
                                processing_status="deferred",
                            )
                            self.operations_client.record_audit_event(
                                "workflow.document.data_entry_deferred",
                                "bookkeeping_document",
                                str(operations_document_id or document_id),
                                {
                                    "documentId": document_id,
                                    "targetSystem": target_system,
                                    "providerStatus": entry_result.get("status"),
                                    "retryAfterSeconds": entry_result.get("retry_after_seconds"),
                                    "rateLimit": entry_result.get("rate_limit"),
                                },
                            )
                            self._mark_source_document(doc_data, "deferred_data_entry")
                            continue
                        route_status = "requires_review" if entry_result.get("requires_manual_review", False) else "failed"
                        self.operations_client.create_routing_attempt(
                            operations_document_id,
                            self._operations_target(target_system),
                            route_status,
                            workflow_run_id=workflow_run_id,
                            message=entry_result["message"],
                            metadata={"route": route_result, "entry_result": entry_result},
                        )
                        self.operations_client.update_document(
                            operations_document_id,
                            doc_data,
                            processing_status="needs_review" if route_status == "requires_review" else "failed",
                        )
                        entry_error = Exception(entry_result["message"])
                        self.error_recovery.handle_error(entry_error, f"data_entry_{document_id}")
                        self._record_workflow_error(
                            f"data_entry_{document_id}",
                            entry_error,
                            workflow_run_id=workflow_run_id,
                            document_id=str(document_id),
                            operations_document_id=operations_document_id,
                            details={"targetSystem": target_system, "routeStatus": route_status},
                        )
                        if entry_result.get("requires_manual_review", False):
                            self._queue_manual_review(
                                document_id,
                                "data_entry_failed",
                                entry_result["message"],
                                operations_document_id,
                            )
                            self._mark_source_document(doc_data, "needs_review_data_entry_failed")
                        else:
                            workflow_had_failures = True
                            self._mark_source_document(doc_data, "failed_data_entry")
                except Exception as e:
                    document_id = doc_data["document_id"]
                    self.logger.error(f"Error during data entry for {document_id} into {target_system}: {e}")
                    self.error_recovery.handle_error(e, f"data_entry_{document_id}")
                    self._record_workflow_error(
                        f"data_entry_{document_id}",
                        e,
                        workflow_run_id=workflow_run_id,
                        document_id=str(document_id),
                        operations_document_id=operations_document_id,
                        details={"targetSystem": target_system},
                    )
                    self.operations_client.create_routing_attempt(
                        operations_document_id,
                        self._operations_target(target_system),
                        "failed",
                        workflow_run_id=workflow_run_id,
                        message=str(e),
                        metadata={"route": route_result},
                    )
                    self.operations_client.update_document(operations_document_id, doc_data, processing_status="needs_review")
                    self._queue_manual_review(document_id, "data_entry_error", str(e), operations_document_id)
                    self._mark_source_document(doc_data, "needs_review_data_entry_error")
            else:
                category = doc_data["category"]
                self.logger.warning(f"No target system for category {category} for document {document_id}. Requires manual review.")
                self.operations_client.create_routing_attempt(
                    operations_document_id,
                    "none",
                    "requires_review",
                    workflow_run_id=workflow_run_id,
                    message=route_result["reason"],
                    metadata={"route": route_result},
                )
                self.operations_client.update_document(operations_document_id, doc_data, processing_status="needs_review")
                self._queue_manual_review(
                    document_id,
                    "no_target_system",
                    f"Category {category} has no defined target system.",
                    operations_document_id,
                )
                self._mark_source_document(doc_data, "needs_review_no_target_system")

        # 6. Reconciliation (after data entry, or as a separate scheduled task)
        try:
            self.logger.info("Starting automated reconciliation...")
            bank_transactions = self.banking_api.fetch_transactions(self.config.get("banking_api_credentials"))
            reconciliation_results = self.reconciliation_manager.reconcile(bank_transactions, routed_documents)
            for result in reconciliation_results:
                self._record_reconciliation_result(result, workflow_run_id)
                if not result["matched"]:
                    self.logger.warning(f"Unmatched transaction/document: {result}")
        except Exception as e:
            workflow_had_failures = True
            self.logger.error(f"Error during reconciliation: {e}")
            self.error_recovery.handle_error(e, "reconciliation_workflow")
            self._record_workflow_error(
                "reconciliation_workflow",
                e,
                workflow_run_id=workflow_run_id,
            )

        # 7. Backup
        try:
            self.logger.info("Performing backup...")
            self.backup_manager.perform_backup(self.config.get("backup_paths"), self.config.get("backup_config"))
            self.logger.info("Backup completed.")
        except Exception as e:
            workflow_had_failures = True
            self.logger.error(f"Error during backup: {e}")
            self.error_recovery.handle_error(e, "backup_workflow")
            self._record_workflow_error(
                "backup_workflow",
                e,
                workflow_run_id=workflow_run_id,
            )

        if not self.checkpoint_store.save():
            workflow_had_failures = True
            checkpoint_error = RuntimeError(
                self.checkpoint_store.last_save_error
                or "Workflow checkpoint state could not be persisted."
            )
            self.logger.error(f"Error saving workflow checkpoint: {checkpoint_error}")
            self._record_workflow_error(
                "checkpoint_save",
                checkpoint_error,
                workflow_run_id=workflow_run_id,
                details={"checkpointPath": self.checkpoint_store.path},
            )

        if workflow_had_failures:
            final_status = "failed"
        elif self._review_document_ids:
            final_status = "completed_with_review"
        else:
            final_status = "completed"
        self.operations_client.update_workflow_run(
            workflow_run_id,
            status=final_status,
            documentsImported=len(all_documents),
            documentsProcessed=documents_processed,
            documentsNeedingReview=len(self._review_document_ids),
        )
        self.operations_client.record_audit_event(
            "workflow.run.completed",
            "workflow_run",
            str(workflow_run_id) if workflow_run_id is not None else None,
            {
                "status": final_status,
                "documentsImported": len(all_documents),
                "documentsProcessed": documents_processed,
                "documentsNeedingReview": len(self._review_document_ids),
            },
        )
        self.logger.info("Automated bookkeeping workflow finished.")



