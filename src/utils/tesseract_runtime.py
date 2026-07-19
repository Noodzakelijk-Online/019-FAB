from __future__ import annotations

import glob
import os
import re
import shutil
from typing import Any, Dict, List, Optional


WINDOWS_TESSERACT_PATHS = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
)


def resolve_tesseract_command(config: Optional[Dict[str, Any]] = None) -> Optional[str]:
    config = config or {}
    configured = str(
        config.get("tesseract_cmd")
        or config.get("ocr_tesseract_cmd")
        or "tesseract"
    ).strip()
    resolved = _resolve_command(configured)
    if resolved:
        return resolved

    candidates = list(WINDOWS_TESSERACT_PATHS)
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidates.append(os.path.join(local_app_data, "Programs", "Tesseract-OCR", "tesseract.exe"))
    return next((path for path in candidates if os.path.isfile(path)), None)


def resolve_tessdata_dir(config: Optional[Dict[str, Any]] = None) -> Optional[str]:
    config = config or {}
    configured = str(
        config.get("tesseract_data_dir")
        or config.get("ocr_tesseract_data_dir")
        or ""
    ).strip()
    if configured:
        path = os.path.abspath(os.path.expandvars(os.path.expanduser(configured)))
        return path if os.path.isdir(path) else None

    command = resolve_tesseract_command(config)
    if command and os.path.isabs(command):
        sibling = os.path.join(os.path.dirname(command), "tessdata")
        if os.path.isdir(sibling):
            return sibling
    return None


def resolve_poppler_path(config: Optional[Dict[str, Any]] = None) -> Optional[str]:
    config = config or {}
    configured = str(config.get("poppler_path") or config.get("pdf_poppler_path") or "").strip()
    if configured:
        path = os.path.abspath(os.path.expandvars(os.path.expanduser(configured)))
        if any(os.path.isfile(os.path.join(path, name)) for name in ("pdftoppm.exe", "pdftoppm")):
            return path

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        pattern = os.path.join(
            local_app_data,
            "Microsoft",
            "WinGet",
            "Packages",
            "oschwartz10612.Poppler_*",
            "poppler-*",
            "Library",
            "bin",
            "pdftoppm.exe",
        )
        matches = sorted(glob.glob(pattern), reverse=True)
        if matches:
            return os.path.dirname(matches[0])

    resolved = shutil.which("pdftoppm")
    if resolved and not (os.name == "nt" and resolved.lower().endswith((".cmd", ".bat"))):
        return os.path.dirname(os.path.abspath(resolved))
    return None


def configured_tesseract_languages(config: Optional[Dict[str, Any]] = None) -> List[str]:
    config = config or {}
    raw = str(config.get("tesseract_lang") or config.get("ocr_tesseract_lang") or "eng")
    languages = []
    for value in re.split(r"[+,;\s]+", raw):
        normalized = re.sub(r"[^A-Za-z0-9_]", "", value).lower()
        if normalized and normalized not in languages:
            languages.append(normalized)
    return languages or ["eng"]


def available_tesseract_languages(config: Optional[Dict[str, Any]] = None) -> List[str]:
    tessdata_dir = resolve_tessdata_dir(config)
    if not tessdata_dir:
        return []
    return sorted({
        os.path.splitext(name)[0]
        for name in os.listdir(tessdata_dir)
        if name.lower().endswith(".traineddata")
    })


def tesseract_cli_config(config: Optional[Dict[str, Any]] = None, extra: str = "") -> str:
    tessdata_dir = resolve_tessdata_dir(config)
    values = []
    if tessdata_dir:
        if os.name == "nt":
            # pytesseract retains quotes in Windows command arguments. The
            # environment variable supports paths containing spaces reliably.
            os.environ["TESSDATA_PREFIX"] = tessdata_dir
        else:
            escaped = tessdata_dir.replace('"', '\\"')
            values.append(f'--tessdata-dir "{escaped}"')
    if extra.strip():
        values.append(extra.strip())
    return " ".join(values)


def _resolve_command(command: str) -> Optional[str]:
    if not command:
        return None
    if os.path.isabs(command):
        expanded = os.path.abspath(os.path.expandvars(os.path.expanduser(command)))
        return expanded if os.path.isfile(expanded) else None
    return shutil.which(command)
