import unittest
from unittest.mock import patch

from src import main as fab_main


class TestMainEntrypoint(unittest.TestCase):
    def test_main_runs_exactly_one_authoritative_worker_cycle(self):
        with patch.object(fab_main, "worker_main", return_value=0) as worker_main:
            result = fab_main.main()

        self.assertEqual(result, 0)
        worker_main.assert_called_once_with(run_once=True)


if __name__ == "__main__":
    unittest.main()
