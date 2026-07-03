import functools
import random
import threading
import time
from collections import deque
from datetime import date
from typing import Any, Callable, Deque, Dict, Optional, Tuple, Type


class RateLimitExceededException(RuntimeError):
    """Raised when a call cannot be admitted within the configured wait budget."""


class QuotaExhaustedException(RateLimitExceededException):
    """Raised when a service daily quota has been consumed."""


class RateLimiter:
    """Thread-safe per-service quota guard for external bookkeeping dependencies."""

    def __init__(
        self,
        calls_per_second: Optional[float] = None,
        calls_per_minute: Optional[int] = None,
        calls_per_day: Optional[int] = None,
        name: str = "service",
        time_source: Callable[[], float] = time.monotonic,
        day_source: Callable[[], date] = date.today,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.calls_per_second = calls_per_second
        self.calls_per_minute = calls_per_minute
        self.calls_per_day = calls_per_day
        self.name = name
        self._time_source = time_source
        self._day_source = day_source
        self._sleep = sleep
        self._lock = threading.RLock()
        self._second_window: Deque[float] = deque()
        self._minute_window: Deque[float] = deque()
        self._day = self._day_source()
        self._daily_count = 0
        self._total_calls = 0
        self._blocked_calls = 0

    def acquire(self, block: bool = True, max_wait_seconds: Optional[float] = 30.0) -> bool:
        deadline = None if max_wait_seconds is None else self._time_source() + max_wait_seconds
        while True:
            with self._lock:
                now = self._time_source()
                self._rollover_day()
                self._trim_windows(now)
                if self._daily_quota_exhausted():
                    self._blocked_calls += 1
                    if block:
                        raise QuotaExhaustedException(f"{self.name} daily quota exhausted.")
                    return False
                wait_seconds = self._required_wait_seconds(now)
                if wait_seconds <= 0:
                    self._record_call(now)
                    return True
                self._blocked_calls += 1

            if not block:
                return False
            if deadline is not None:
                remaining = deadline - self._time_source()
                if remaining <= 0:
                    raise RateLimitExceededException(f"{self.name} rate limit wait budget exceeded.")
                wait_seconds = min(wait_seconds, remaining)
            self._sleep(max(wait_seconds, 0.001))

    def get_current_rate(self) -> Dict[str, Any]:
        with self._lock:
            now = self._time_source()
            self._rollover_day()
            self._trim_windows(now)
            return {
                "name": self.name,
                "callsPerSecond": self.calls_per_second,
                "callsPerMinute": self.calls_per_minute,
                "callsPerDay": self.calls_per_day,
                "secondCount": len(self._second_window),
                "minuteCount": len(self._minute_window),
                "dailyCount": self._daily_count,
                "dailyRemaining": None if self.calls_per_day is None else max(self.calls_per_day - self._daily_count, 0),
                "totalCalls": self._total_calls,
                "blockedCalls": self._blocked_calls,
                "quotaExhausted": self._daily_quota_exhausted(),
            }

    def get_remaining_quota(self) -> Dict[str, Optional[int]]:
        rate = self.get_current_rate()
        second_capacity = None if self.calls_per_second is None else max(int(self.calls_per_second), 1)
        return {
            "perSecond": None if second_capacity is None else max(second_capacity - rate["secondCount"], 0),
            "perMinute": None if self.calls_per_minute is None else max(self.calls_per_minute - rate["minuteCount"], 0),
            "perDay": rate["dailyRemaining"],
        }

    def reset(self) -> None:
        with self._lock:
            self._second_window.clear()
            self._minute_window.clear()
            self._day = self._day_source()
            self._daily_count = 0
            self._total_calls = 0
            self._blocked_calls = 0

    def _record_call(self, now: float) -> None:
        self._second_window.append(now)
        self._minute_window.append(now)
        self._daily_count += 1
        self._total_calls += 1

    def _required_wait_seconds(self, now: float) -> float:
        waits = []
        if self.calls_per_second is not None:
            if self.calls_per_second >= 1:
                if len(self._second_window) >= int(self.calls_per_second):
                    waits.append(1.0 - (now - self._second_window[0]))
            elif self._second_window:
                waits.append((1.0 / self.calls_per_second) - (now - self._second_window[-1]))
        if self.calls_per_minute is not None and len(self._minute_window) >= self.calls_per_minute:
            waits.append(60.0 - (now - self._minute_window[0]))
        return max(waits) if waits else 0.0

    def _trim_windows(self, now: float) -> None:
        second_window_seconds = 1.0
        if self.calls_per_second is not None and 0 < self.calls_per_second < 1:
            second_window_seconds = 1.0 / self.calls_per_second
        while self._second_window and now - self._second_window[0] >= second_window_seconds:
            self._second_window.popleft()
        while self._minute_window and now - self._minute_window[0] >= 60.0:
            self._minute_window.popleft()

    def _rollover_day(self) -> None:
        today = self._day_source()
        if today != self._day:
            self._day = today
            self._daily_count = 0

    def _daily_quota_exhausted(self) -> bool:
        return self.calls_per_day is not None and self._daily_count >= self.calls_per_day


DEFAULT_SERVICE_LIMITS: Dict[str, Dict[str, Any]] = {
    "gmail": {"calls_per_second": 10, "calls_per_minute": 250, "calls_per_day": 15000, "name": "Gmail API"},
    "drive": {"calls_per_second": 10, "calls_per_minute": 600, "calls_per_day": 12000, "name": "Google Drive API"},
    "vision": {"calls_per_second": 20, "calls_per_minute": 1800, "calls_per_day": 50000, "name": "Cloud Vision API"},
    "waveapps": {"calls_per_second": 2, "calls_per_minute": 60, "calls_per_day": 5000, "name": "WaveApps"},
    "mijngeldzaken": {"calls_per_second": 1, "calls_per_minute": 30, "calls_per_day": 2000, "name": "MijnGeldzaken"},
    "hunyuan": {"calls_per_second": 5, "calls_per_minute": 100, "calls_per_day": 10000, "name": "Hunyuan OCR"},
    "ing_bank": {"calls_per_second": 0.5, "calls_per_minute": 15, "calls_per_day": 500, "name": "ING Bank"},
    "wise": {"calls_per_second": 2, "calls_per_minute": 60, "calls_per_day": 3000, "name": "Wise"},
    "svb": {"calls_per_second": 0.5, "calls_per_minute": 15, "calls_per_day": 500, "name": "SVB"},
}

_rate_limiters: Dict[str, RateLimiter] = {}
_registry_lock = threading.RLock()


def get_rate_limiter(service: str) -> RateLimiter:
    key = service.lower()
    with _registry_lock:
        limiter = _rate_limiters.get(key)
        if limiter is None:
            settings = DEFAULT_SERVICE_LIMITS.get(key, {"calls_per_second": 1, "calls_per_minute": 30, "name": key})
            limiter = RateLimiter(**settings)
            _rate_limiters[key] = limiter
        return limiter


def set_rate_limiter(
    service: str,
    calls_per_second: Optional[float] = None,
    calls_per_minute: Optional[int] = None,
    calls_per_day: Optional[int] = None,
    name: Optional[str] = None,
    limiter: Optional[RateLimiter] = None,
) -> RateLimiter:
    key = service.lower()
    with _registry_lock:
        _rate_limiters[key] = limiter or RateLimiter(
            calls_per_second=calls_per_second,
            calls_per_minute=calls_per_minute,
            calls_per_day=calls_per_day,
            name=name or service,
        )
        return _rate_limiters[key]


def reset_all_limiters() -> None:
    with _registry_lock:
        _rate_limiters.clear()


def get_all_rates() -> Dict[str, Dict[str, Any]]:
    with _registry_lock:
        for service in DEFAULT_SERVICE_LIMITS:
            get_rate_limiter(service)
        return {service: limiter.get_current_rate() for service, limiter in sorted(_rate_limiters.items())}


def get_rate_limit_dashboard() -> str:
    lines = ["FAB Rate Limiter Dashboard", "Service | Used today | Remaining today | Blocked"]
    for service, rate in get_all_rates().items():
        remaining = "unlimited" if rate["dailyRemaining"] is None else str(rate["dailyRemaining"])
        lines.append(f"{service} | {rate['dailyCount']} | {remaining} | {rate['blockedCalls']}")
    return "\n".join(lines)


def rate_limit(service: str, block: bool = True, max_wait_seconds: Optional[float] = 30.0) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            get_rate_limiter(service).acquire(block=block, max_wait_seconds=max_wait_seconds)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def rate_limit_with_retry(
    service: str,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retry_exceptions: Tuple[Type[BaseException], ...] = (Exception,),
    jitter: float = 0.1,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempt = 0
            while True:
                get_rate_limiter(service).acquire()
                try:
                    return func(*args, **kwargs)
                except retry_exceptions:
                    attempt += 1
                    if attempt > max_retries:
                        raise
                    delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
                    if jitter:
                        delay += random.uniform(0, jitter)
                    time.sleep(delay)

        return wrapper

    return decorator
