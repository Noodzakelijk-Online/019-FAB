"""Central implementation blueprint for FAB.

This module keeps the high-level product requirements close to the code so
implementation modules can be mapped directly to the product scope.
"""

FAB_MODULE_BLUEPRINT = {
    "data_extraction_and_upload": [
        "Google Drive sort-out folder ingestion",
        "Advanced OCR for diverse receipt formats and multiple languages",
        "Vendor, date, amount, tax, and item extraction",
        "Automated validation before posting",
    ],
    "vendor_and_category_management": [
        "Vendor identification and profile creation",
        "Smart vendor suggestions from aliases, fuzzy matches, and history",
        "Consistent categorization from vendor history and purchase patterns",
        "Dynamic nested category hierarchy",
        "User-defined categorization rules",
    ],
    "duplicate_and_document_handling": [
        "Fuzzy duplicate detection",
        "Invoice and receipt priority over order confirmation",
        "Receipt equal legal standing handling",
        "Version manifest for document changes",
    ],
    "integration_and_multi_account_support": [
        "Category A to mijngeldzaken",
        "Categories B and C to Waveapps accounts",
        "Bank transaction import and reconciliation",
        "API-ready design for third-party integrations",
    ],
    "user_interface_and_experience": [
        "Real-time dashboard",
        "Customizable views",
        "Manual review backlog",
    ],
    "reporting_and_analytics": [
        "Expense, revenue, and cash-flow reporting",
        "Charts and visual interpretation",
        "Scheduled report delivery",
    ],
    "security_and_compliance": [
        "Encryption in transit and at rest",
        "Role-based access control",
        "Local VAT and tax compliance support",
    ],
    "workflow_automation_and_notifications": [
        "Invoice approvals",
        "Payment scheduling",
        "Duplicate, missing receipt, and discrepancy alerts",
        "Tax and invoice deadline reminders",
    ],
    "error_handling_and_support": [
        "Automated correction where safe",
        "Comprehensive audit logs",
        "Manual escalation for uncertain cases",
    ],
    "scalability_performance_backup_recovery": [
        "Scalable architecture",
        "Performance monitoring",
        "Cloud-ready infrastructure",
        "Automated backups",
        "Disaster recovery",
        "User-initiated restores",
    ],
}

DEFAULT_CATEGORY_ROUTES = {
    "A": "mijngeldzaken",
    "B": "waveapps_business",
    "C": "waveapps_personal",
}
