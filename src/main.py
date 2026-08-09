"""Run one authoritative FAB worker cycle.

The legacy checkpoint controller remains available only through the explicit
``worker_run_legacy_workflow`` compatibility switch. Production entrypoints
use the SQLite operations ledger, runtime ownership lock, and governed worker
stages shared with the long-running Windows and container services.
"""

from src.run_worker import main as worker_main


def main() -> int:
    return worker_main(run_once=True)


if __name__ == "__main__":
    raise SystemExit(main())

