from typing import Any, Dict, List
import os
import datetime
import zipfile


class BackupManager:
    """Manages backup and restoration of FAB local data/configuration."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config or {}
        self.backup_base_dir = self.config.get("backup_base_dir", "backups")
        os.makedirs(self.backup_base_dir, exist_ok=True)

    def default_backup_paths(self) -> List[str]:
        paths = [
            self.config.get("database_path", "data/fab.sqlite3"),
            self.config.get("manual_review_queue_file", "data/manual_review_queue.json"),
            self.config.get("local_input_dir", "data/sort_out"),
            self.config.get("bank_import_dir", "data/bank_exports"),
        ]
        return [path for path in paths if path and os.path.exists(path)]

    def perform_backup(self, paths_to_backup: List[str] = None, backup_config: Dict[str, Any] = None) -> Dict[str, Any]:
        backup_config = backup_config or {}
        paths_to_backup = paths_to_backup or self.default_backup_paths()
        backup_type = backup_config.get("type", "zip")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"fab_backup_{timestamp}"
        backup_path = os.path.join(self.backup_base_dir, backup_name)

        if backup_type != "zip":
            return {"status": "failure", "message": f"Unsupported backup type: {backup_type}"}

        zip_file_path = f"{backup_path}.zip"
        try:
            with zipfile.ZipFile(zip_file_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for path in paths_to_backup:
                    if not path or not os.path.exists(path):
                        continue
                    if os.path.isfile(path):
                        zipf.write(path, os.path.relpath(path, start=os.getcwd()))
                    elif os.path.isdir(path):
                        for root, _, files in os.walk(path):
                            for file in files:
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path, start=os.getcwd())
                                zipf.write(file_path, arcname)
            return {"status": "success", "path": zip_file_path, "included_paths": paths_to_backup}
        except Exception as exc:
            return {"status": "failure", "message": str(exc)}

    def list_backups(self) -> List[Dict[str, Any]]:
        backups = []
        if not os.path.exists(self.backup_base_dir):
            return backups
        for filename in sorted(os.listdir(self.backup_base_dir), reverse=True):
            if not filename.endswith(".zip"):
                continue
            path = os.path.join(self.backup_base_dir, filename)
            backups.append(
                {
                    "filename": filename,
                    "path": path,
                    "size_bytes": os.path.getsize(path),
                    "modified_at": datetime.datetime.fromtimestamp(os.path.getmtime(path)).isoformat(),
                }
            )
        return backups

    def restore_backup(self, backup_file_path: str, restore_dir: str, allow_overwrite: bool = False) -> Dict[str, Any]:
        if not os.path.exists(backup_file_path):
            return {"status": "failure", "message": f"Backup file not found: {backup_file_path}"}
        if not backup_file_path.endswith(".zip"):
            return {"status": "failure", "message": "Unsupported backup file format. Only .zip is supported."}

        os.makedirs(restore_dir, exist_ok=True)
        try:
            with zipfile.ZipFile(backup_file_path, "r") as zipf:
                for member in zipf.namelist():
                    target_path = os.path.abspath(os.path.join(restore_dir, member))
                    restore_root = os.path.abspath(restore_dir)
                    if not target_path.startswith(restore_root):
                        return {"status": "failure", "message": f"Unsafe path in backup: {member}"}
                    if os.path.exists(target_path) and not allow_overwrite:
                        return {"status": "failure", "message": f"Restore target already exists: {target_path}"}
                zipf.extractall(restore_dir)
            return {"status": "success", "path": restore_dir}
        except Exception as exc:
            return {"status": "failure", "message": str(exc)}
