import os
import tempfile
import unittest

from src.banking.bank_transaction_importer import BankTransactionImporter
from src.banking.banking_api import BankingAPI


class TestBankTransactionImporter(unittest.TestCase):
    def test_imports_csv_bank_transactions_with_dutch_columns(self):
        with tempfile.TemporaryDirectory() as tempdir:
            csv_path = os.path.join(tempdir, "bank.csv")
            with open(csv_path, "w", encoding="utf-8") as handle:
                handle.write("Datum;Omschrijving;Bedrag;Valuta\n")
                handle.write("05-06-2026;Albert Heijn;-4,28;EUR\n")

            importer = BankTransactionImporter({"bank_import_dir": tempdir})
            transactions = importer.import_transactions()

            self.assertEqual(len(transactions), 1)
            self.assertEqual(transactions[0]["date"], "2026-06-05")
            self.assertEqual(transactions[0]["description"], "Albert Heijn")
            self.assertEqual(transactions[0]["amount"], -4.28)
            self.assertEqual(transactions[0]["currency"], "EUR")
            self.assertTrue(transactions[0]["id"].startswith("bank_"))

    def test_banking_api_defaults_to_local_import(self):
        with tempfile.TemporaryDirectory() as tempdir:
            csv_path = os.path.join(tempdir, "bank.csv")
            with open(csv_path, "w", encoding="utf-8") as handle:
                handle.write("date,description,amount,currency\n")
                handle.write("2026-06-05,Store,-10.50,EUR\n")

            banking_api = BankingAPI({"bank_import_dir": tempdir})
            transactions = banking_api.fetch_transactions()

            self.assertEqual(len(transactions), 1)
            self.assertEqual(transactions[0]["amount"], -10.50)

    def test_date_filtering(self):
        with tempfile.TemporaryDirectory() as tempdir:
            csv_path = os.path.join(tempdir, "bank.csv")
            with open(csv_path, "w", encoding="utf-8") as handle:
                handle.write("date,description,amount,currency\n")
                handle.write("2026-06-01,Old,-1.00,EUR\n")
                handle.write("2026-06-05,New,-2.00,EUR\n")

            banking_api = BankingAPI({"bank_import_dir": tempdir})
            transactions = banking_api.fetch_transactions(start_date="2026-06-03")

            self.assertEqual(len(transactions), 1)
            self.assertEqual(transactions[0]["description"], "New")


if __name__ == "__main__":
    unittest.main()
