from src.config_loader import ConfigLoader
from src.data_entry.posting_executor import PostingExecutor
from src.operations.local_exports import LocalExportAttemptService
from src.operations.local_runtime import build_local_operations_ledger


def run_approved_postings(config):
    ledger = build_local_operations_ledger(config)
    if ledger:
        service = LocalExportAttemptService(ledger, config)
        preparation = service.prepare_ready_exports(limit=25)
        execution = service.process_approved_attempts(limit=20, actor="manual_runner")
        return {
            "status": execution.get("status"),
            "sourceOfTruth": "local_operations_ledger",
            "preparation": preparation,
            "execution": execution,
        }
    result = PostingExecutor(config).process_approved_attempts()
    return {**result, "sourceOfTruth": "legacy_posting_attempts"}


if __name__ == "__main__":
    config = ConfigLoader(config_file="config/config.ini").get_all_config()
    result = run_approved_postings(config)
    print(result)
