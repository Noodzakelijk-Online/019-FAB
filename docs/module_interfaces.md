# Module Interfaces and Data Flow

This document describes the interfaces between different modules of the Automated Bookkeeping Solution and the data flow within the system.

## System Architecture Overview

The system is designed with a modular architecture, consisting of the following main components:

1.  **Document Fetchers**: Responsible for retrieving financial documents from various sources.
2.  **Document Processors**: Handles OCR, data extraction, and pre-processing of documents.
3.  **Categorizers**: Assigns categories to processed documents based on rules and machine learning.
4.  **Learning Modules**: Learns from historical data and user feedback to improve categorization and data extraction.
5.  **Data Entry Handlers**: Integrates with external bookkeeping systems (mijngeldzaken.nl, Waveapps) to enter processed data.
6.  **Workflow Orchestration**: Manages the overall flow of documents through the system, including error handling and logging.
7.  **Validation**: Ensures the legal compliance and completeness of receipts.
8.  **Migration**: Tools for importing historical data.
9.  **Budgeting**: Manages household budgets and enforces spending policies.
10. **Banking Integration**: Connects to banking APIs for reconciliation.
11. **Financial Analysis**: Provides advanced reporting and forecasting.
12. **Manual Review**: Interface for human intervention on flagged documents.
13. **Backup**: Manages backup and disaster recovery.
14. **Performance & Security**: Cross-cutting concerns for optimization and protection.

## Data Flow Diagram

```mermaid
graph TD
    A[Document Sources] --> B{Document Fetchers}
    B --> C[Raw Documents]
    C --> D{Document Processors}
    D --> E[Processed Data]
    E --> F{Learning Modules}
    E --> G{Categorizers}
    F --> G
    G --> H[Categorized Data]
    H --> I{Validation}
    I --> J[Validated Data]
    J --> K{Budgeting}
    K --> L[Budget-Checked Data]
    L --> M{Data Entry Handlers}
    M --> N[Bookkeeping Systems]
    N --> F
    J --> O{Manual Review}
    O --> M
    P[Bank Statements] --> Q{Banking Integration}
    Q --> R[Bank Transactions]
    R --> S{Automated Reconciliation}
    S --> M
    S --> O
    S --> T[Missing Document Alerts]
    M --> U{Financial Analysis}
    U --> V[Reports]
    SubGraph System Management
        W[Workflow Orchestration] --> B
        W --> D
        W --> G
        W --> M
        W --> O
        W --> S
        W --> U
        W --> X[Logging & Notifications]
        Y[Security Manager] --> W
        Z[Performance Optimizer] --> W
        AA[Backup Manager] --> W
    End
```

## Module Interfaces

### 1. Document Fetchers
- **Input**: Configuration (source credentials, filters, paths).
- **Output**: Raw document files (PDF, JPG, PNG) and associated metadata (source, timestamp, original filename).
- **Interface**: `fetch_documents(config: dict) -> List[Document]`

### 2. Document Processors
- **Input**: Raw document file, metadata.
- **Output**: Extracted data (vendor, amount, date, line items, VAT, currency), OCR text, language detected.
- **Interface**: `process_document(document: Document) -> ProcessedData`

### 3. Categorizers
- **Input**: Processed data, historical categorization data (from Learning Modules).
- **Output**: Categorized data (assigned category: Personal, Business, Handicap), confidence score.
- **Interface**: `categorize_data(processed_data: ProcessedData, learning_data: dict) -> CategorizedData`

### 4. Learning Modules
- **Input**: Categorized data, user corrections/feedback, historical data from bookkeeping systems.
- **Output**: Updated categorization rules, vendor mappings, transaction patterns, ML model weights.
- **Interface**: `learn_from_data(data: Union[CategorizedData, FeedbackData]) -> None`
- **Interface**: `analyze_waveapps_data(api_client) -> dict`
- **Interface**: `analyze_mijngeldzaken_data(browser_client) -> dict`

### 5. Data Entry Handlers
- **Input**: Categorized data, credentials.
- **Output**: Success/failure status, transaction ID from bookkeeping system.
- **Interface**: `enter_data(categorized_data: CategorizedData, credentials: dict) -> EntryResult`

### 6. Workflow Orchestration
- **Input**: System configuration, triggers (scheduled, manual).
- **Output**: Orchestrates calls to other modules, manages state, handles errors, sends notifications.
- **Interface**: `run_workflow(config: dict) -> None`

### 7. Validation
- **Input**: Processed data, configuration for validation rules.
- **Output**: Validation status (valid, invalid, flagged), reasons for flagging.
- **Interface**: `validate_receipt(processed_data: ProcessedData) -> ValidationResult`

### 8. Migration
- **Input**: Historical data file (CSV, Excel), mapping configuration.
- **Output**: Processed and imported historical data.
- **Interface**: `migrate_data(file_path: str, mapping: dict) -> MigrationSummary`

### 9. Budgeting
- **Input**: Categorized data, budget configuration.
- **Output**: Budget compliance status, alerts for overspending.
- **Interface**: `check_budget(categorized_data: CategorizedData, budget: dict) -> BudgetStatus`

### 10. Banking Integration
- **Input**: Bank API credentials, date range.
- **Output**: Bank transaction data.
- **Interface**: `fetch_transactions(credentials: dict, start_date: date, end_date: date) -> List[Transaction]`

### 11. Financial Analysis
- **Input**: Processed data, categorized data, bank data.
- **Output**: Financial reports, forecasts, trend analysis.
- **Interface**: `generate_report(data: List[dict], report_type: str) -> Report`

### 12. Manual Review
- **Input**: Flagged documents/data.
- **Output**: User corrections, updated categorization.
- **Interface**: `get_review_queue() -> List[ReviewItem]`
- **Interface**: `submit_correction(item_id: str, correction: dict) -> None`

### 13. Backup
- **Input**: Data to backup, backup configuration.
- **Output**: Backup status.
- **Interface**: `perform_backup(data_paths: List[str], config: dict) -> BackupResult`

## Data Structures (Examples)

### Document
```python
{
    'id': 'unique_doc_id',
    'source': 'gmail' | 'drive' | 'freshdesk' | 'photos',
    'original_filename': 'invoice_123.pdf',
    'local_path': '/tmp/invoice_123.pdf',
    'timestamp': '2025-03-31T10:00:00Z',
    'metadata': {...} # Source-specific metadata
}
```

### ProcessedData
```python
{
    'document_id': 'unique_doc_id',
    'ocr_text': 'Full OCR text content',
    'language': 'en' | 'nl',
    'extracted_data': {
        'vendor_name': 'Albert Heijn',
        'transaction_date': '2025-03-30',
        'total_amount': 123.45,
        'currency': 'EUR',
        'vat_amount': 10.00,
        'line_items': [
            {'description': 'Milk', 'quantity': 1, 'unit_price': 1.20, 'total': 1.20},
            {'description': 'Bread', 'quantity': 1, 'unit_price': 2.50, 'total': 2.50}
        ]
    }
}
```

### CategorizedData
```python
{
    'document_id': 'unique_doc_id',
    'processed_data': {...},
    'category': 'Personal' | 'Business' | 'Handicap',
    'confidence_score': 0.95,
    'categorization_method': 'ml' | 'rule_based' | 'fallback'
}
```

### EntryResult
```python
{
    'document_id': 'unique_doc_id',
    'status': 'success' | 'failure' | 'manual_review_required',
    'message': 'Successfully entered into Waveapps Business',
    'external_id': 'waveapps_transaction_id_xyz' # ID from external system
}
```


