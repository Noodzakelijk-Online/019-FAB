import unittest
from datetime import date
from unittest.mock import patch

from src.utils.rate_limiter import (
    QuotaExhaustedException,
    RateLimitExceededException,
    RateLimiter,
    get_all_rates,
    get_rate_limit_dashboard,
    get_rate_limiter,
    rate_limit,
    rate_limit_with_retry,
    reset_all_limiters,
    set_rate_limiter,
)


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.today = date(2026, 7, 3)
        self.sleeps = []

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds

    def day(self):
        return self.today


class TestRateLimiter(unittest.TestCase):
    def tearDown(self):
        reset_all_limiters()

    def test_non_blocking_acquire_reports_second_limit(self):
        clock = FakeClock()
        limiter = RateLimiter(calls_per_second=1, name="test", time_source=clock.monotonic, day_source=clock.day, sleep=clock.sleep)

        self.assertTrue(limiter.acquire(block=False))
        self.assertFalse(limiter.acquire(block=False))
        self.assertEqual(limiter.get_current_rate()["blockedCalls"], 1)

    def test_blocking_acquire_waits_until_window_resets(self):
        clock = FakeClock()
        limiter = RateLimiter(calls_per_second=1, name="test", time_source=clock.monotonic, day_source=clock.day, sleep=clock.sleep)

        self.assertTrue(limiter.acquire())
        self.assertTrue(limiter.acquire(max_wait_seconds=2))

        self.assertGreaterEqual(sum(clock.sleeps), 1.0)
        self.assertEqual(limiter.get_current_rate()["totalCalls"], 2)

    def test_wait_budget_exceeded_raises(self):
        clock = FakeClock()
        limiter = RateLimiter(calls_per_minute=1, name="test", time_source=clock.monotonic, day_source=clock.day, sleep=clock.sleep)

        self.assertTrue(limiter.acquire())
        with self.assertRaises(RateLimitExceededException):
            limiter.acquire(max_wait_seconds=0.01)

    def test_daily_quota_exhaustion_raises_and_resets_next_day(self):
        clock = FakeClock()
        limiter = RateLimiter(calls_per_day=1, name="test", time_source=clock.monotonic, day_source=clock.day, sleep=clock.sleep)

        self.assertTrue(limiter.acquire())
        with self.assertRaises(QuotaExhaustedException):
            limiter.acquire()

        clock.today = date(2026, 7, 4)
        self.assertTrue(limiter.acquire())

    def test_registry_preconfigures_bookkeeping_services(self):
        rates = get_all_rates()

        self.assertIn("waveapps", rates)
        self.assertIn("mijngeldzaken", rates)
        self.assertIn("drive", rates)
        self.assertEqual(get_rate_limiter("waveapps").calls_per_minute, 60)
        self.assertIn("FAB Rate Limiter Dashboard", get_rate_limit_dashboard())

    def test_rate_limit_decorator_uses_registered_limiter(self):
        limiter = set_rate_limiter("custom", calls_per_day=1)

        @rate_limit("custom")
        def call():
            return "ok"

        self.assertEqual(call(), "ok")
        self.assertEqual(limiter.get_current_rate()["dailyCount"], 1)
        with self.assertRaises(QuotaExhaustedException):
            call()

    def test_retry_decorator_retries_transient_failure(self):
        set_rate_limiter("retry", calls_per_second=100)
        attempts = {"count": 0}

        @rate_limit_with_retry("retry", max_retries=2, base_delay=0, jitter=0, retry_exceptions=(ValueError,))
        def call():
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise ValueError("temporary")
            return "ok"

        with patch("time.sleep", lambda _: None):
            self.assertEqual(call(), "ok")
        self.assertEqual(attempts["count"], 3)


if __name__ == "__main__":
    unittest.main()

