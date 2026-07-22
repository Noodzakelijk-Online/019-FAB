import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


class FinancialFieldExtractor:
    """Extract core bookkeeping fields from OCR text with confidence hints."""

    AMOUNT_PATTERN = (
        r"(?P<sign>-)?\s*"
        r"(?:(?P<currency_code>US\$|EUR|USD|GBP)\s*)?"
        r"(?P<currency_symbol>[\u20ac$\u00a3])?\s*"
        r"(?P<amount>\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})|\d+(?:[.,]\d{2}))"
    )
    MONTH_NAMES = (
        "jan(?:uary|uari)?|feb(?:ruary|ruari)?|mar(?:ch)?|maart|mrt|apr(?:il)?|"
        "may|mei|jun(?:e|i)?|jul(?:y|i)?|aug(?:ust|ustus)?|sep(?:tember)?|"
        "oct(?:ober)?|okt(?:ober)?|nov(?:ember)?|dec(?:ember)?"
    )
    DATE_PATTERNS = [
        r"\b(?P<date>\d{4}[-/]\d{1,2}[-/]\d{1,2})\b",
        r"\b(?P<date>\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b",
        rf"\b(?P<date>\d{{1,2}}\s+(?:{MONTH_NAMES})\s+\d{{2,4}})\b",
        rf"\b(?P<date>(?:{MONTH_NAMES})\s+\d{{1,2}},?\s+\d{{2,4}})\b",
    ]
    TOTAL_LABELS = [
        "totaal",
        "total",
        "amount due",
        "amount paid",
        "amount charged",
        "paid today",
        "factuurbedrag",
        "te betalen",
        "grand total",
        "saldo",
    ]
    VAT_LABELS = ["btw", "vat", "tax", "omzetbelasting"]
    DATE_PRIMARY_LABELS = (
        "date paid",
        "paid on",
        "date of issue",
        "invoice date",
        "factuurdatum",
        "datum:",
        "besteldatum",
    )
    DATE_SECONDARY_LABELS = (
        "wordt rond",
        "afgeschreven",
        "date due",
        "due",
    )
    KNOWN_VENDOR_PATTERNS = (
        (r"\bbrainforce\s+co\.?\b", "BrainForce Co."),
        (r"\bgetimg\.ai\b", "getimg.ai"),
        (r"\bslack\b", "Slack"),
        (r"\bt-?mobile\b", "T-Mobile"),
        (r"\bvisser\s+assen\b", "Visser Assen"),
    )

    def extract(self, text: str) -> Dict[str, Any]:
        text = text or ""
        vendor_name, vendor_confidence = self._extract_vendor(text)
        date_value, date_confidence = self._extract_date(text)
        total_amount, currency, amount_confidence = self._extract_total_amount(text)
        vat_amount, vat_confidence = self._extract_vat_amount(text)
        invoice_number, invoice_confidence = self._extract_reference(
            text,
            ["invoice", "factuur", "invoice no", "factuurnummer"],
        )
        receipt_number, receipt_confidence = self._extract_reference(
            text,
            ["receipt", "bon", "kassabon"],
        )
        order_number, order_confidence = self._extract_reference(
            text,
            ["order", "bestel", "ordernummer", "bestelnummer"],
        )
        line_items = self.extract_line_items(text)

        extracted_data = {
            "vendor_name": vendor_name,
            "transaction_date": date_value,
            "total_amount": total_amount,
            "currency": currency or self._currency_from_text(text) or "EUR",
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
            "currency": 0.85 if currency or self._currency_from_text(text) else 0.55,
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
            match = re.search(
                r"^(?P<description>.+?)\s+(?:EUR|USD|GBP|US\$)?\s*"
                r"[\u20ac$\u00a3]?\s*(?P<amount>-?\d+[.,]\d{2})$",
                line,
                flags=re.IGNORECASE,
            )
            if not match:
                continue
            description = match.group("description").strip(" .:-")
            amount = self._parse_amount(match.group("amount"))
            if description and amount is not None:
                line_items.append({"description": description, "total": amount})
        return line_items[:100]

    def _extract_vendor(self, text: str) -> Tuple[Optional[str], float]:
        explicit = re.search(
            r"\b(?:receipt|invoice)\s+from\s+(?P<vendor>[^\r\n]{2,120})",
            text,
            flags=re.IGNORECASE,
        )
        if explicit:
            explicit_vendor = explicit.group("vendor").strip(" .:-")
            for pattern, vendor in self.KNOWN_VENDOR_PATTERNS:
                if re.search(pattern, explicit_vendor, flags=re.IGNORECASE):
                    return vendor, 0.95
            return explicit_vendor, 0.95

        for pattern, vendor in self.KNOWN_VENDOR_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE):
                return vendor, 0.9

        for line in text.splitlines():
            cleaned = line.strip()
            if len(cleaned) < 3:
                continue
            if self._looks_like_noise(cleaned):
                continue
            return cleaned[:120], 0.65
        return None, 0.0

    def _extract_date(self, text: str) -> Tuple[Optional[str], float]:
        candidates: List[Tuple[str, float, int]] = []
        previous_nonempty = ""
        for line_index, line in enumerate(text.splitlines()):
            context = f"{previous_nonempty} {line}".lower()
            for pattern in self.DATE_PATTERNS:
                for match in re.finditer(pattern, line, flags=re.IGNORECASE):
                    normalized = self._normalize_date(match.group("date"))
                    if not normalized:
                        continue
                    if any(label in context for label in self.DATE_PRIMARY_LABELS):
                        confidence = 0.95
                    elif any(label in context for label in self.DATE_SECONDARY_LABELS):
                        confidence = 0.82
                    else:
                        confidence = 0.65
                    candidates.append((normalized, confidence, line_index))
            if line.strip():
                previous_nonempty = line
        if candidates:
            chosen = max(candidates, key=lambda candidate: (candidate[1], -candidate[2]))
            return chosen[0], chosen[1]
        return None, 0.0

    def _extract_total_amount(self, text: str) -> Tuple[Optional[float], Optional[str], float]:
        candidates: List[Tuple[float, Optional[str], float, int]] = []
        previous_nonempty = ""
        has_total_label = any(label in text.lower() for label in self.TOTAL_LABELS)
        for line_index, line in enumerate(text.splitlines()):
            lowered = line.lower()
            context = f"{previous_nonempty} {lowered}"
            if any(label in lowered for label in self.TOTAL_LABELS):
                line_weight = 0.95
            elif any(label in context for label in self.TOTAL_LABELS):
                line_weight = 0.88
            else:
                line_weight = 0.55
            for match in re.finditer(self.AMOUNT_PATTERN, line, flags=re.IGNORECASE):
                amount = self._amount_from_match(match)
                if amount is None:
                    continue
                currency = self._currency_from_tokens(
                    match.group("currency_code"),
                    match.group("currency_symbol"),
                )
                candidates.append((amount, currency, line_weight, line_index))
            if line.strip():
                previous_nonempty = lowered

        if not candidates:
            return None, None, 0.0

        labelled = [candidate for candidate in candidates if candidate[2] >= 0.85]
        if labelled:
            highest_confidence = max(candidate[2] for candidate in labelled)
            finalists = [candidate for candidate in labelled if candidate[2] == highest_confidence]
            chosen = max(finalists, key=lambda candidate: candidate[3])
        else:
            unique_amounts = {round(abs(candidate[0]), 2) for candidate in candidates}
            if has_total_label and len(unique_amounts) == 1:
                amount, currency, _, line_index = candidates[-1]
                chosen = (amount, currency, 0.85, line_index)
            else:
                chosen = max(candidates, key=lambda candidate: abs(candidate[0]))
        return chosen[0], chosen[1], chosen[2]

    def _extract_vat_amount(self, text: str) -> Tuple[Optional[float], float]:
        for line in text.splitlines():
            if re.search(r"\b(?:btw|vat|tax|omzetbelasting)\b", line, flags=re.IGNORECASE):
                amounts = [
                    self._amount_from_match(match)
                    for match in re.finditer(self.AMOUNT_PATTERN, line, flags=re.IGNORECASE)
                ]
                amounts = [amount for amount in amounts if amount is not None]
                if amounts:
                    return amounts[-1], 0.75
        return None, 0.0

    def _extract_reference(self, text: str, labels: List[str]) -> Tuple[Optional[str], float]:
        for label in labels:
            pattern = (
                rf"\b{re.escape(label)}\b\s*(?:nr|no|number|nummer)?\s*[:#-]?\s*"
                rf"(?P<ref>[A-Z0-9][A-Z0-9\-/]{{3,}})"
            )
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group("ref"), 0.8
        return None, 0.0

    @classmethod
    def _amount_from_match(cls, match: re.Match) -> Optional[float]:
        amount = cls._parse_amount(match.group("amount"))
        if amount is not None and match.group("sign") == "-":
            return -abs(amount)
        return amount

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
    def _currency_from_tokens(code: Optional[str], symbol: Optional[str]) -> Optional[str]:
        normalized_code = str(code or "").upper()
        if normalized_code:
            return {"US$": "USD"}.get(normalized_code, normalized_code)
        return {"\u20ac": "EUR", "$": "USD", "\u00a3": "GBP"}.get(symbol or "")

    @staticmethod
    def _currency_from_text(text: str) -> Optional[str]:
        if re.search(r"(?:\bEUR\b|\u20ac)", text, flags=re.IGNORECASE):
            return "EUR"
        if re.search(r"(?:\bUSD\b|US\$|\$)", text, flags=re.IGNORECASE):
            return "USD"
        if re.search(r"(?:\bGBP\b|\u00a3)", text, flags=re.IGNORECASE):
            return "GBP"
        return None

    @staticmethod
    def _normalize_date(raw_date: str) -> Optional[str]:
        normalized_date = re.sub(r"\s+", " ", str(raw_date or "").strip().rstrip(","))
        month_replacements = {
            "januari": "January",
            "februari": "February",
            "maart": "March",
            "mrt": "Mar",
            "april": "April",
            "mei": "May",
            "juni": "June",
            "juli": "July",
            "augustus": "August",
            "september": "September",
            "oktober": "October",
            "okt": "Oct",
            "november": "November",
            "december": "December",
        }
        for source, target in month_replacements.items():
            normalized_date = re.sub(
                rf"\b{source}\b",
                target,
                normalized_date,
                flags=re.IGNORECASE,
            )
        candidates = [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%d-%m-%y",
            "%d/%m/%y",
            "%m-%d-%Y",
            "%m/%d/%Y",
            "%m-%d-%y",
            "%m/%d/%y",
            "%d %B %Y",
            "%d %b %Y",
            "%B %d, %Y",
            "%b %d, %Y",
            "%B %d %Y",
            "%b %d %Y",
        ]
        for fmt in candidates:
            try:
                return datetime.strptime(normalized_date, fmt).date().isoformat()
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
