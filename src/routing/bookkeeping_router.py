from typing import Any, Dict, Optional


class BookkeepingRouter:
    """Route FAB entries to the correct bookkeeping handler."""

    DEFAULT_ROUTES = {
        "A": "mijngeldzaken",
        "category_a": "mijngeldzaken",
        "personal": "mijngeldzaken",
        "B": "waveapps_business",
        "category_b": "waveapps_business",
        "business": "waveapps_business",
        "C": "waveapps_personal",
        "category_c": "waveapps_personal",
        "handicaps": "waveapps_personal",
    }

    def __init__(self, config: Dict[str, Any]):
        self.config = config or {}
        self.routes = dict(self.DEFAULT_ROUTES)
        self.routes.update(self.config.get("bookkeeping_platform_routes", {}))
        self.account_map = self.config.get("bookkeeping_account_map", {})

    def resolve_target(self, document_data: Dict[str, Any]) -> Optional[str]:
        category = document_data.get("category") or document_data.get("category_code")
        if not category:
            extracted = document_data.get("extracted_data", {})
            category = extracted.get("category") or extracted.get("category_code")
        if not category:
            return None
        key = str(category).strip()
        return self.routes.get(key) or self.routes.get(key.lower())

    def resolve_account(self, document_data: Dict[str, Any]) -> Optional[str]:
        target = self.resolve_target(document_data)
        if not target:
            return None
        category = document_data.get("category") or document_data.get("category_code")
        account_key = f"{target}:{category}"
        return self.account_map.get(account_key) or self.account_map.get(target)

    def route(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        target = self.resolve_target(document_data)
        return {
            "target_system": target,
            "target_account": self.resolve_account(document_data),
            "requires_manual_review": target is None,
            "reason": "category_route_found" if target else "no_route_for_category",
        }
