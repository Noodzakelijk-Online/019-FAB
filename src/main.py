"""Run one authoritative, ownership-checked FAB worker cycle."""

from src.run_worker import main as worker_main


def main() -> int:
    return worker_main(run_once=True)


if __name__ == "__main__":
    raise SystemExit(main())

