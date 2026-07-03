from typing import Dict, Any, List
import json
import os
from datetime import datetime

class BudgetManager:
    """Manages household budgets and checks expenses against them."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.budget_file = self.config.get("budget_file", "config/budgets.json")
        self.budgets = self._load_budgets()

    def _load_budgets(self) -> Dict[str, Any]:
        if os.path.exists(self.budget_file):
            with open(self.budget_file, "r") as f:
                return json.load(f)
        return {"categories": {}, "total_monthly_budget": 0.0}

    def _save_budgets(self):
        os.makedirs(os.path.dirname(self.budget_file), exist_ok=True)
        with open(self.budget_file, "w") as f:
            json.dump(self.budgets, f, indent=4)

    def configure_budget(self, category_budgets: Dict[str, float], total_monthly_budget: float):
        """Configures or updates the budget for various categories and total monthly spending."""
        self.budgets["categories"] = category_budgets
        self.budgets["total_monthly_budget"] = total_monthly_budget
        self._save_budgets()
        print("Budget configured successfully.")

    def _category_limit_and_spent(self, category: str) -> tuple[float, float]:
        category_budget = self.budgets.get("categories", {}).get(category, 0.0)
        if isinstance(category_budget, dict):
            return float(category_budget.get("limit", 0.0)), float(category_budget.get("spent", 0.0))
        return float(category_budget or 0.0), 0.0

    def check_budget(self, categorized_data: Dict[str, Any] | str, amount: float = None) -> Dict[str, Any]:
        """Checks if a given expense fits within the configured budget.

        Args:
            categorized_data: A dictionary containing the categorized document data.

        Returns:
            A dictionary indicating if the expense is within budget and any warnings.
        """
        if isinstance(categorized_data, str):
            categorized_data = {
                "category": categorized_data,
                "extracted_data": {
                    "total_amount": amount,
                    "transaction_date": datetime.now().strftime("%Y-%m-%d"),
                },
            }

        category = categorized_data.get("category")
        amount = categorized_data.get("extracted_data", {}).get("total_amount")
        transaction_date_str = categorized_data.get("extracted_data", {}).get("transaction_date")

        if not category or amount is None or not transaction_date_str:
            return {"is_within_budget": True, "message": "Insufficient data for budget check.", "flagged": False}

        try:
            transaction_date = datetime.strptime(transaction_date_str, "%Y-%m-%d")
        except ValueError:
            return {"is_within_budget": True, "message": "Invalid date format for budget check.", "flagged": False}

        current_month_key = transaction_date.strftime("%Y-%m")

        # Initialize monthly spending if not present
        if current_month_key not in self.budgets:
            self.budgets[current_month_key] = {"total_spent": 0.0, "category_spent": {}}

        # Update spending for the current month
        amount = float(amount)
        self.budgets[current_month_key]["total_spent"] += amount
        self.budgets[current_month_key]["category_spent"][category] = \
            self.budgets[current_month_key]["category_spent"].get(category, 0.0) + amount
        self._save_budgets()

        is_within_budget = True
        message = ""
        flagged = False
        remaining = None

        # Check category budget
        category_budget_limit, historical_spent = self._category_limit_and_spent(category)
        category_spent = historical_spent + self.budgets[current_month_key]["category_spent"].get(category, 0.0)
        if category_budget_limit > 0:
            remaining = max(category_budget_limit - category_spent, 0.0)
        if category_budget_limit > 0 and category_spent > category_budget_limit:
            is_within_budget = False
            flagged = True
            message += f"Category '{category}' budget exceeded. Spent: {category_spent:.2f}, Limit: {category_budget_limit:.2f}. "

        # Check total monthly budget
        total_monthly_limit = self.budgets.get("total_monthly_budget", 0.0)
        if total_monthly_limit > 0 and self.budgets[current_month_key]["total_spent"] > total_monthly_limit:
            is_within_budget = False
            flagged = True
            message += f"Total monthly budget exceeded. Spent: {self.budgets[current_month_key]['total_spent']:.2f}, Limit: {total_monthly_limit:.2f}. "

        return {"is_within_budget": is_within_budget, "message": message.strip(), "flagged": flagged, "remaining": remaining}

    def get_current_spending(self, month_key: str = None) -> Dict[str, Any]:
        """Returns current spending for a given month or the current month."""
        if month_key is None:
            month_key = datetime.now().strftime("%Y-%m")
        return self.budgets.get(month_key, {"total_spent": 0.0, "category_spent": {}})

    def get_budget_limits(self) -> Dict[str, Any]:
        """Returns the configured budget limits."""
        return {
            "categories": self.budgets.get("categories", {}),
            "total_monthly_budget": self.budgets.get("total_monthly_budget", 0.0)
        }


