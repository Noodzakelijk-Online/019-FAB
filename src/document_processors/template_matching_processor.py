import json
import os
import re
from typing import Any, Dict, Iterable, Optional

from src.document_processors.base import BaseProcessor
from src.document_processors.financial_field_extractor import FinancialFieldExtractor

class TemplateMatchingProcessor(BaseProcessor):
    """Apply governed, user-owned vendor templates to OCR text."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.template_errors = []
        self.templates = self._load_templates()

    def process_document(self, document_path: str, ocr_text: str) -> Dict[str, Any]:
        extracted_data: Dict[str, Any] = {}
        confidences: Dict[str, float] = {}
        evidence: Dict[str, Any] = {}
        for vendor, template_config in self.templates.items():
            keyword_pattern = self._keyword_pattern(template_config.get("keywords"))
            if not keyword_pattern or not self._search(keyword_pattern, ocr_text, vendor, "keywords"):
                continue

            extracted_data["vendor_name"] = vendor
            confidences["vendor_name"] = 0.95
            evidence["vendor_name"] = {
                "source": "vendor_template",
                "template": vendor,
            }

            configured_patterns = template_config.get("extraction_patterns")
            if configured_patterns is None:
                extraction_patterns: Dict[str, Any] = {}
            elif isinstance(configured_patterns, dict):
                extraction_patterns = dict(configured_patterns)
            else:
                self.template_errors.append({
                    "path": f"{vendor}.extraction_patterns",
                    "error": "extraction_patterns must be an object",
                })
                extraction_patterns = {}
            if template_config.get("total_pattern") and "total_amount" not in extraction_patterns:
                extraction_patterns["total_amount"] = template_config["total_pattern"]
            for field, pattern in extraction_patterns.items():
                value = self._extract_field(vendor, str(field), pattern, ocr_text)
                if value is None:
                    continue
                extracted_data[str(field)] = value
                confidences[str(field)] = 0.92
                evidence[str(field)] = {
                    "source": "vendor_template",
                    "template": vendor,
                }

            line_items = self._extract_line_items(vendor, template_config, ocr_text)
            if line_items:
                extracted_data["line_items"] = line_items
                confidences["line_items"] = 0.88
                evidence["line_items"] = {
                    "source": "vendor_template",
                    "template": vendor,
                    "count": len(line_items),
                }
            break

        return {
            "ocr_text": ocr_text,
            "extracted_data": extracted_data,
            "field_confidences": confidences,
            "field_evidence": evidence,
            "language": "",
        }

    def _load_templates(self) -> Dict[str, Dict[str, Any]]:
        templates: Dict[str, Dict[str, Any]] = {}
        template_directory = str(
            self.config.get("template_matching_templates_dir") or ""
        ).strip()
        if template_directory and os.path.isdir(template_directory):
            for filename in sorted(os.listdir(template_directory)):
                if filename.lower().endswith(".json"):
                    self._merge_templates(
                        templates,
                        self._load_json(os.path.join(template_directory, filename)),
                    )

        template_file = str(self.config.get("vendor_templates_file") or "").strip()
        if template_file:
            self._merge_templates(templates, self._load_json(template_file))

        self._merge_templates(templates, self.config.get("vendor_templates"))
        return templates

    def _load_json(self, path: str) -> Any:
        if not os.path.isfile(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            self.template_errors.append({"path": path, "error": str(exc)})
            return None

    def _merge_templates(self, target: Dict[str, Dict[str, Any]], source: Any) -> None:
        if source is None:
            return
        if isinstance(source, dict) and isinstance(source.get("templates"), dict):
            source = source["templates"]
        if not isinstance(source, dict):
            self.template_errors.append({
                "path": "configuration",
                "error": "templates must be an object",
            })
            return
        for vendor, template in source.items():
            if not str(vendor).strip() or not isinstance(template, dict):
                self.template_errors.append({
                    "path": str(vendor),
                    "error": "template must be an object",
                })
                continue
            target[str(vendor).strip()] = dict(template)

    @staticmethod
    def _keyword_pattern(keywords: Any) -> Optional[str]:
        if isinstance(keywords, str) and keywords.strip():
            return keywords
        if isinstance(keywords, (list, tuple)):
            values = [str(value).strip() for value in keywords if str(value).strip()]
            if values:
                return "(?:" + "|".join(re.escape(value) for value in values) + ")"
        return None

    def _search(self, pattern: str, text: str, vendor: str, field: str) -> Optional[re.Match[str]]:
        try:
            return re.search(pattern, text or "", flags=re.IGNORECASE | re.MULTILINE)
        except re.error as exc:
            self.template_errors.append({"path": f"{vendor}.{field}", "error": str(exc)})
            return None

    def _extract_field(self, vendor: str, field: str, pattern: Any, text: str) -> Any:
        if not isinstance(pattern, str) or not pattern:
            self.template_errors.append({
                "path": f"{vendor}.{field}",
                "error": "pattern must be a string",
            })
            return None
        match = self._search(pattern, text, vendor, field)
        if not match:
            return None
        value = match.groupdict().get(field)
        if value is None:
            value = match.group(1) if match.lastindex else match.group(0)
        value = str(value).strip()
        if field in {"total_amount", "vat_amount", "amount", "total"}:
            return FinancialFieldExtractor._parse_amount(value)
        if field in {"transaction_date", "invoice_date", "date"}:
            return FinancialFieldExtractor._normalize_date(value)
        if field == "currency":
            return {"EURO": "EUR", "US$": "USD", "$": "USD", "€": "EUR", "£": "GBP"}.get(
                value.upper(), value.upper()
            )
        return value

    def _extract_line_items(self, vendor: str, template: Dict[str, Any], text: str) -> list[Dict[str, Any]]:
        pattern = template.get("line_item_pattern")
        if not isinstance(pattern, str) or not pattern:
            return []
        try:
            matches: Iterable[re.Match[str]] = re.finditer(
                pattern,
                text or "",
                flags=re.IGNORECASE | re.MULTILINE,
            )
            items = []
            for match in matches:
                groups = match.groupdict()
                description = groups.get("description")
                total = groups.get("total")
                if description is None and match.lastindex and match.lastindex >= 2:
                    description, total = match.group(1), match.group(2)
                parsed_total = FinancialFieldExtractor._parse_amount(str(total or ""))
                normalized_description = str(description or "").strip().rstrip(":")
                if normalized_description.lower() in {
                    "total",
                    "totaal",
                    "vat",
                    "btw",
                    "tax",
                    "amount due",
                    "te betalen",
                }:
                    continue
                if normalized_description and parsed_total is not None:
                    items.append({"description": normalized_description, "total": parsed_total})
                if len(items) >= 100:
                    break
            return items
        except re.error as exc:
            self.template_errors.append({"path": f"{vendor}.line_item_pattern", "error": str(exc)})
            return []


