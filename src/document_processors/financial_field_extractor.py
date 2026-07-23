import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from src.validation.financial_consistency import valid_vat_amount


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
        "may|mei|jun(?:e|i)?|jur|jul(?:y|i)?|aug(?:ust|ustus)?|sep(?:tember)?|"
        "oct(?:ober)?|okt(?:ober)?|nov(?:ember)?|dec(?:ember)?"
    )
    DATE_PATTERNS = [
        r"\b(?P<date>\d{4}[-/]\d{1,2}[-/]\d{1,2})\b",
        r"\b(?P<date>\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b",
        r"\b(?P<date>\d{1,2}\.\d{1,2}\.\d{2,4})\b",
        rf"\b(?P<date>\d{{4}}[-\s]+(?:{MONTH_NAMES})[-\s]+\d{{1,2}})\b",
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
    PAYMENT_TOTAL_LABELS = [
        "pin",
        "vpay",
        "bankpas",
        "amount charged",
        "amount paid",
        "paid today",
        "betaling",
        "betaald",
    ]
    ROUNDING_TOTAL_LABELS = [
        "totaal na afronding",
        "total after rounding",
    ]
    REFUND_TOTAL_LABELS = [
        "terug (",
        "terug {",
        "terugbetaling",
        "refund",
        "refunded",
    ]
    NON_PAYABLE_TOTAL_PHRASES = [
        "totaal prijsvoordeel",
        "totale korting",
        "total discount",
        "total savings",
    ]
    NON_PAYABLE_AMOUNT_LABELS = [
        "discount",
        "korting",
        "prijsvoordeel",
        "savings",
        "besparing",
        "verzekerde bedrag",
        "verzekerde bedragen",
        "verzekerd bedrag",
        "cataloguswaarde",
        "eigen risico",
        "schade",
        "dekking",
        "dekkingsbedrag",
        "coverage limit",
        "insured amount",
        "policy limit",
        "sum insured",
        "bijstandsnorm",
        "vrij te laten vermogen",
        "vrijlatingsgrens",
        "vermogen is",
    ]
    VAT_LABELS = ["btw", "vat", "tax", "omzetbelasting"]
    DATE_PRIMARY_LABELS = (
        "date paid",
        "paid on",
        "date of issue",
        "invoice date",
        "factuurdatum",
        "datum",
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
        (r"\bpraxis\b", "Praxis"),
        (r"\bhornbach(?:\s+b(?:ouwmarkt)?\.?\s*v\.?)?\b", "Hornbach Bouwmarkt B.V."),
        (r"\baction\b", "Action"),
        (r"\bodido\b", "Odido"),
        (r"\bvodafone\b", "Vodafone"),
        (r"\bziggo\b", "Ziggo"),
        (r"\bvisser\s+assen\b", "Visser Assen"),
        (r"\b(?:merchant|herchant)\s*[:.]?\s*1770001\b", "Lidl"),
    )
    VENDOR_HEADER_PATTERNS = (
        (
            r"^\W*(?:aaction|aagtion|aagction|agtion)\W*$",
            "Action",
            0.85,
        ),
        (r"^\W*albert\s+heijn\b", None, 0.9),
        (r"^\W*sun\s+wah\s+supermarket\b", "Sun Wah Supermarket", 0.9),
        (r"^\W*so\s*low\b", "SoLow", 0.9),
        (r"^\W*2\s*switch\b", "2Switch", 0.9),
        (r"^\W*mantel\b", "Mantel", 0.9),
    )

    def extract(self, text: str) -> Dict[str, Any]:
        text = text or ""
        vendor_name, vendor_confidence, vendor_evidence = self._extract_vendor(text)
        date_value, date_confidence = self._extract_date(text)
        total_amount, currency, amount_confidence = self._extract_total_amount(text)
        vat_amount, vat_confidence = self._extract_vat_amount(text, total_amount)
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
            "field_evidence": {
                "vendor_name": vendor_evidence,
            } if vendor_name else {},
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

    def _extract_vendor(self, text: str) -> Tuple[Optional[str], float, Dict[str, Any]]:
        explicit = re.search(
            r"\b(?:receipt|invoice)\s+from\s+(?P<vendor>[^\r\n]{2,120})",
            text,
            flags=re.IGNORECASE,
        )
        if explicit:
            explicit_vendor = explicit.group("vendor").strip(" .:-")
            for pattern, vendor in self.KNOWN_VENDOR_PATTERNS:
                if re.search(pattern, explicit_vendor, flags=re.IGNORECASE):
                    return vendor, 0.95, {
                        "source": "explicit_receipt_vendor",
                        "matchedText": explicit_vendor,
                        "canonicalized": vendor != explicit_vendor,
                    }
            return explicit_vendor, 0.95, {
                "source": "explicit_receipt_vendor",
                "matchedText": explicit_vendor,
                "canonicalized": False,
            }

        for pattern, vendor in self.KNOWN_VENDOR_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE):
                return vendor, 0.9, {
                    "source": "known_vendor_pattern",
                    "canonicalized": True,
                }

        nonempty_lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]
        header_lines = nonempty_lines[:6]
        for cleaned in header_lines:
            for pattern, vendor, confidence in self.VENDOR_HEADER_PATTERNS:
                if re.search(pattern, cleaned, flags=re.IGNORECASE):
                    resolved_vendor = vendor or cleaned[:120]
                    return resolved_vendor, confidence, {
                        "source": "receipt_header_vendor_pattern",
                        "matchedHeader": cleaned[:120],
                        "canonicalized": resolved_vendor != cleaned[:120],
                    }

        for cleaned in nonempty_lines:
            if len(cleaned) < 3:
                continue
            if self._looks_like_noise(cleaned):
                continue
            return cleaned[:120], 0.65, {
                "source": "first_non_noise_header_line",
                "matchedHeader": cleaned[:120],
                "canonicalized": False,
            }
        return None, 0.0, {}

    def _extract_date(self, text: str) -> Tuple[Optional[str], float]:
        candidates: List[Tuple[str, float, int]] = []
        previous_nonempty = ""
        for line_index, line in enumerate(text.splitlines()):
            search_line = re.sub(
                r"(?<=[A-Za-z])[\]}](?=\s|\d)",
                " ",
                line,
            )
            context = f"{previous_nonempty} {search_line}".lower()
            for pattern in self.DATE_PATTERNS:
                for match in re.finditer(pattern, search_line, flags=re.IGNORECASE):
                    normalized = self._normalize_date(match.group("date"))
                    if not normalized or not self._plausible_transaction_date(normalized):
                        continue
                    if (
                        any(label in context for label in self.DATE_PRIMARY_LABELS)
                        or re.search(r"\bd?atum\b", context)
                    ):
                        confidence = 0.95
                    elif any(label in context for label in self.DATE_SECONDARY_LABELS):
                        confidence = 0.82
                    else:
                        confidence = 0.65
                    candidates.append((normalized, confidence, line_index))
            if search_line.strip():
                previous_nonempty = search_line
        if candidates:
            chosen = max(candidates, key=lambda candidate: (candidate[1], -candidate[2]))
            confidence = chosen[1]
            distinct_dates = {candidate[0] for candidate in candidates}
            if confidence == 0.65 and len(distinct_dates) == 1:
                confidence = 0.8
            return chosen[0], confidence
        return None, 0.0

    def _extract_total_amount(self, text: str) -> Tuple[Optional[float], Optional[str], float]:
        candidates: List[Tuple[float, Optional[str], float, int, int]] = []
        vat_candidates: List[Tuple[float, Optional[str], float, int, int]] = []
        previous_nonempty = ""
        pending_total_label = False
        normalized_text = "\n".join(
            self._normalize_ocr_amount_labels(line)
            for line in text.splitlines()
        )
        has_total_label = any(
            label in normalized_text
            for label in self.TOTAL_LABELS
        )
        for line_index, line in enumerate(text.splitlines()):
            lowered = self._normalize_ocr_amount_labels(line)
            line_amounts: List[Tuple[float, Optional[str], int]] = []
            for match in re.finditer(self.AMOUNT_PATTERN, line, flags=re.IGNORECASE):
                if re.match(r"\s*%", line[match.end():]):
                    continue
                amount = self._amount_from_match(match)
                if amount is None:
                    continue
                currency = self._currency_from_tokens(
                    match.group("currency_code"),
                    match.group("currency_symbol"),
                )
                line_amounts.append((amount, currency, match.start()))
            if not line_amounts:
                if line.strip():
                    pending_total_label = any(
                        label in lowered
                        for label in self.TOTAL_LABELS + self.PAYMENT_TOTAL_LABELS
                    )
                    previous_nonempty = lowered
                continue

            had_pending_total_label = pending_total_label
            pending_total_label = False
            has_line_total_label = any(label in lowered for label in self.TOTAL_LABELS)
            non_payable_total = any(
                phrase in lowered for phrase in self.NON_PAYABLE_TOTAL_PHRASES
            )
            if non_payable_total or (
                not has_line_total_label
                and any(label in lowered for label in self.NON_PAYABLE_AMOUNT_LABELS)
            ):
                if line.strip():
                    previous_nonempty = lowered
                continue

            has_rounding_label = any(label in lowered for label in self.ROUNDING_TOTAL_LABELS)
            has_payment_label = any(
                re.search(rf"\b{re.escape(label)}\b", lowered)
                for label in self.PAYMENT_TOTAL_LABELS
            )
            has_refund_label = any(label in lowered for label in self.REFUND_TOTAL_LABELS)
            payment_metadata_line = bool(
                re.search(
                    r"\bauth(?:orization)?\.?\s*code\b|\bautorisatiecode\b",
                    lowered,
                )
            )
            vat_summary_line = self._is_vat_summary_context(lowered)
            vat_summary_context = vat_summary_line or self._is_vat_summary_context(
                previous_nonempty
            )

            if has_rounding_label:
                amount, currency, position = line_amounts[-1]
                candidates.append((amount, currency, 1.0, line_index, position))
            elif has_refund_label:
                amount, currency, position = line_amounts[-1]
                candidates.append((-abs(amount), currency, 0.997, line_index, position))
            elif has_payment_label:
                amount, currency, position = line_amounts[-1]
                candidates.append((amount, currency, 0.997, line_index, position))
            elif has_line_total_label and not vat_summary_line and len(line_amounts) == 1:
                amount, currency, position = line_amounts[0]
                candidates.append((amount, currency, 0.999, line_index, position))
            elif has_line_total_label or vat_summary_context:
                vat_candidate = self._vat_summary_total(
                    line_amounts,
                    line_text=lowered,
                    previous_line=previous_nonempty,
                )
                if vat_candidate:
                    amount, currency, confidence, position = vat_candidate
                    candidate = (amount, currency, confidence, line_index, position)
                    candidates.append(candidate)
                    vat_candidates.append(candidate)
            elif (
                had_pending_total_label
                and len(line_amounts) == 1
                and not payment_metadata_line
            ):
                amount, currency, position = line_amounts[0]
                candidates.append((amount, currency, 0.88, line_index, position))
            else:
                candidates.extend(
                    (amount, currency, 0.55, line_index, position)
                    for amount, currency, position in line_amounts
                )
            if line.strip():
                previous_nonempty = lowered

        compact_payment_amounts = self._compact_payment_amounts(text)
        for candidate in vat_candidates:
            if any(
                abs(abs(candidate[0]) - payment_amount) <= 0.01
                for payment_amount in compact_payment_amounts
            ):
                candidates.append((
                    candidate[0],
                    candidate[1],
                    1.0,
                    candidate[3],
                    candidate[4],
                ))

        if not candidates:
            return None, None, 0.0

        highest_confidence = max(candidate[2] for candidate in candidates)
        finalists = [candidate for candidate in candidates if candidate[2] == highest_confidence]
        if highest_confidence < 0.85:
            unique_amounts = {round(abs(candidate[0]), 2) for candidate in candidates}
            if not has_total_label or len(unique_amounts) != 1:
                return None, None, 0.0
            amount, currency, _, line_index, token_index = candidates[-1]
            chosen = (amount, currency, 0.85, line_index, token_index)
        else:
            chosen = max(finalists, key=lambda candidate: (candidate[3], candidate[4]))
        return chosen[0], chosen[1], chosen[2]

    @staticmethod
    def _vat_summary_total(
        line_amounts: List[Tuple[float, Optional[str], int]],
        *,
        line_text: str = "",
        previous_line: str = "",
    ) -> Optional[Tuple[float, Optional[str], float, int]]:
        # OCR often renders VAT-column separators as minus signs. VAT, net, and
        # gross columns are magnitudes; refund direction comes from the payable
        # or refund line instead.
        values = [abs(amount) for amount, _, _ in line_amounts]
        if len(values) >= 3:
            vat_amount, net_amount, gross_amount = values[-3:]
            tolerance = max(0.02, abs(gross_amount) * 0.01)
            if (
                vat_amount >= 0
                and net_amount >= 0
                and gross_amount > 0
                and abs((vat_amount + net_amount) - gross_amount) <= tolerance
            ):
                return (
                    gross_amount,
                    line_amounts[-1][1],
                    0.99,
                    line_amounts[-1][2],
                )
            if 0 < vat_amount <= net_amount * 0.3:
                return (
                    round(vat_amount + net_amount, 2),
                    line_amounts[-2][1] or line_amounts[-3][1],
                    0.94,
                    line_amounts[-2][2],
                )
            return None
        if len(values) == 2:
            first_amount, second_amount = values
            header_context = f"{previous_line} {line_text}"
            if (
                first_amount > second_amount > 0
                and second_amount <= first_amount * 0.3
                and re.search(
                    r"\b(?:btw|vat|bw)\b|\b(?:excl|incl|bruto|gross)\b",
                    header_context,
                )
            ):
                return (
                    round(first_amount + second_amount, 2),
                    line_amounts[0][1] or line_amounts[-1][1],
                    0.94,
                    line_amounts[0][2],
                )
            if (
                second_amount > first_amount > 0
                and re.search(r"\b(?:bruto|gross)\b", header_context)
            ):
                return (
                    second_amount,
                    line_amounts[-1][1],
                    0.92,
                    line_amounts[-1][2],
                )
            difference = second_amount - first_amount
            if second_amount > first_amount > 0 and 0 < difference <= second_amount * 0.25:
                return (
                    second_amount,
                    line_amounts[-1][1],
                    0.92,
                    line_amounts[-1][2],
                )
            if 0 < first_amount <= second_amount * 0.3:
                return (
                    round(first_amount + second_amount, 2),
                    line_amounts[-1][1] or line_amounts[0][1],
                    0.94,
                    line_amounts[-1][2],
                )
        return None

    @staticmethod
    def _is_vat_summary_context(value: str) -> bool:
        normalized = str(value or "").lower()
        return bool(
            re.search(r"\b(?:btw|vat)\b|\b\d{1,2}(?:[.,]\d+)?\s*%", normalized)
            or re.search(
                r"(?:\b(?:btw|vat|bw)\b.*\b(?:excl|incl)\b|"
                r"\b(?:excl|incl)\b.*\b(?:btw|vat|bw)\b)",
                normalized,
            )
        )

    def _extract_vat_amount(
        self,
        text: str,
        total_amount: Optional[float],
    ) -> Tuple[Optional[float], float]:
        for line in text.splitlines():
            if not re.search(r"\b(?:btw|vat|tax|omzetbelasting)\b", line, flags=re.IGNORECASE):
                continue
            if re.search(
                r"\b(?:btw|vat|tax)[\s-]*(?:nummer|number|nr|id)\b",
                line,
                flags=re.IGNORECASE,
            ):
                continue
            candidates = []
            for match in re.finditer(self.AMOUNT_PATTERN, line, flags=re.IGNORECASE):
                if re.match(r"\s*%", line[match.end():]):
                    continue
                amount = self._amount_from_match(match)
                if amount is None:
                    continue
                validated = valid_vat_amount(amount, total_amount)
                if validated is not None:
                    candidates.append(validated)
            if candidates:
                return candidates[-1], 0.75
        return None, 0.0

    @staticmethod
    def _normalize_ocr_amount_labels(value: str) -> str:
        normalized = str(value or "").lower()
        normalized = re.sub(
            r"\b[fjt]otaa(?:l|[\]\[!|1)}])",
            "totaal",
            normalized,
        )
        normalized = re.sub(r"^\s*taal(?=\s*:)", "totaal", normalized)
        normalized = re.sub(r"^\s*mota(?=\s*:)", "totaal", normalized)
        normalized = re.sub(r"\bpri\s+javoordeel\b", "prijsvoordeel", normalized)
        return normalized

    @classmethod
    def _compact_payment_amounts(cls, text: str) -> List[float]:
        amounts = []
        for line in str(text or "").splitlines():
            match = re.search(
                r"\bbankpas\s+(\d{3,6})\b",
                line,
                flags=re.IGNORECASE,
            )
            if not match:
                continue
            value = int(match.group(1)) / 100
            if 0 < value <= 10000:
                amounts.append(round(value, 2))
        return amounts

    def _extract_reference(self, text: str, labels: List[str]) -> Tuple[Optional[str], float]:
        for label in labels:
            pattern = (
                rf"\b{re.escape(label)}\b\s*(?:nr|no|number|nummer)?\s*[:#-]?\s*"
                rf"(?P<ref>[A-Z0-9][A-Z0-9\-/]{{3,}})"
            )
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                reference = match.group("ref")
                if self._plausible_reference(reference):
                    return reference, 0.8
        return None, 0.0

    @staticmethod
    def _plausible_reference(value: str) -> bool:
        normalized = re.sub(r"[^A-Z0-9]", "", str(value or "").upper())
        return len(normalized) >= 4 and any(character.isdigit() for character in normalized)

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
            "jur": "Jun",
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
        if re.search(r"[A-Za-z]", normalized_date):
            normalized_date = re.sub(r"[-\s]+", " ", normalized_date).strip()
        candidates = [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%d.%m.%Y",
            "%d-%m-%y",
            "%d/%m/%y",
            "%d.%m.%y",
            "%m-%d-%Y",
            "%m/%d/%Y",
            "%m-%d-%y",
            "%m/%d/%y",
            "%Y-%B-%d",
            "%Y-%b-%d",
            "%Y %B %d",
            "%Y %b %d",
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
    def _plausible_transaction_date(value: str) -> bool:
        try:
            year = datetime.strptime(value, "%Y-%m-%d").year
        except (TypeError, ValueError):
            return False
        return 1990 <= year <= datetime.now().year + 1

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
