from typing import Dict, Any, List
try:
    import pandas as pd
except ImportError:
    pd = None
import datetime

class FinancialAnalyzer:
    """Provides advanced financial analysis and reporting capabilities."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def generate_report(self, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        total_income = sum(float(item.get("amount", 0)) for item in transactions if float(item.get("amount", 0)) > 0)
        total_expenses = sum(float(item.get("amount", 0)) for item in transactions if float(item.get("amount", 0)) < 0)
        return {
            "total_income": total_income,
            "total_expenses": total_expenses,
            "net_cash_flow": total_income + total_expenses,
            "transaction_count": len(transactions),
        }

    def generate_expense_report(self, transactions: List[Dict[str, Any]], group_by: str = "category") -> Dict[str, Any]:
        """Generates a summary report of expenses.

        Args:
            transactions: A list of categorized transaction dictionaries.
            group_by: The field to group expenses by (e.g., "category", "vendor").

        Returns:
            A dictionary summarizing expenses.
        """
        if not transactions:
            return {"message": "No transactions to report.", "summary": {}}

        if pd is None:
            summary: Dict[str, float] = {}
            for transaction in transactions:
                extracted = transaction.get("extracted_data", {})
                key = transaction.get(group_by) or extracted.get(group_by)
                if key is None:
                    continue
                amount = float(extracted.get("total_amount") or transaction.get("amount") or 0)
                summary[str(key)] = summary.get(str(key), 0.0) + amount
            return {"message": "Expense report generated successfully.", "summary": summary}

        df = pd.DataFrame(transactions)
        
        # Ensure 'total_amount' is numeric and handle potential missing values
        df["total_amount"] = pd.to_numeric(
            df["extracted_data"].apply(lambda x: x.get("total_amount")),
            errors="coerce",
        ).fillna(0)
        
        # Extract category and vendor from the main dict or extracted_data
        df["category"] = df["category"]
        df["vendor_name"] = df["extracted_data"].apply(lambda x: x.get("vendor_name"))

        if group_by not in df.columns:
            return {"message": f"Invalid group_by field: {group_by}", "summary": {}}

        summary = df.groupby(group_by)["total_amount"].sum().to_dict()
        return {"message": "Expense report generated successfully.", "summary": summary}

    def cash_flow_forecast(self, transactions: List[Dict[str, Any]], forecast_months: int = 3) -> Dict[str, Any]:
        """Forecasts cash flow based on historical recurring expenses.

        Args:
            transactions: A list of categorized transaction dictionaries.
            forecast_months: Number of months to forecast into the future.

        Returns:
            A dictionary with forecasted cash flow data.
        """
        if not transactions:
            return {"message": "No transactions for forecasting.", "forecast": {}}

        if pd is None:
            return {"message": "pandas is required for cash flow forecasting.", "forecast": {}}

        df = pd.DataFrame(transactions)
        df["total_amount"] = pd.to_numeric(
            df["extracted_data"].apply(lambda x: x.get("total_amount")),
            errors="coerce",
        ).fillna(0)
        df["transaction_date"] = pd.to_datetime(df["extracted_data"].apply(lambda x: x.get("transaction_date")))
        df = df.dropna(subset=["transaction_date"])

        # Simple monthly average for forecasting
        monthly_expenses = df.set_index("transaction_date")["total_amount"].resample("M").sum()
        average_monthly_expense = monthly_expenses.mean() if not monthly_expenses.empty else 0

        forecast = {}
        current_month = datetime.date.today().replace(day=1)
        for i in range(forecast_months):
            forecast_month = (current_month + pd.DateOffset(months=i)).strftime("%Y-%m")
            forecast[forecast_month] = -average_monthly_expense # Negative for expense
        
        return {"message": "Cash flow forecast generated.", "forecast": forecast}

    def analyze_trend(self, transactions: List[Dict[str, Any]], category: str = None) -> Dict[str, Any]:
        """Analyzes spending trends over time for a specific category or overall.

        Args:
            transactions: A list of categorized transaction dictionaries.
            category: Optional category to filter by.

        Returns:
            A dictionary with trend data.
        """
        if not transactions:
            return {"message": "No transactions for trend analysis.", "trend": {}}

        if pd is None:
            return {"message": "pandas is required for trend analysis.", "trend": {}}

        df = pd.DataFrame(transactions)
        df["total_amount"] = pd.to_numeric(
            df["extracted_data"].apply(lambda x: x.get("total_amount")),
            errors="coerce",
        ).fillna(0)
        df["transaction_date"] = pd.to_datetime(df["extracted_data"].apply(lambda x: x.get("transaction_date")))
        df = df.dropna(subset=["transaction_date"])

        if category:
            df = df[df["category"] == category]

        monthly_spending = df.set_index("transaction_date")["total_amount"].resample("M").sum()
        
        return {"message": "Spending trend analyzed.", "trend": monthly_spending.to_dict()}


