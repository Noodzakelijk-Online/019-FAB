import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from src.data_entry.waveapps_entity_sync import WaveappsEntitySyncService
from src.operations.local_ledger import LocalOperationsLedger
from src.utils.rate_limiter import RateLimiter, reset_all_limiters, set_rate_limiter


class TestWaveappsEntitySyncService(unittest.TestCase):
    def setUp(self):
        reset_all_limiters()
        set_rate_limiter(
            "waveapps",
            limiter=RateLimiter(calls_per_second=100, calls_per_day=1000, name="WaveApps"),
        )
        self.config = {
            "waveapps_business_access_token": "business-secret-token",
            "waveapps_business_id": "business-1",
            "wave_entity_sync_max_wait_seconds": 0,
        }

    def tearDown(self):
        reset_all_limiters()

    @patch("src.data_entry.waveapps_entity_sync.requests.post")
    def test_syncs_paginated_customers_products_and_invoices_into_ledger(self, mock_post):
        def response_for_request(*args, **kwargs):
            query = kwargs["json"]["query"]
            page = kwargs["json"]["variables"]["page"]
            if "customers(" in query:
                nodes = (
                    [{"id": "customer-1", "name": "Acme", "email": "billing@acme.test", "currency": {"code": "EUR"}}]
                    if page == 1
                    else [{"id": "customer-2", "name": "Beta", "email": None, "currency": {"code": "EUR"}}]
                )
                return _response("customers", nodes, page, 2, 2)
            if "products(" in query:
                return _response("products", [{
                    "id": "product-1",
                    "name": "Consulting",
                    "description": "Hourly consulting",
                    "unitPrice": "125.00",
                    "isSold": True,
                    "isBought": False,
                    "isArchived": False,
                    "modifiedAt": "2026-07-09T12:00:00Z",
                }], 1, 1, 1)
            return _response("invoices", [{
                "id": "invoice-1",
                "invoiceNumber": "INV-2026-001",
                "status": "DRAFT",
                "invoiceDate": "2026-07-10",
                "dueDate": "2026-08-09",
                "modifiedAt": "2026-07-10T12:00:00Z",
                "customer": {"id": "customer-1", "name": "Acme"},
                "currency": {"code": "EUR"},
                "total": {"value": "250.00"},
                "amountDue": {"value": "250.00"},
                "amountPaid": {"value": "0.00"},
                "taxTotal": {"value": "43.39"},
            }], 1, 1, 1)

        mock_post.side_effect = response_for_request
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))

            result = WaveappsEntitySyncService(self.config).sync(
                ledger,
                "waveapps_business",
                page_size=1,
            )

            self.assertTrue(result["success"])
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["pagesFetched"], 4)
            self.assertEqual(result["entitiesSeen"], 4)
            self.assertEqual(mock_post.call_count, 4)
            entities = ledger.list_wave_entities(limit=20)
            self.assertEqual({entity["entity_type"] for entity in entities}, {"customer", "product", "invoice"})
            customer = next(entity for entity in entities if entity["external_id"] == "customer-1")
            product = next(entity for entity in entities if entity["entity_type"] == "product")
            invoice = next(entity for entity in entities if entity["entity_type"] == "invoice")
            self.assertEqual(customer["email"], "billing@acme.test")
            self.assertEqual(product["amount"], 125.0)
            self.assertEqual(invoice["name"], "INV-2026-001")
            self.assertEqual(invoice["amount"], 250.0)
            self.assertEqual(invoice["presence_status"], "present")
            sync_run = ledger.get_wave_sync_run(result["syncRunId"])
            self.assertEqual(sync_run["status"], "completed")
            self.assertEqual(sync_run["entities_seen"], 4)
            self.assertEqual(ledger.dashboard_metrics()["wave_entities"], 4)
            self.assertNotIn("business-secret-token", str(result))
            self.assertNotIn("business-secret-token", str(entities))

    @patch("src.data_entry.waveapps_entity_sync.requests.post")
    def test_complete_sync_marks_entities_missing_but_failed_sync_does_not(self, mock_post):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            service = WaveappsEntitySyncService(self.config)
            mock_post.return_value = _response("customers", [
                {"id": "customer-1", "name": "Acme"},
                {"id": "customer-2", "name": "Beta"},
            ], 1, 1, 2)
            first = service.sync(ledger, "waveapps_business", ["customer"])

            mock_post.return_value = _response("customers", [
                {"id": "customer-1", "name": "Acme"},
            ], 1, 1, 1)
            second = service.sync(ledger, "waveapps_business", ["customer"])

            self.assertTrue(first["success"])
            self.assertEqual(second["missingMarked"], 1)
            missing = ledger.list_wave_entities(presence_status="missing_downstream")
            self.assertEqual([entity["external_id"] for entity in missing], ["customer-2"])

            mock_post.return_value = _response_payload({"errors": [{"message": "temporary provider error"}]})
            failed = service.sync(ledger, "waveapps_business", ["customer"])

            self.assertFalse(failed["success"])
            self.assertEqual(failed["status"], "provider_error")
            self.assertEqual(
                ledger.get_wave_entity(next(entity["id"] for entity in missing))["presence_status"],
                "missing_downstream",
            )
            self.assertEqual(ledger.get_wave_sync_run(failed["syncRunId"])["status"], "provider_error")

    def test_missing_configuration_does_not_create_sync_run(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))

            result = WaveappsEntitySyncService({}).sync(ledger, "waveapps_business")

            self.assertFalse(result["success"])
            self.assertEqual(result["status"], "not_configured")
            self.assertEqual(result["missingFields"], ["accessToken", "businessId"])
            self.assertEqual(ledger.list_wave_sync_runs(), [])

    @patch("src.data_entry.waveapps_entity_sync.requests.post")
    def test_incomplete_total_does_not_mark_prior_entities_missing(self, mock_post):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            ledger.upsert_wave_entity({
                "targetSystem": "waveapps_business",
                "entityType": "customer",
                "externalId": "customer-existing",
                "name": "Existing customer",
            })
            mock_post.return_value = _response(
                "customers",
                [{"id": "customer-new", "name": "New customer"}],
                1,
                1,
                2,
            )

            result = WaveappsEntitySyncService(self.config).sync(
                ledger,
                "waveapps_business",
                ["customer"],
            )

            self.assertFalse(result["success"])
            self.assertEqual(result["status"], "pagination_incomplete")
            existing = next(
                entity
                for entity in ledger.list_wave_entities(limit=20)
                if entity["external_id"] == "customer-existing"
            )
            self.assertEqual(existing["presence_status"], "present")
            self.assertEqual(
                ledger.get_wave_sync_run(result["syncRunId"])["status"],
                "pagination_incomplete",
            )

    @patch("src.data_entry.waveapps_entity_sync.requests.post")
    def test_quota_exhaustion_is_recorded_without_provider_dispatch(self, mock_post):
        set_rate_limiter(
            "waveapps",
            limiter=RateLimiter(calls_per_day=0, name="WaveApps"),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))

            result = WaveappsEntitySyncService(self.config).sync(
                ledger,
                "waveapps_business",
                ["customer"],
            )

            self.assertFalse(result["success"])
            self.assertEqual(result["status"], "quota_exhausted")
            mock_post.assert_not_called()
            sync_run = ledger.get_wave_sync_run(result["syncRunId"])
            self.assertEqual(sync_run["status"], "quota_exhausted")
            self.assertEqual(sync_run["entities_seen"], 0)


def _response(collection, nodes, current_page, total_pages, total_count):
    return _response_payload({
        "data": {
            "business": {
                "id": "business-1",
                collection: {
                    "pageInfo": {
                        "currentPage": current_page,
                        "totalPages": total_pages,
                        "totalCount": total_count,
                    },
                    "edges": [{"node": node} for node in nodes],
                },
            }
        }
    })


def _response_payload(payload):
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload
    return response


if __name__ == "__main__":
    unittest.main()
