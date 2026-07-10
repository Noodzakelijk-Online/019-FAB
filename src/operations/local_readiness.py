from __future__ import annotations

import importlib.util
import os
import platform
import shutil
import sqlite3
import sys
from typing import Any, Dict, List, Optional


LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
SECRET_MARKERS = ("token", "secret", "password", "api_key", "client_secret", "credential")


class LocalReadinessService:
    """Summarize local FAB setup readiness without returning secret values."""

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        *,
        ledger_path: Optional[str] = None,
        api_host: Optional[str] = None,
        api_port: Optional[Any] = None,
        base_url: Optional[str] = None,
        api_token_configured: Optional[bool] = None,
        intake_paths: Optional[List[str]] = None,
        intake_extensions: Optional[List[str]] = None,
    ):
        self.config = config or {}
        self.ledger_path = ledger_path or str(
            _config_value(
                self.config,
                "fab_local_ledger_path",
                "operations_ledger_path",
                "ledger_path",
                default="data/fab_operations.sqlite3",
            )
        )
        self.api_host = api_host or str(
            _config_value(
                self.config,
                "fab_local_api_host",
                "operations_api_host",
                "api_host",
                default="127.0.0.1",
            )
        )
        self.api_port = _bounded_port(api_port or _config_value(
            self.config,
            "fab_local_api_port",
            "operations_api_port",
            "api_port",
            default=5001,
        ))
        self.base_url = _normalized_base_url(base_url or _config_value(
            self.config,
            "fab_local_api_base_url",
            "operations_api_url",
            "operations_api_base_url",
            "api_base_url",
            "api_url",
        ))
        self.api_token_configured = (
            api_token_configured
            if api_token_configured is not None
            else _has_value(
                self.config,
                "fab_local_api_token",
                "fab_operations_api_token",
                "operations_api_token",
                "api_token",
            )
        )
        self.intake_paths = intake_paths if intake_paths is not None else _list_config(
            self.config,
            "fab_local_intake_paths",
            "operations_local_intake_paths",
            "operations_intake_paths",
            "operations_scanner_folder",
            "operations_scanner_watch_folder",
            "scanner_folder",
            "scanner_watch_folder",
        )
        self.intake_extensions = intake_extensions if intake_extensions is not None else _list_config(
            self.config,
            "fab_local_intake_extensions",
            "operations_local_intake_extensions",
            "operations_intake_extensions",
        )

    def summarize(self) -> Dict[str, Any]:
        dependencies = self._dependencies()
        paths = self._paths()
        credentials = self._credentials()
        sources = self._sources(credentials, paths)
        security = self._security()
        local_access = self._local_access(security)
        issues = self._issues(dependencies, paths, credentials, sources, security)
        status = _overall_status(issues)
        return {
            "status": status,
            "security": security,
            "localAccess": local_access,
            "paths": paths,
            "dependencies": dependencies,
            "credentials": credentials,
            "sources": sources,
            "issues": issues,
            "nextActions": _next_actions(issues, sources),
        }

    def compact(self) -> Dict[str, Any]:
        summary = self.summarize()
        return {
            "status": summary["status"],
            "issueCount": len(summary["issues"]),
            "blockedIssues": len([issue for issue in summary["issues"] if issue["severity"] == "blocked"]),
            "attentionIssues": len([issue for issue in summary["issues"] if issue["severity"] == "attention"]),
            "readySources": len([source for source in summary["sources"] if source["status"] == "ready"]),
            "dashboardUrl": summary["localAccess"]["dashboardUrl"],
            "apiBaseUrl": summary["localAccess"]["apiBaseUrl"],
            "authMode": summary["localAccess"]["authMode"],
            "remoteExposureSafe": summary["security"]["remoteExposureSafe"],
        }

    def _dependencies(self) -> List[Dict[str, Any]]:
        tesseract_cmd = str(
            _config_value(self.config, "tesseract_cmd", "ocr_tesseract_cmd", default="tesseract")
        )
        tesseract_resolved = _resolve_executable(tesseract_cmd)
        return [
            {
                "id": "python",
                "label": "Python",
                "status": "ok",
                "configured": True,
                "version": platform.python_version(),
                "details": f"{platform.system()} {platform.release()}",
            },
            {
                "id": "sqlite",
                "label": "SQLite",
                "status": "ok",
                "configured": True,
                "version": sqlite3.sqlite_version,
                "details": "Local operations ledger backend.",
            },
            _python_dependency("flask", "Flask", "Local dashboard/API"),
            _python_dependency("pytesseract", "pytesseract", "Python wrapper for Tesseract OCR"),
            {
                "id": "tesseract",
                "label": "Tesseract executable",
                "status": "ok" if tesseract_resolved else "attention",
                "configured": bool(tesseract_cmd),
                "command": tesseract_cmd,
                "resolved": tesseract_resolved,
                "details": "Required for local OCR when Tesseract is selected.",
            },
            _python_dependency("PIL", "Pillow", "Image loading for OCR processors"),
            _python_dependency("googleapiclient", "Google API client", "Gmail, Drive, Photos, and Vision integrations"),
            _python_dependency("playwright", "Playwright", "Optional supervised browser tooling"),
        ]

    def _paths(self) -> Dict[str, Any]:
        backup_dir = str(
            _config_value(
                self.config,
                "fab_local_backup_dir",
                "operations_backup_dir",
                "backup_dir",
                default="data/backups",
            )
        )
        return {
            "ledger": _path_status("ledger", "Operations ledger", self.ledger_path, kind="file"),
            "backupDir": _path_status("backupDir", "Backup directory", backup_dir, kind="directory"),
            "mijngeldzakenExportDir": _path_status(
                "mijngeldzakenExportDir",
                "MijnGeldzaken supervised exports",
                _config_value(
                    self.config,
                    "mijngeldzaken_export_dir",
                    "operations_mijngeldzaken_export_dir",
                    default="data/exports/mijngeldzaken",
                ),
                kind="directory",
            ),
            "intake": [
                _path_status(f"intake_{index + 1}", f"Intake folder {index + 1}", path, kind="directory")
                for index, path in enumerate(self.intake_paths)
            ],
            "intakeExtensions": list(self.intake_extensions),
        }

    def _credentials(self) -> List[Dict[str, Any]]:
        return [
            _credential_file("gmail_credentials", "Gmail OAuth credentials", self.config, "gmail_credentials_file", "gmail.credentials_file", "gmail_credentials_path"),
            _credential_file("gmail_token", "Gmail OAuth token", self.config, "gmail_token_file", "gmail.token_file", "gmail_token_path"),
            _credential_file("drive_credentials", "Google Drive OAuth credentials", self.config, "google_drive_credentials_file", "google_drive.credentials_file", "drive.credentials_file", "drive_credentials_path"),
            _credential_file("drive_token", "Google Drive OAuth token", self.config, "google_drive_token_file", "google_drive.token_file", "drive.token_file", "drive_token_path"),
            _credential_file("photos_credentials", "Google Photos OAuth credentials", self.config, "google_photos_credentials_file", "google_photos.credentials_file", "photos.credentials_file", "photos_credentials_path"),
            _credential_file("photos_token", "Google Photos OAuth token", self.config, "google_photos_token_file", "google_photos.token_file", "photos.token_file", "photos_token_path"),
            _credential_file("vision_credentials", "Google Vision credentials", self.config, "google_vision_credentials_file", "google_vision.credentials_file"),
            _credential_value("freshdesk_api_key", "Freshdesk API key", self.config, "freshdesk_api_key", "freshdesk.api_key"),
            _credential_value("freshdesk_domain", "Freshdesk domain", self.config, "freshdesk_domain", "freshdesk.domain", secret=False),
            _credential_value("wave_business_token", "Waveapps Business token", self.config, "waveapps_business_access_token", "waveapps_business.access_token"),
            _credential_value("wave_business_id", "Waveapps Business ID", self.config, "waveapps_business_id", "waveapps_business.business_id", secret=False),
            _credential_value("wave_personal_token", "Waveapps Personal token", self.config, "waveapps_personal_access_token", "waveapps_personal.access_token"),
            _credential_value("wave_personal_id", "Waveapps Personal ID", self.config, "waveapps_personal_id", "waveapps_personal.personal_id", secret=False),
            _credential_value("mijngeldzaken_username", "Legacy MijnGeldzaken username (ignored)", self.config, "mijngeldzaken_username", "mijngeldzaken.username", secret=False),
            _credential_value("mijngeldzaken_password", "Legacy MijnGeldzaken password (ignored)", self.config, "mijngeldzaken_password", "mijngeldzaken.password"),
            _credential_value("banking_credentials", "Banking API credentials", self.config, "banking_api_credentials", "banking.api_credentials", "banking_api_client_secret", "banking.client_secret"),
            _credential_value("api_token", "FAB local API token", self.config, "fab_local_api_token", "fab_operations_api_token", "operations_api_token", "operations.api_token", "api_token"),
        ]

    def _sources(self, credentials: List[Dict[str, Any]], paths: Dict[str, Any]) -> List[Dict[str, Any]]:
        credential_map = {item["id"]: item for item in credentials}
        dependencies = {item["id"]: item for item in self._dependencies()}
        return [
            _source_status(
                "local_folder",
                "Local/scanner folders",
                configured=bool(paths["intake"]),
                ready=any(path["exists"] for path in paths["intake"]),
                details="Reads configured local_intake_paths into the local ledger.",
            ),
            _oauth_source("gmail", "Gmail", credential_map["gmail_credentials"], credential_map["gmail_token"]),
            _oauth_source("google_drive", "Google Drive", credential_map["drive_credentials"], credential_map["drive_token"]),
            _oauth_source("google_photos", "Google Photos", credential_map["photos_credentials"], credential_map["photos_token"]),
            _pair_source(
                "freshdesk",
                "Freshdesk",
                credential_map["freshdesk_api_key"],
                credential_map["freshdesk_domain"],
                details="Requires API key and domain.",
            ),
            _source_status(
                "tesseract_ocr",
                "Tesseract OCR",
                configured=dependencies["pytesseract"]["configured"] or dependencies["tesseract"]["configured"],
                ready=dependencies["pytesseract"]["status"] == "ok" and dependencies["tesseract"]["status"] == "ok",
                details="Local OCR path for PDFs/images converted to images.",
            ),
            _source_status(
                "mijngeldzaken",
                "MijnGeldzaken",
                configured=paths["mijngeldzakenExportDir"]["configured"],
                ready=paths["mijngeldzakenExportDir"]["status"] == "ok",
                details=(
                    "FAB can prepare checksum-bound import artifacts. External submission "
                    "requires a supervised user-owned session; stored passwords are ignored."
                ),
            ),
            _pair_source(
                "waveapps_business",
                "Waveapps Business",
                credential_map["wave_business_token"],
                credential_map["wave_business_id"],
                details="API target for business bookkeeping drafts and approved exports.",
            ),
            _pair_source(
                "waveapps_personal",
                "Waveapps Personal",
                credential_map["wave_personal_token"],
                credential_map["wave_personal_id"],
                details="API target for personal or special-administration drafts and approved exports.",
            ),
            _source_status(
                "banking_api",
                "Banking API",
                configured=_has_value(self.config, "banking_api_endpoint") or credential_map["banking_credentials"]["configured"],
                ready=_has_value(self.config, "banking_api_endpoint") and credential_map["banking_credentials"]["configured"],
                details="Feeds reconciliation; missing credentials should keep matching manual/import-based.",
            ),
        ]

    def _security(self) -> Dict[str, Any]:
        host_is_loopback = self.api_host in LOOPBACK_HOSTS
        remote_blocked = not host_is_loopback and not self.api_token_configured
        secret_config_keys = _configured_secret_keys(self.config)
        return {
            "apiHost": self.api_host,
            "loopbackOnly": host_is_loopback,
            "apiTokenConfigured": bool(self.api_token_configured),
            "remoteExposureSafe": not remote_blocked,
            "remoteExposureBlocked": remote_blocked,
            "secretValuesRedacted": True,
            "configuredSecretKeys": secret_config_keys,
        }

    def _local_access(self, security: Dict[str, Any]) -> Dict[str, Any]:
        dashboard_url = self.base_url or f"http://{self.api_host}:{self.api_port}/"
        api_base_url = dashboard_url.rstrip("/") + "/api"
        token_required = bool(self.api_token_configured)
        ngrok_ready = bool(token_required and security["remoteExposureSafe"])
        return {
            "dashboardUrl": dashboard_url,
            "apiBaseUrl": api_base_url,
            "authMode": "bearer_token_or_dashboard_login" if token_required else "loopback_no_token",
            "authHeaderRequired": token_required,
            "authHeaderExample": "Authorization: Bearer <FAB_LOCAL_API_TOKEN>" if token_required else "",
            "ngrokReady": ngrok_ready,
            "ngrokSafety": (
                "safe_with_token" if ngrok_ready
                else "blocked_without_token" if security["remoteExposureBlocked"]
                else "loopback_only"
            ),
            "windows": {
                "startCommand": "python -m src.operations.local_api",
                "workingDirectory": "019-FAB repository root",
                "taskScheduler": "Run the start command from Windows Task Scheduler after logon; keep host on 127.0.0.1 unless a token is configured.",
                "recommendedEnvironment": [
                    "FAB_LOCAL_LEDGER_PATH",
                    "FAB_LOCAL_API_HOST",
                    "FAB_LOCAL_API_PORT",
                    "FAB_LOCAL_API_TOKEN",
                    "FAB_LOCAL_INTAKE_PATHS",
                ],
            },
            "safeRemoteChecklist": [
                "Set FAB_LOCAL_API_TOKEN before any ngrok or non-loopback exposure.",
                "Keep the dashboard on 127.0.0.1 for normal local use.",
                "Do not put credentials, tokens, or financial documents in Git-tracked folders.",
                "Use approval phrases for export, restore, and other irreversible actions.",
            ],
            "externalSubmission": "not_executed",
        }

    def _issues(
        self,
        dependencies: List[Dict[str, Any]],
        paths: Dict[str, Any],
        credentials: List[Dict[str, Any]],
        sources: List[Dict[str, Any]],
        security: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        issues: List[Dict[str, Any]] = []
        if security["remoteExposureBlocked"]:
            issues.append({
                "severity": "blocked",
                "type": "remote_api_without_token",
                "message": "FAB refuses non-loopback API exposure without an API token.",
                "nextAction": "Set operations.api_token before using a tunnel or non-loopback host.",
            })
        for dependency in dependencies:
            if dependency["status"] != "ok":
                issues.append({
                    "severity": "attention",
                    "type": "dependency_missing",
                    "entity": dependency["id"],
                    "message": f"{dependency['label']} is not ready.",
                    "nextAction": dependency["details"],
                })
        for path in [
            paths["ledger"],
            paths["backupDir"],
            paths["mijngeldzakenExportDir"],
            *paths["intake"],
        ]:
            if path["configured"] and not path["parentWritable"]:
                issues.append({
                    "severity": "blocked",
                    "type": "path_not_writable",
                    "entity": path["id"],
                    "message": f"{path['label']} is not writable.",
                    "nextAction": "Move this path to a private writable local folder.",
                })
            elif path["configured"] and not path["exists"] and path["kind"] == "directory":
                issues.append({
                    "severity": "attention",
                    "type": "path_missing",
                    "entity": path["id"],
                    "message": f"{path['label']} does not exist yet.",
                    "nextAction": "Create the folder or update the configured path.",
                })
        for credential in credentials:
            if credential.get("partial"):
                issues.append({
                    "severity": "attention",
                    "type": "credential_path_missing",
                    "entity": credential["id"],
                    "message": f"{credential['label']} is configured but the file is missing.",
                    "nextAction": "Create the file, finish OAuth login, or update config.ini.",
                })
        if not any(source["status"] == "ready" for source in sources):
            issues.append({
                "severity": "attention",
                "type": "no_ready_sources",
                "message": "No document source is fully ready.",
                "nextAction": "Configure a local intake folder or finish one external source credential setup.",
            })
        return issues


def _python_dependency(module_name: str, label: str, details: str) -> Dict[str, Any]:
    found = importlib.util.find_spec(module_name) is not None
    return {
        "id": module_name.lower(),
        "label": label,
        "status": "ok" if found else "attention",
        "configured": found,
        "details": details,
    }


def _resolve_executable(command: str) -> Optional[str]:
    if not command:
        return None
    if os.path.isabs(command) and os.path.exists(command):
        return command
    return shutil.which(command)


def _path_status(path_id: str, label: str, path: Any, kind: str) -> Dict[str, Any]:
    raw_path = str(path or "").strip()
    configured = bool(raw_path)
    resolved = os.path.abspath(os.path.expanduser(raw_path)) if configured else ""
    exists = os.path.exists(resolved) if configured else False
    parent = resolved if kind == "directory" and exists else _nearest_existing_parent(os.path.dirname(resolved))
    parent_writable = bool(configured and parent and os.path.isdir(parent) and os.access(parent, os.W_OK))
    return {
        "id": path_id,
        "label": label,
        "kind": kind,
        "configured": configured,
        "path": raw_path,
        "resolvedPath": resolved,
        "exists": exists,
        "parentWritable": parent_writable,
        "status": "ok" if configured and (exists or parent_writable) else "attention",
    }


def _nearest_existing_parent(path: str) -> str:
    current = path
    while current and not os.path.exists(current):
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return current


def _credential_file(identifier: str, label: str, config: Dict[str, Any], *keys: str) -> Dict[str, Any]:
    value = _config_value(config, *keys)
    configured = value not in (None, "")
    path = str(value or "")
    exists = os.path.exists(os.path.expanduser(path)) if configured else False
    return {
        "id": identifier,
        "label": label,
        "kind": "file",
        "configured": configured,
        "exists": exists,
        "partial": configured and not exists,
        "path": path if configured else "",
        "secret": True,
    }


def _credential_value(identifier: str, label: str, config: Dict[str, Any], *keys: str, secret: bool = True) -> Dict[str, Any]:
    configured = _has_value(config, *keys)
    return {
        "id": identifier,
        "label": label,
        "kind": "value",
        "configured": configured,
        "exists": configured,
        "partial": False,
        "source": "configured" if configured else "missing",
        "secret": secret,
    }


def _source_status(identifier: str, label: str, configured: bool, ready: bool, details: str) -> Dict[str, Any]:
    if ready:
        status = "ready"
    elif configured:
        status = "needs_attention"
    else:
        status = "not_configured"
    return {
        "id": identifier,
        "label": label,
        "configured": bool(configured),
        "status": status,
        "ready": bool(ready),
        "details": details,
    }


def _oauth_source(identifier: str, label: str, credentials: Dict[str, Any], token: Dict[str, Any]) -> Dict[str, Any]:
    configured = credentials["configured"] or token["configured"]
    ready = credentials["exists"] and token["exists"]
    source = _source_status(
        identifier,
        label,
        configured=configured,
        ready=ready,
        details="OAuth credentials and a token file are required for unattended fetches.",
    )
    if credentials["exists"] and not token["exists"]:
        source["status"] = "needs_auth"
        source["details"] = "Credentials exist; finish OAuth login to create the token file."
    return source


def _pair_source(identifier: str, label: str, first: Dict[str, Any], second: Dict[str, Any], details: str) -> Dict[str, Any]:
    return _source_status(
        identifier,
        label,
        configured=first["configured"] or second["configured"],
        ready=first["configured"] and second["configured"],
        details=details,
    )


def _overall_status(issues: List[Dict[str, Any]]) -> str:
    if any(issue["severity"] == "blocked" for issue in issues):
        return "blocked"
    if issues:
        return "attention"
    return "ok"


def _next_actions(issues: List[Dict[str, Any]], sources: List[Dict[str, Any]]) -> List[str]:
    actions = list(dict.fromkeys([issue["nextAction"] for issue in issues if issue.get("nextAction")]))
    if any(source["status"] == "ready" for source in sources):
        actions.append("Run folder intake or the configured workflow from the dashboard.")
    return actions[:8]


def _bounded_port(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = 5001
    if parsed < 1 or parsed > 65535:
        return 5001
    return parsed


def _normalized_base_url(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text if text.endswith("/") else f"{text}/"


def _configured_secret_keys(config: Dict[str, Any]) -> List[str]:
    flattened = _flatten_keys(config)
    return sorted(
        key
        for key, value in flattened.items()
        if value not in (None, "") and any(marker in key.lower() for marker in SECRET_MARKERS)
    )


def _flatten_keys(config: Dict[str, Any]) -> Dict[str, Any]:
    flattened: Dict[str, Any] = {}
    for key, value in config.items():
        if isinstance(value, dict):
            for nested_key, nested_value in value.items():
                flattened[f"{key}_{nested_key}"] = nested_value
        else:
            flattened[key] = value
    return flattened


def _list_config(config: Dict[str, Any], *keys: str) -> List[str]:
    value = _config_value(config, *keys)
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        raw_items = value
    else:
        raw_items = str(value).replace("\n", ",").replace(";", ",").split(",")
    return [str(item).strip() for item in raw_items if str(item).strip()]


def _has_value(config: Dict[str, Any], *keys: str) -> bool:
    return _config_value(config, *keys) not in (None, "")


def _config_value(config: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        value = config.get(key)
        if value not in (None, ""):
            return value
    for key in keys:
        if "." in key:
            section, option = key.split(".", 1)
        elif "_" in key:
            section, option = key.split("_", 1)
        else:
            continue
        section_values = config.get(section)
        if isinstance(section_values, dict):
            value = section_values.get(option)
            if value not in (None, ""):
                return value
    return default
