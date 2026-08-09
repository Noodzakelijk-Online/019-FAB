import argparse
import json

from src.config_loader import ConfigLoader
from src.operations.local_ledger import LocalOperationsLedger
from src.operations.local_readiness import LocalReadinessService
from src.operations.local_support_bundle import LocalSupportBundleService


def main() -> int:
    parser = argparse.ArgumentParser(description="Run sanitized FAB readiness and health diagnostics.")
    parser.add_argument("--json", action="store_true", help="Print the full sanitized diagnostic JSON.")
    parser.add_argument("--support-bundle", action="store_true", help="Create a sanitized support ZIP.")
    parser.add_argument("--actor", default="fab_doctor:local_operator")
    args = parser.parse_args()

    config = ConfigLoader(config_file="config/config.ini").get_all_config()
    ledger_path = str(
        config.get("fab_local_ledger_path")
        or config.get("operations_ledger_path")
        or "data/fab_operations.sqlite3"
    )
    readiness = LocalReadinessService(config, ledger_path=ledger_path)
    service = LocalSupportBundleService(LocalOperationsLedger(ledger_path), config, readiness)
    result = service.doctor()
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"FAB readiness: {result['readiness']['status']}")
        print(f"FAB health: {result['health']['status']}")
        print(f"Readiness issues: {result['readiness']['issueCount']}")
        print(f"Operational issues: {sum(result['health']['severityCounts'].values())}")
        print(f"Emergency stop: {'engaged' if result['autonomy']['active'] else 'clear'}")
    if args.support_bundle:
        bundle = service.create(actor=args.actor, note="Created by FAB doctor CLI.")
        print(f"Support bundle: {bundle['bundlePath']}")
        print(f"SHA-256: {bundle['sha256']}")
    return 1 if result["readiness"]["status"] == "blocked" or result["health"]["status"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
