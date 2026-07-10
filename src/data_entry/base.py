from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from src.utils.rate_limiter import (
    QuotaExhaustedException,
    RateLimitExceededException,
    get_rate_limiter,
)

class BaseDataEntryHandler(ABC):
    """Abstract base class for all data entry handlers."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def acquire_outbound_slot(self, service: str) -> Optional[Dict[str, Any]]:
        """Reserve a downstream API/browser slot immediately before dispatch.

        A temporary provider throttle is operationally different from a failed
        bookkeeping action. Callers receive a structured, retryable result so
        workers can defer the approved attempt without consuming its failure
        budget or creating avoidable manual-review work.
        """
        limiter = get_rate_limiter(service)
        max_wait_seconds = _non_negative_float(
            self.config.get("outbound_rate_limit_max_wait_seconds"),
            default=0.0,
        )
        try:
            admitted = limiter.acquire(
                block=max_wait_seconds > 0,
                max_wait_seconds=max_wait_seconds,
            )
        except QuotaExhaustedException:
            admitted = False
        except RateLimitExceededException:
            admitted = False

        if admitted:
            return None

        rate = limiter.get_current_rate()
        quota_exhausted = bool(rate.get("quotaExhausted"))
        retry_after_seconds = _non_negative_float(
            self.config.get(
                "quota_exhausted_retry_delay_seconds"
                if quota_exhausted
                else "rate_limit_retry_delay_seconds"
            ),
            default=3600.0 if quota_exhausted else 60.0,
        )
        status = "quota_exhausted" if quota_exhausted else "rate_limited"
        label = str(rate.get("name") or service)
        return {
            "status": status,
            "message": f"{label} dispatch deferred because its configured quota is currently unavailable.",
            "retryable": True,
            "retry_after_seconds": retry_after_seconds,
            "requires_manual_review": False,
            "rate_limit": rate,
        }

    @abstractmethod
    def enter_data(self, categorized_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enters the categorized document data into the target system.

        Args:
            categorized_data: A dictionary containing the categorized document data.

        Returns:
            A dictionary indicating the success/failure status and any relevant messages.
        """
        pass


def _non_negative_float(value: Any, default: float) -> float:
    try:
        return max(float(value), 0.0)
    except (TypeError, ValueError):
        return default


