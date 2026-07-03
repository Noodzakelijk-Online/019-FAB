import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher, get_close_matches
from typing import Any, Dict, Iterable, List, Optional


class VendorManager:
    """Identify, create, suggest, and categorize vendors for FAB.

    The manager is intentionally dependency-free. It uses normalized string
    comparison and difflib-based fuzzy matching so it works in constrained
    local deployments without requiring a separate fuzzy-matching package.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config or {}
        self.match_threshold = float(self.config.get("vendor_match_threshold", 0.72))
        self.auto_create_vendors = bool(self.config.get("auto_create_vendors", True))

        self.vendors: Dict[str, Dict[str, Any]] = {}
        self.aliases = {
            self._normalize(alias): canonical
            for alias, canonical in self.config.get("vendor_aliases", {}).items()
        }

        configured_vendors = self.config.get("vendors", {})
        for name, profile in configured_vendors.items():
            self.create_vendor(name, profile or {}, overwrite=True)

        self.category_history: Dict[str, Counter] = defaultdict(Counter)
        for event in self.config.get("vendor_category_history", []):
            vendor = event.get("vendor_name")
            category = event.get("category")
            if vendor and category:
                self.record_vendor_usage(vendor, category)

    @staticmethod
    def _normalize(value: Optional[str]) -> str:
        if not value:
            return ""
        value = value.lower().strip()
        value = re.sub(r"\b(bv|b\.v\.|vof|v\.o\.f\.|ltd|llc|inc|the)\b", " ", value)
        value = re.sub(r"[^a-z0-9]+", " ", value)
        return re.sub(r"\s+", " ", value).strip()

    def create_vendor(
        self,
        vendor_name: str,
        profile: Optional[Dict[str, Any]] = None,
        overwrite: bool = False,
    ) -> Dict[str, Any]:
        canonical = vendor_name.strip()
        normalized = self._normalize(canonical)
        if not canonical:
            raise ValueError("vendor_name is required")

        if normalized in self.vendors and not overwrite:
            return self.vendors[normalized]

        stored_profile = {
            "vendor_name": canonical,
            "normalized_name": normalized,
            "category": None,
            "category_path": [],
            "aliases": [],
            "metadata": {},
            "created_by": "fab_vendor_manager",
            "is_auto_created": False,
        }
        stored_profile.update(profile or {})
        stored_profile["vendor_name"] = stored_profile.get("vendor_name") or canonical
        stored_profile["normalized_name"] = normalized

        for alias in stored_profile.get("aliases", []):
            self.aliases[self._normalize(alias)] = stored_profile["vendor_name"]

        self.vendors[normalized] = stored_profile
        return stored_profile

    def suggest_vendors(self, vendor_name: str, limit: int = 3) -> List[Dict[str, Any]]:
        normalized = self._normalize(vendor_name)
        if not normalized:
            return []

        candidates = list(self.vendors.keys())
        exact_alias = self.aliases.get(normalized)
        suggestions: List[Dict[str, Any]] = []
        if exact_alias:
            alias_profile = self.get_vendor_profile(exact_alias)
            if alias_profile:
                suggestions.append(
                    {
                        "vendor_name": alias_profile["vendor_name"],
                        "score": 1.0,
                        "reason": "alias",
                    }
                )

        close_matches = get_close_matches(normalized, candidates, n=limit, cutoff=0)
        scored = []
        for candidate in close_matches:
            score = SequenceMatcher(None, normalized, candidate).ratio()
            if score >= self.match_threshold:
                scored.append(
                    {
                        "vendor_name": self.vendors[candidate]["vendor_name"],
                        "score": round(score, 4),
                        "reason": "fuzzy_name_match",
                    }
                )

        existing_names = {item["vendor_name"] for item in suggestions}
        for suggestion in sorted(scored, key=lambda item: item["score"], reverse=True):
            if suggestion["vendor_name"] not in existing_names:
                suggestions.append(suggestion)
                existing_names.add(suggestion["vendor_name"])

        return suggestions[:limit]

    def get_vendor_profile(self, vendor_name: str) -> Optional[Dict[str, Any]]:
        normalized = self._normalize(vendor_name)
        if normalized in self.vendors:
            return self.vendors[normalized]

        canonical_from_alias = self.aliases.get(normalized)
        if canonical_from_alias:
            return self.vendors.get(self._normalize(canonical_from_alias))

        return None

    def identify_vendor(
        self,
        ocr_text: str = "",
        extracted_vendor: Optional[str] = None,
    ) -> Dict[str, Any]:
        vendor_name = (extracted_vendor or "").strip()
        if vendor_name:
            profile = self.get_vendor_profile(vendor_name)
            if profile:
                return self._build_vendor_result(profile, matched_existing=True, suggestions=[])

            suggestions = self.suggest_vendors(vendor_name)
            if suggestions and suggestions[0]["score"] >= self.match_threshold:
                profile = self.get_vendor_profile(suggestions[0]["vendor_name"])
                if profile:
                    return self._build_vendor_result(
                        profile,
                        matched_existing=True,
                        suggestions=suggestions,
                        match_reason=suggestions[0]["reason"],
                    )

            if self.auto_create_vendors:
                profile = self.create_vendor(
                    vendor_name,
                    {"is_auto_created": True, "metadata": {"source": "ocr_extracted_vendor"}},
                )
                return self._build_vendor_result(
                    profile,
                    matched_existing=False,
                    suggestions=suggestions,
                    match_reason="auto_created_from_ocr",
                )

            return {
                "vendor_name": vendor_name,
                "matched_existing": False,
                "suggestions": suggestions,
                "category": None,
                "category_path": [],
                "requires_manual_review": True,
            }

        text_vendor = self._find_vendor_in_text(ocr_text)
        if text_vendor:
            profile = self.get_vendor_profile(text_vendor)
            if profile:
                return self._build_vendor_result(
                    profile,
                    matched_existing=True,
                    suggestions=[],
                    match_reason="vendor_name_found_in_ocr_text",
                )

        return {
            "vendor_name": None,
            "matched_existing": False,
            "suggestions": [],
            "category": None,
            "category_path": [],
            "requires_manual_review": True,
        }

    def assign_category(
        self,
        vendor_name: Optional[str],
        purchase_items: Optional[Iterable[Dict[str, Any]]] = None,
        fallback_category: str = "Manual Review",
    ) -> Dict[str, Any]:
        profile = self.get_vendor_profile(vendor_name or "")
        if profile and profile.get("category"):
            return {
                "category": profile["category"],
                "category_path": profile.get("category_path") or self.get_category_path(profile["category"]),
                "confidence_score": 0.9,
                "reason": "vendor_default_category",
            }

        normalized = self._normalize(vendor_name or "")
        if normalized in self.category_history and self.category_history[normalized]:
            category, count = self.category_history[normalized].most_common(1)[0]
            total = sum(self.category_history[normalized].values())
            confidence = min(0.85, 0.55 + (count / max(total, 1)) * 0.3)
            return {
                "category": category,
                "category_path": self.get_category_path(category),
                "confidence_score": round(confidence, 4),
                "reason": "vendor_history",
            }

        item_text = " ".join(str(item) for item in (purchase_items or []))
        pattern_rules = self.config.get("purchase_pattern_rules", {})
        for category, patterns in pattern_rules.items():
            for pattern in patterns:
                if re.search(pattern, item_text, flags=re.IGNORECASE):
                    return {
                        "category": category,
                        "category_path": self.get_category_path(category),
                        "confidence_score": 0.75,
                        "reason": "purchase_pattern_rule",
                    }

        return {
            "category": fallback_category,
            "category_path": self.get_category_path(fallback_category),
            "confidence_score": 0.1,
            "reason": "fallback",
        }

    def record_vendor_usage(self, vendor_name: str, category: str) -> None:
        normalized = self._normalize(vendor_name)
        if normalized and category:
            self.category_history[normalized][category] += 1

    def get_category_path(self, category: Optional[str]) -> List[str]:
        if not category:
            return []

        hierarchy = self.config.get("category_hierarchy", {})
        path = self._find_category_path(category, hierarchy)
        return path or [category]

    def _find_category_path(self, target: str, subtree: Dict[str, Any], path=None) -> List[str]:
        path = path or []
        for name, children in subtree.items():
            current_path = path + [name]
            if name == target:
                return current_path
            if isinstance(children, dict):
                found = self._find_category_path(target, children, current_path)
                if found:
                    return found
        return []

    def _find_vendor_in_text(self, ocr_text: str) -> Optional[str]:
        normalized_text = self._normalize(ocr_text)
        for normalized_name, profile in self.vendors.items():
            if normalized_name and normalized_name in normalized_text:
                return profile["vendor_name"]
        for alias, canonical in self.aliases.items():
            if alias and alias in normalized_text:
                return canonical
        return None

    def _build_vendor_result(
        self,
        profile: Dict[str, Any],
        matched_existing: bool,
        suggestions: List[Dict[str, Any]],
        match_reason: str = "exact_match",
    ) -> Dict[str, Any]:
        category = profile.get("category")
        return {
            "vendor_name": profile["vendor_name"],
            "matched_existing": matched_existing,
            "suggestions": suggestions,
            "category": category,
            "category_path": profile.get("category_path") or self.get_category_path(category),
            "profile": profile,
            "match_reason": match_reason,
            "requires_manual_review": False,
        }
