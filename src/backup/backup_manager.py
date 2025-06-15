from typing import Dict, Any, List
import os
import shutil
import datetime
import zipfile

class BackupManager:
    """Manages the backup and restoration of application data and configurations."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.backup_base_dir = self.config.get("backup_base_dir", "./backups")
        os.makedirs(self.backup_base_dir, exist_ok=True)

    def perform_backup(self, paths_to_backup: List[str], backup_config: Dict[str, Any]) -> Dict[str, Any]:
        """Performs a backup of specified files and directories.

        Args:
            paths_to_backup: A list of file or directory paths to include in the backup.
            backup_config: Configuration for the backup (e.g., "type": "zip").

        Returns:
            A dictionary with the backup status and path.
        """
        backup_type = backup_config.get("type", "zip")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"automated_bookkeeping_backup_{timestamp}"
        backup_path = os.path.join(self.backup_base_dir, backup_name)

        if backup_type == "zip":
            zip_file_path = f"{backup_path}.zip"
            try:
                with zipfile.ZipFile(zip_file_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                    for path in paths_to_backup:
                        if os.path.isfile(path):
                            zipf.write(path, os.path.basename(path))
                        elif os.path.isdir(path):
                            for root, _, files in os.walk(path):
                                for file in files:
                                    file_path = os.path.join(root, file)
                                    arcname = os.path.relpath(file_path, os.path.dirname(path)) # Relative path in zip
                                    zipf.write(file_path, arcname)
                print(f"Backup created successfully at {zip_file_path}")
                return {"status": "success", "path": zip_file_path}
            except Exception as e:
                print(f"Error creating zip backup: {e}")
                return {"status": "failure", "message": str(e)}
        else:
            return {"status": "failure", "message": f"Unsupported backup type: {backup_type}"}

    def restore_backup(self, backup_file_path: str, restore_dir: str) -> Dict[str, Any]:
        """Restores data from a specified backup file.

        Args:
            backup_file_path: The path to the backup file.
            restore_dir: The directory where the backup should be restored.

        Returns:
            A dictionary with the restore status.
        """
        if not os.path.exists(backup_file_path):
            return {"status": "failure", "message": f"Backup file not found: {backup_file_path}"}

        os.makedirs(restore_dir, exist_ok=True)

        if backup_file_path.endswith(".zip"):
            try:
                with zipfile.ZipFile(backup_file_path, "r") as zipf:
                    zipf.extractall(restore_dir)
                print(f"Backup restored successfully to {restore_dir}")
                return {"status": "success", "path": restore_dir}
            except Exception as e:
                print(f"Error restoring zip backup: {e}")
                return {"status": "failure", "message": str(e)}
        else:
            return {"status": "failure", "message": "Unsupported backup file format. Only .zip is supported."}


