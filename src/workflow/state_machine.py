from typing import Dict, Iterable, Set


class InvalidStateTransition(ValueError):
    pass


class DocumentStateMachine:
    """Controls safe FAB document state transitions."""

    INITIAL_STATE = "received"

    TERMINAL_STATES = {
        "posted",
        "duplicate_confirmed",
        "reversed",
        "archived",
    }

    TRANSITIONS: Dict[str, Set[str]] = {
        "received": {"stored", "manual_review_required", "failed"},
        "stored": {"ocr_pending", "manual_review_required", "failed"},
        "ocr_pending": {"ocr_completed", "ocr_failed", "manual_review_required"},
        "ocr_completed": {"extraction_pending", "manual_review_required"},
        "ocr_failed": {"manual_review_required", "ocr_pending", "failed"},
        "extraction_pending": {"extraction_completed", "extraction_low_confidence", "manual_review_required", "failed"},
        "extraction_completed": {"vendor_matching_pending", "manual_review_required"},
        "extraction_low_confidence": {"manual_review_required"},
        "vendor_matching_pending": {"vendor_matched", "vendor_uncertain", "manual_review_required"},
        "vendor_matched": {"categorization_pending", "manual_review_required"},
        "vendor_uncertain": {"manual_review_required"},
        "categorization_pending": {"categorized", "category_uncertain", "manual_review_required"},
        "categorized": {"duplicate_check_pending", "manual_review_required"},
        "category_uncertain": {"manual_review_required"},
        "duplicate_check_pending": {"duplicate_clear", "suspected_duplicate", "duplicate_confirmed"},
        "duplicate_clear": {"validation_pending", "manual_review_required"},
        "suspected_duplicate": {"manual_review_required", "duplicate_confirmed", "duplicate_clear"},
        "validation_pending": {"validated", "validation_failed", "manual_review_required"},
        "validated": {"routing_pending", "manual_review_required"},
        "validation_failed": {"manual_review_required"},
        "routing_pending": {"routed", "manual_review_required"},
        "routed": {"dry_run_pending", "manual_review_required"},
        "dry_run_pending": {"dry_run_completed", "posting_failed", "manual_review_required"},
        "dry_run_completed": {"approved_for_posting", "manual_review_required"},
        "approved_for_posting": {"posting_pending", "manual_review_required"},
        "posting_pending": {"posted", "posting_failed", "manual_review_required"},
        "posting_failed": {"manual_review_required", "dry_run_pending"},
        "posted": {"reconciliation_pending", "reversed", "archived"},
        "reconciliation_pending": {"reconciled", "reconciliation_conflict", "missing_receipt", "manual_review_required"},
        "reconciled": {"archived", "reversed"},
        "reconciliation_conflict": {"manual_review_required", "exception_approved"},
        "missing_receipt": {"manual_review_required", "exception_approved"},
        "exception_approved": {"reconciled", "archived"},
        "manual_review_required": {"approved_for_posting", "ocr_pending", "duplicate_clear", "exception_approved", "failed", "archived"},
        "failed": {"manual_review_required", "archived"},
        "duplicate_confirmed": {"archived"},
        "reversed": {"archived"},
        "archived": set(),
    }

    @classmethod
    def can_transition(cls, current_state: str, next_state: str) -> bool:
        return next_state in cls.TRANSITIONS.get(current_state, set())

    @classmethod
    def validate_transition(cls, current_state: str, next_state: str) -> None:
        if not cls.can_transition(current_state, next_state):
            raise InvalidStateTransition(f"Invalid transition from {current_state} to {next_state}")

    @classmethod
    def allowed_next_states(cls, current_state: str) -> Iterable[str]:
        return sorted(cls.TRANSITIONS.get(current_state, set()))
