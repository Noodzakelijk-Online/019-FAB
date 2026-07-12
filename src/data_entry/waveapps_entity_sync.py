"""Read-only Wave customer, product, and invoice mirror synchronization."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

from src.data_entry.waveapps_account_discovery import (
    resolve_wave_target_config,
    wave_graph_errors,
    wave_timeout_seconds,
)
from src.data_entry.waveapps_transaction import WAVE_GRAPHQL_URL
from src.operations.local_ledger import LocalOperationsLedger
from src.utils.rate_limiter import (
    QuotaExhaustedException,
    RateLimitExceededException,
    get_rate_limiter,
)


WAVE_CUSTOMERS_QUERY = """
query ($businessId: ID!, $page: Int!, $pageSize: Int!) {
  business(id: $businessId) {
    id
    customers(page: $page, pageSize: $pageSize, sort: [NAME_ASC]) {
      pageInfo { currentPage totalPages totalCount }
      edges {
        node {
          id name firstName lastName email
          currency { code }
        }
      }
    }
  }
}
"""

WAVE_PRODUCTS_QUERY = """
query ($businessId: ID!, $page: Int!, $pageSize: Int!) {
  business(id: $businessId) {
    id
    products(page: $page, pageSize: $pageSize) {
      pageInfo { currentPage totalPages totalCount }
      edges {
        node {
          id name description unitPrice isSold isBought isArchived createdAt modifiedAt
          defaultSalesTaxes { id name abbreviation rate }
        }
      }
    }
  }
}
"""

WAVE_INVOICES_QUERY = """
query ($businessId: ID!, $page: Int!, $pageSize: Int!) {
  business(id: $businessId) {
    id
    invoices(page: $page, pageSize: $pageSize) {
      pageInfo { currentPage totalPages totalCount }
      edges {
        node {
          id createdAt modifiedAt status title invoiceNumber invoiceDate dueDate
          customer { id name }
          currency { code }
          amountDue { value }
          amountPaid { value }
          taxTotal { value }
          total { value }
        }
      }
    }
  }
}
"""


ENTITY_SPECS: Dict[str, Dict[str, Any]] = {
    "customer": {
        "collection": "customers",
        "query": WAVE_CUSTOMERS_QUERY,
        "normalize": lambda node: {
            "name": node.get("name"),
            "email": node.get("email"),
            "currency": _nested(node, "currency", "code"),
            "status": "active",
        },
    },
    "product": {
        "collection": "products",
        "query": WAVE_PRODUCTS_QUERY,
        "normalize": lambda node: {
            "name": node.get("name"),
            "status": "archived" if node.get("isArchived") else "active",
            "amount": node.get("unitPrice"),
            "modifiedAt": node.get("modifiedAt"),
        },
    },
    "invoice": {
        "collection": "invoices",
        "query": WAVE_INVOICES_QUERY,
        "normalize": lambda node: {
            "name": node.get("invoiceNumber") or node.get("title"),
            "status": node.get("status"),
            "currency": _nested(node, "currency", "code"),
            "amount": _nested(node, "total", "value"),
            "entityDate": node.get("invoiceDate"),
            "dueDate": node.get("dueDate"),
            "modifiedAt": node.get("modifiedAt"),
        },
    },
}


class WaveappsEntitySyncService:
    """Mirror supported Wave entities into FAB's local operations ledger."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.api_url = str(self.config.get("waveapps_api_url") or WAVE_GRAPHQL_URL)
        self.timeout_seconds = wave_timeout_seconds(self.config.get("waveapps_request_timeout_seconds"))
        self.max_wait_seconds = _safe_float(
            self.config.get("wave_entity_sync_max_wait_seconds"),
            5.0,
        )

    def sync(
        self,
        ledger: LocalOperationsLedger,
        target_system: str,
        entity_types: Optional[List[str]] = None,
        page_size: int = 50,
        max_pages: int = 100,
    ) -> Dict[str, Any]:
        target = resolve_wave_target_config(self.config, str(target_system or ""))
        requested_types = _entity_types(entity_types)
        if not target:
            return _failure("unsupported_target", "Unsupported Wave target account.")
        missing = [
            label
            for label, value in (("accessToken", target.get("access_token")), ("businessId", target.get("business_id")))
            if value in (None, "")
        ]
        if missing:
            result = _failure("not_configured", "Wave entity sync requires credentials and a business id.")
            result["missingFields"] = missing
            return result
        if not requested_types:
            result = _failure("invalid_entity_types", "At least one supported Wave entity type is required.")
            result["supportedEntityTypes"] = sorted(ENTITY_SPECS)
            return result

        page_size = min(max(_safe_int(page_size, 50), 1), 100)
        max_pages = min(max(_safe_int(max_pages, 100), 1), 500)
        sync_run_id = ledger.create_wave_sync_run({
            "targetSystem": target["id"],
            "entityTypes": requested_types,
            "pageSize": page_size,
            "status": "running",
            "metadata": {"readOnly": True, "externalSubmission": "not_executed"},
        })
        summaries = []
        total_pages = 0
        total_entities = 0
        try:
            for entity_type in requested_types:
                summary = self._sync_entity_type(
                    ledger,
                    sync_run_id,
                    target,
                    entity_type,
                    page_size,
                    max_pages,
                )
                summaries.append(summary)
                total_pages += int(summary.get("pagesFetched") or 0)
                total_entities += int(summary.get("entitiesSeen") or 0)
                if not summary.get("success"):
                    status = str(summary.get("status") or "provider_error")
                    ledger.update_wave_sync_run(sync_run_id, {
                        "status": status,
                        "pagesFetched": total_pages,
                        "entitiesSeen": total_entities,
                        "errorMessage": summary.get("message"),
                        "finishedAt": _now(),
                        "metadata": {"summaries": summaries, "readOnly": True, "externalSubmission": "not_executed"},
                    })
                    return {
                        "success": False,
                        "status": status,
                        "syncRunId": sync_run_id,
                        "targetSystem": target["id"],
                        "entityTypes": requested_types,
                        "pagesFetched": total_pages,
                        "entitiesSeen": total_entities,
                        "summaries": summaries,
                        "message": summary.get("message"),
                        "externalSubmission": "not_executed",
                    }
        except Exception as exc:
            ledger.update_wave_sync_run(sync_run_id, {
                "status": "internal_error",
                "pagesFetched": total_pages,
                "entitiesSeen": total_entities,
                "errorMessage": str(exc),
                "finishedAt": _now(),
                "metadata": {"summaries": summaries, "readOnly": True, "externalSubmission": "not_executed"},
            })
            return {
                "success": False,
                "status": "internal_error",
                "syncRunId": sync_run_id,
                "targetSystem": target["id"],
                "message": str(exc),
                "externalSubmission": "not_executed",
            }

        ledger.update_wave_sync_run(sync_run_id, {
            "status": "completed",
            "pagesFetched": total_pages,
            "entitiesSeen": total_entities,
            "finishedAt": _now(),
            "metadata": {"summaries": summaries, "readOnly": True, "externalSubmission": "not_executed"},
        })
        return {
            "success": True,
            "status": "completed",
            "syncRunId": sync_run_id,
            "targetSystem": target["id"],
            "entityTypes": requested_types,
            "pagesFetched": total_pages,
            "entitiesSeen": total_entities,
            "missingMarked": sum(int(summary.get("missingMarked") or 0) for summary in summaries),
            "summaries": summaries,
            "externalSubmission": "not_executed",
        }

    def _sync_entity_type(
        self,
        ledger: LocalOperationsLedger,
        sync_run_id: int,
        target: Dict[str, Any],
        entity_type: str,
        page_size: int,
        max_pages: int,
    ) -> Dict[str, Any]:
        spec = ENTITY_SPECS[entity_type]
        page = 1
        pages_fetched = 0
        entities_seen = 0
        expected_total = None
        seen_external_ids = set()
        while page <= max_pages:
            limiter = get_rate_limiter("waveapps")
            try:
                admitted = limiter.acquire(
                    block=self.max_wait_seconds > 0,
                    max_wait_seconds=self.max_wait_seconds,
                )
            except (QuotaExhaustedException, RateLimitExceededException):
                admitted = False
            if not admitted:
                rate = limiter.get_current_rate()
                return {
                    "success": False,
                    "status": "quota_exhausted" if rate.get("quotaExhausted") else "rate_limited",
                    "entityType": entity_type,
                    "pagesFetched": pages_fetched,
                    "entitiesSeen": entities_seen,
                    "message": "Wave entity sync was deferred by the outbound quota guard.",
                    "rateLimit": rate,
                }
            result = self._fetch_page(target, spec, page, page_size)
            if not result.get("success"):
                return {
                    **result,
                    "entityType": entity_type,
                    "pagesFetched": pages_fetched,
                    "entitiesSeen": entities_seen,
                }
            pages_fetched += 1
            page_info = result["pageInfo"]
            page_total = _optional_non_negative_int(page_info.get("totalCount"))
            if expected_total is None:
                expected_total = page_total
            elif page_total is not None and page_total != expected_total:
                return _incomplete_pagination(
                    entity_type,
                    pages_fetched,
                    entities_seen,
                    "Wave changed the reported total while the entity mirror was paging.",
                )
            for node in result["nodes"]:
                external_id = str(node["id"])
                if external_id in seen_external_ids:
                    return _incomplete_pagination(
                        entity_type,
                        pages_fetched,
                        entities_seen,
                        "Wave returned a duplicate entity id while the mirror was paging.",
                    )
                seen_external_ids.add(external_id)
                normalized = spec["normalize"](node)
                ledger.upsert_wave_entity({
                    "targetSystem": target["id"],
                    "entityType": entity_type,
                    "externalId": node["id"],
                    "lastSyncRunId": sync_run_id,
                    "lastSeenAt": _now(),
                    "presenceStatus": "present",
                    "payload": node,
                    **normalized,
                })
                entities_seen += 1
            total_pages = max(_safe_int(page_info.get("totalPages"), 1), 1)
            current_page = max(_safe_int(page_info.get("currentPage"), page), page)
            if current_page >= total_pages:
                if expected_total is None or len(seen_external_ids) != expected_total:
                    return _incomplete_pagination(
                        entity_type,
                        pages_fetched,
                        entities_seen,
                        "Wave pagination ended before the reported entity total was captured.",
                    )
                missing_marked = ledger.mark_wave_entities_missing(target["id"], entity_type, sync_run_id)
                return {
                    "success": True,
                    "status": "completed",
                    "entityType": entity_type,
                    "pagesFetched": pages_fetched,
                    "entitiesSeen": entities_seen,
                    "expectedTotal": expected_total,
                    "missingMarked": missing_marked,
                }
            page = current_page + 1
        return {
            "success": False,
            "status": "pagination_incomplete",
            "entityType": entity_type,
            "pagesFetched": pages_fetched,
            "entitiesSeen": entities_seen,
            "message": f"Wave {entity_type} sync exceeded the configured page limit.",
        }

    def _fetch_page(
        self,
        target: Dict[str, Any],
        spec: Dict[str, Any],
        page: int,
        page_size: int,
    ) -> Dict[str, Any]:
        try:
            response = requests.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {target['access_token']}",
                    "Content-Type": "application/json",
                },
                json={
                    "query": spec["query"],
                    "variables": {
                        "businessId": target["business_id"],
                        "page": page,
                        "pageSize": page_size,
                    },
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.exceptions.RequestException as exc:
            return _failure("provider_error", f"Wave entity sync request failed: {exc}")
        except ValueError:
            return _failure("provider_error", "Wave entity sync returned invalid JSON.")

        business = ((payload.get("data") or {}).get("business") or {}) if isinstance(payload, dict) else {}
        collection = business.get(spec["collection"]) if isinstance(business, dict) else None
        if not isinstance(collection, dict):
            return _failure(
                "provider_error",
                wave_graph_errors(payload) or f"Wave returned no {spec['collection']} collection.",
            )
        nodes = []
        for edge in collection.get("edges") or []:
            node = edge.get("node") if isinstance(edge, dict) else None
            if isinstance(node, dict) and node.get("id"):
                nodes.append(node)
        return {
            "success": True,
            "status": "page_captured",
            "nodes": nodes,
            "pageInfo": collection.get("pageInfo") or {},
        }


def _entity_types(values: Optional[List[str]]) -> List[str]:
    if values is None:
        return list(ENTITY_SPECS)
    if isinstance(values, str):
        values = [item.strip() for item in values.replace(";", ",").split(",")]
    result = []
    for value in values:
        entity_type = str(value or "").strip().lower()
        if entity_type in ENTITY_SPECS and entity_type not in result:
            result.append(entity_type)
    return result


def _nested(payload: Dict[str, Any], parent: str, child: str) -> Any:
    value = payload.get(parent)
    return value.get(child) if isinstance(value, dict) else None


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float) -> float:
    try:
        return max(float(value), 0.0)
    except (TypeError, ValueError):
        return default


def _optional_non_negative_int(value: Any) -> Optional[int]:
    try:
        result = int(value)
    except (TypeError, ValueError):
        return None
    return result if result >= 0 else None


def _incomplete_pagination(
    entity_type: str,
    pages_fetched: int,
    entities_seen: int,
    message: str,
) -> Dict[str, Any]:
    return {
        "success": False,
        "status": "pagination_incomplete",
        "entityType": entity_type,
        "pagesFetched": pages_fetched,
        "entitiesSeen": entities_seen,
        "message": message,
    }


def _failure(status: str, message: str) -> Dict[str, Any]:
    return {
        "success": False,
        "status": status,
        "message": message,
        "externalSubmission": "not_executed",
    }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
