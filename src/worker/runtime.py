import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from src.utils.runtime_identity import local_instance_id


class WorkerAlreadyRunningError(RuntimeError):
    pass


@contextmanager
def managed_worker_runtime(project_root: Path) -> Iterator[dict]:
    root = project_root.resolve()
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    lock_path = data_dir / "fab-worker.lock"
    runtime_path = data_dir / "fab-worker-runtime.json"
    lock_handle = lock_path.open("a+b")
    _ensure_lock_byte(lock_handle)

    try:
        _lock_worker(lock_handle)
    except OSError as exc:
        lock_handle.close()
        raise WorkerAlreadyRunningError(
            "Another FAB autonomous worker already owns this project runtime."
        ) from exc

    payload = {
        "service": "fab-autonomous-worker",
        "apiVersion": "1",
        "pid": os.getpid(),
        "instanceId": local_instance_id(root),
        "instanceRoot": str(root),
        "startedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    _atomic_json_write(runtime_path, payload)
    try:
        yield payload
    finally:
        try:
            current = json.loads(runtime_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            current = {}
        if int(current.get("pid") or 0) == os.getpid():
            runtime_path.unlink(missing_ok=True)
        _unlock_worker(lock_handle)
        lock_handle.close()


def _ensure_lock_byte(handle) -> None:
    handle.seek(0, os.SEEK_END)
    if handle.tell() == 0:
        handle.write(b"\0")
        handle.flush()
    handle.seek(0)


def _lock_worker(handle) -> None:
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        return

    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock_worker(handle) -> None:
    try:
        handle.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            return

        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    except OSError:
        pass


def _atomic_json_write(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(f"{path.suffix}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    os.replace(temporary, path)
