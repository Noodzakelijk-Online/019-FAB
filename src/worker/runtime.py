import json
import os
import ctypes
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
    try:
        lock_handle = _acquire_worker_lock(root, lock_path)
    except OSError as exc:
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
        _release_worker_lock(lock_handle)


def _acquire_worker_lock(project_root: Path, lock_path: Path):
    if os.name == "nt":
        return _acquire_windows_mutex(project_root)

    lock_handle = lock_path.open("a+b")
    _ensure_lock_byte(lock_handle)
    try:
        _lock_worker(lock_handle)
    except OSError:
        lock_handle.close()
        raise
    return lock_handle


def _release_worker_lock(lock_handle) -> None:
    if os.name == "nt":
        _release_windows_mutex(lock_handle)
        return

    _unlock_worker(lock_handle)
    lock_handle.close()


def _acquire_windows_mutex(project_root: Path):
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    name = f"Local\\FABWorker-{local_instance_id(project_root)}"
    handle = kernel32.CreateMutexW(None, False, name)
    if not handle:
        raise OSError(ctypes.get_last_error(), "Unable to create the FAB worker mutex")

    wait_result = kernel32.WaitForSingleObject(handle, 0)
    if wait_result not in (0x00000000, 0x00000080):
        kernel32.CloseHandle(handle)
        if wait_result == 0x00000102:
            raise OSError("The FAB worker mutex is already owned")
        raise OSError(ctypes.get_last_error(), "Unable to acquire the FAB worker mutex")
    return handle


def _release_windows_mutex(handle) -> None:
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.ReleaseMutex.argtypes = [wintypes.HANDLE]
    kernel32.ReleaseMutex.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.ReleaseMutex(handle)
    kernel32.CloseHandle(handle)


def _ensure_lock_byte(handle) -> None:
    handle.seek(0, os.SEEK_END)
    if handle.tell() == 0:
        handle.write(b"\0")
        handle.flush()
    handle.seek(0)


def _lock_worker(handle) -> None:
    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock_worker(handle) -> None:
    try:
        handle.seek(0)
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
