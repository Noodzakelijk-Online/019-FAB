import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


class FinancialFieldExtractor:
    """Extracts core bookkeeping fields from OCR text with simple confidence hints."""

    AMOUNT_PATTERN = r"(?P<currency>[€$£])?\s*(?P<amount>-?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})|-?\d+(?:[.,]\d{2}))"
    DATE_PATTERNS = [
        r"\b(?P<date>\d{4}[-/]\d{1,2}[-/]\d{1,2})\b",
        r"\b(?P<date>\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b",
        r"\b(?P<date>\d{1,2}\s+(?:jan|feb|mrt|mar|apr|mei|may|jun|jul|aug|sep|okt|oct|nov|dec)[a-z]*\s+\d{2,4})\b",
    ]
    TOTAL_LABELS = ["totaal", "total", "amount due", "te betalen", "grand total", "saldo"]
    VAT_LABELS = ["btw", "vat", "tax", "omzetbelasting"]

    def extract(self, text: str) -> Dict[str, Any]:
        text = text or ""
        vendor_name, vendor_confidence = self._extract_vendor(text)
        date_value, date_confidence = self._extract_date(text)
        total_amount, currency, amount_confidence = self._extract_total_amount(text)
        vat_amount, vat_confidence = self._extract_vat_amount(text)
        invoice_number, invoice_confidence = self._extract_reference(text, ["invoice", "factuur", "invoice no", "factuurnummer"])
        receipt_number, receipt_confidence = self._extract_reference(text, ["receipt", "bon", "kassabon"])
        order_number, order_confidence = self._extract_reference(text, ["order", "bestel", "ordernummer", "bestelnummer"])
        line_items = self.extract_line_items(text)

        extracted_data = {
            "vendor_name": vendor_name,
            "transaction_date": date_value,
            "total_amount": total_amount,
            "currency": currency or "EUR",
            "vat_amount": vat_amount,
            "invoice_number": invoice_number,
            "receipt_number": receipt_number,
            "order_number": order_number,
            "line_items": line_items,
        }
        field_confidences = {
            "vendor_name": vendor_confidence,
            "transaction_date": date_confidence,
            "total_amount": amount_confidence,
            "currency": 0.85 if currency else 0.55,
            "vat_amount": vat_confidence,
            "invoice_number": invoice_confidence,
            "receipt_number": receipt_confidence,
            "order_number": order_confidence,
            "line_items": 0.65 if line_items else 0.2,
        }

        return {
            "extracted_data": extracted_data,
            "field_confidences": field_confidences,
        }

    def extract_line_items(self, text: str) -> List[Dict[str, Any]]:
        line_items: List[Dict[str, Any]] = []
        for raw_line in (text or "").splitlines():
            line = raw_line.strip()
            if len(line) < 5:
                continue
            if any(label in line.lower() for label in self.TOTAL_LABELS + self.VAT_LABELS):
                continue
            match = re.search(r"^(?P<description>.+?)\s+(?P<amount>-?\d+[.,]\d{2})$", line)
            if not match:
                continue
            description = match.group("description").strip(" .:-")
            amount = self._parse_amount(match.group("amount"))
            if description and amount is not None:
                line_items.append({"description": description, "total": amount})
        return line_items[:100]

    def _extract_vendor(self, text: str) -> Tuple[Optional[str], float]:
        for line in text.splitlines():
            cleaned = line.strip()
            if not cleaned:
                continue
            if self._looks_like_noise(cleaned):
                continue
            return cleaned[:120], 0.65
        return None, 0.0

    def _extract_date(self, text: str) -> Tuple[Optional[str], float]:
        for pattern in self.DATE_PATTERNS:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                raw_date = match.group("date")
                normalized = self._normalize_date(raw_date)
                return normalized or raw_date, 0.8 if normalized else 0.6
        return None, 0.0

    def _extract_total_amount(self, text: str) -> Tuple[Optional[float], Optional[str], float]:
        candidates: List[Tuple[float, Optional[str], float]] = []
        lines = text.splitlines()
        for line in lines:
            lowered = line.lower()
            line_weight = 0.95 if any(label in lowered for label in self.TOTAL_LABELS) else 0.55
            for match in re.finditer(self.AMOUNT_PATTERN, line):
                amount = self._parse_amount(match.group("amount"))
                if amount is None:
                    continue
                currency = self._currency_from_symbol(match.group("currency"))
                candidates.append((amount, currency, line_weight))

        if not candidates:
            return None, None, 0.0

        labelled = [candidate for candidate in candidates if candidate[2] >= 0.9]
        chosen = max(labelled or candidates, key=lambda candidate: abs(candidate[0]))
        return chosen[0], chosen[1], chosen[2]

    def _extract_vat_amount(self, text: str) -> Tuple[Optional[float], float]:
        for line in text.splitlines():
            if any(label in line.lower() for label in self.VAT_LABELS):
                amounts = [self._parse_amount(match.group("amount")) for match in re.finditer(self.AMOUNT_PATTERN, line)]
                amounts = [amount for amount in amounts if amount is not None]
                if amounts:
                    return amounts[-1], 0.75
        return None, 0.0

    def _extract_reference(self, text: str, labels: List[str]) -> Tuple[Optional[str], float]:
        for label in labels:
            pattern = rf"\b{re.escape(label)}\b\s*(?:nr|no|number|nummer)?\s*[:#-]?\s*(?P<ref>[A-Z0-9][A-Z0-9\-/]{{3,}})"
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group("ref"), 0.8
        return None, 0.0

    @staticmethod
    def _parse_amount(raw_amount: str) -> Optional[float]:
        if not raw_amount:
            return None
        value = raw_amount.strip().replace(" ", "")
        if "," in value and "." in value:
            if value.rfind(",") > value.rfind("."):
                value = value.replace(".", "").replace(",", ".")
            else:
                value = value.replace(",", "")
        else:
            value = value.replace(",", ".")
        try:
            return float(value)
        except ValueError:
            return None

    @staticmethod
    def _currency_from_symbol(symbol: Optional[str]) -> Optional[str]:
        return {"€": "EUR", "$": "USD", "£": "GBP"}.get(symbol or "")

    @staticmethod
    def _normalize_date(raw_date: str) -> Optional[str]:
        candidates = [
            "%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y", "%d-%m-%y", "%d/%m/%y",
        ]
        for fmt in candidates:
            try:
                return datetime.strptime(raw_date, fmt).date().isoformat()
            except ValueError:
                continue
        return None

    @staticmethod
    def _looks_like_noise(line: str) -> bool:
        lowered = line.lower()
        if any(token in lowered for token in ["invoice", "factuur", "receipt", "kassabon", "total", "totaal"]):
            return True
        if re.search(r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}", line):
            return True
        if re.search(r"\d+[.,]\d{2}", line):
            return True
        return False
