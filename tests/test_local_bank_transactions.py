import os
import tempfile
import unittest

from src.operations.local_bank_transactions import LocalBankTransactionImportService
from src.operations.local_ledger import LocalOperationsLedger


class TestLocalBankTransactionImportService(unittest.TestCase):
    def test_import_transactions_is_idempotent_and_reconciliation_ready(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            service = LocalBankTransactionImportService(ledger, {})

            first = service.import_transactions([
                {
                    "id": "tx-json-1",
                    "date": "2026-06-28",
                    "amount": "-42.50",
                    "description": "Office Shop",
                    "counterparty": "Office Shop",
                }
            ], account_identifier="wave-checking", source="wave_report", filename="account-transactions.json")
            second = service.import_transactions([
                {
                    "id": "tx-json-1",
                    "date": "2026-06-28",
                    "amount": "-42.50",
                    "description": "Office Shop",
                    "counterparty": "Office Shop",
                }
            ], account_identifier="wave-checking", source="wave_report", filename="account-transactions.json")

            transactions = ledger.list_bank_transactions(account_identifier="wave-checking")
            reconciliation_batch = service.transactions_for_reconciliation()

            self.assertEqual(first["rowsImported"], 1)
            self.assertEqual(first["duplicates"], 0)
            self.assertEqual(second["rowsImported"], 0)
            self.assertEqual(second["duplicates"], 1)
            self.assertEqual(len(transactions), 1)
            self.assertEqual(transactions[0]["transaction_id"], "tx-json-1")
            self.assertEqual(transactions[0]["amount"], -42.5)
            self.assertEqual(reconciliation_batch[0]["id"], "tx-json-1")
            self.assertEqual(reconciliation_batch[0]["ledgerBankTransactionId"], transactions[0]["id"])
            self.assertEqual(ledger.list_audit_events()[0]["action"], "local_bank_transactions.import_completed")

    def test_import_csv_statement_maps_debit_credit_columns(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            service = LocalBankTransactionImportService(ledger, {})

            result = service.import_statement_text(
                "Date;Description;Debit;Credit;Name;Reference\n"
                "28-06-2026;Office Shop;42,50;;Office Shop;csv-1\n"
                "29-06-2026;Client payment;;100,00;Client BV;csv-2\n",
                format="csv",
                account_identifier="nl-bank",
                source="bank_csv",
            )

            transactions = ledger.list_bank_transactions(account_identifier="nl-bank", limit=10)
            by_id = {transaction["transaction_id"]: transaction for transaction in transactions}

            self.assertEqual(result["rowsImported"], 2)
            self.assertEqual(by_id["csv-1"]["transaction_date"], "2026-06-28")
            self.assertEqual(by_id["csv-1"]["amount"], -42.5)
            self.assertEqual(by_id["csv-2"]["amount"], 100.0)

    def test_import_camt_statement_normalizes_debit_entry(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            service = LocalBankTransactionImportService(ledger, {})

            result = service.import_statement_text(
                """
                <Document>
                  <BkToCstmrStmt>
                    <Stmt>
                      <Ntry>
                        <Amt Ccy="EUR">42.50</Amt>
                        <CdtDbtInd>DBIT</CdtDbtInd>
                        <BookgDt><Dt>2026-06-28</Dt></BookgDt>
                        <AcctSvcrRef>camt-1</AcctSvcrRef>
                        <NtryDtls><TxDtls><RltdPties><Cdtr><Nm>Office Shop</Nm></Cdtr></RltdPties><RmtInf><Ustrd>Office supplies</Ustrd></RmtInf></TxDtls></NtryDtls>
                      </Ntry>
                    </Stmt>
                  </BkToCstmrStmt>
                </Document>
                """,
                format="camt",
                account_identifier="camt-account",
            )

            transaction = ledger.list_bank_transactions(account_identifier="camt-account")[0]

            self.assertEqual(result["rowsImported"], 1)
            self.assertEqual(transaction["transaction_id"], "camt-1")
            self.assertEqual(transaction["amount"], -42.5)
            self.assertEqual(transaction["counterparty"], "Office Shop")

    def test_import_mt940_statement_extracts_amount_date_and_description(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = LocalOperationsLedger(os.path.join(temp_dir, "fab.sqlite3"))
            service = LocalBankTransactionImportService(ledger, {})

            result = service.import_statement_text(
                ":20:START\n"
                ":61:2606280628D42,50NTRFNONREF\n"
                ":86:Office Shop payment\n",
                format="mt940",
                account_identifier="mt940-account",
            )

            transaction = ledger.list_bank_transactions(account_identifier="mt940-account")[0]

            self.assertEqual(result["rowsImported"], 1)
            self.assertEqual(transaction["transaction_date"], "2026-06-28")
            self.assertEqual(transaction["amount"], -42.5)
            self.assertIn("Office Shop", transaction["description"])


if __name__ == "__main__":
    unittest.main()
