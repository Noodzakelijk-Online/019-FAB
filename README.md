# Automated Bookkeeping Solution

## Overview
This project aims to develop a fully automated system to fetch financial documents from various sources, extract relevant data, categorize them based on predefined rules, and enter the data into mijngeldzaken.nl and Waveapps accounts.

## Features
- **Document Fetching**: Runs paginated, durable Gmail, Google Drive, and Freshdesk intake into the local source/document ledger, with duplicate and provider-revision evidence. Google Photos intake is fail-closed until a user completes a supervised Picker session.
- **Advanced Document Processing**: Utilizes OCR (Tesseract, Google Cloud Vision), including Dutch OCR, handwritten recognition, template matching, and line item extraction.
- **Intelligent Categorization**: Employs rule-based, machine learning, and hybrid categorization approaches.
- **Automated Data Entry**: Supports data entry into mijngeldzaken.nl (via browser automation) and Waveapps (via API).
- **Learning System**: Incorporates feedback loops and learns from existing data to improve categorization accuracy.
- **Validation**: Validates extracted data against predefined rules and patterns.
- **Error Handling & Recovery**: Robust error handling with retry mechanisms and manual review interfaces for flagged documents.
- **Performance Optimization**: Includes batch processing, caching, and performance optimization strategies.
- **Security**: Manages credentials securely using encryption.
- **Compliance**: Checks documents against regulatory compliance rules.
- **Mobile Capture**: Provides a module for mobile document capture integration.
- **Automated Reconciliation**: Reconciles processed transactions with banking data.
- **Data Migration**: Tools for migrating existing financial data.
- **Budget Management**: Helps in tracking and managing budgets.
- **Banking API Integration**: Integrates with banking APIs to fetch transaction data.
- **Financial Analysis**: Generates financial reports and insights.
- **Backup & Restore**: Manages backup and restoration of application data.

## Project Structure
```
automated_bookkeeping/
├── config/
│   └── config_template.ini
├── docs/
│   ├── additional_improvements_requirements.md
│   ├── deployment_guide.md
│   ├── dependencies.md
│   ├── gap_analysis.md
│   ├── module_interfaces.md
│   ├── requirements_analysis.md
│   ├── security_approach.md
│   ├── technical_reference.md
│   └── user_guide.md
├── src/
│   ├── __init__.py
│   ├── banking/
│   │   └── banking_api.py
│   ├── backup/
│   │   └── backup_manager.py
│   ├── budget/
│   │   └── budget_manager.py
│   ├── categorizers/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── fallback_categorizer.py
│   │   ├── hybrid_categorizer.py
│   │   ├── ml_categorizer.py
│   │   └── rule_based_categorizer.py
│   ├── cloud_functions.py
│   ├── compliance/
│   │   └── regulatory_compliance.py
│   ├── config_loader.py
│   ├── data_entry/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── mijngeldzaken_handler.py
│   │   ├── waveapps_business_handler.py
│   │   └── waveapps_personal_handler.py
│   ├── document_fetchers/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── drive_fetcher.py
│   │   ├── freshdesk_fetcher.py
│   │   ├── gmail_fetcher.py
│   │   └── photos_fetcher.py
│   ├── document_processors/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── bilingual_processor.py
│   │   ├── dutch_ocr_processor.py
│   │   ├── enhanced_processor.py
│   │   ├── handwritten_recognition_processor.py
│   │   ├── line_item_extractor.py
│   │   ├── processor_factory.py
│   │   ├── processor_pipeline.py
│   │   ├── template_matching_processor.py
│   │   ├── tesseract_processor.py
│   │   ├── vendor_template_processor.py
│   │   └── vision_processor.py
│   ├── error_handling/
│   │   ├── __init__.py
│   │   ├── enhanced_error_recovery.py
│   │   └── manual_review.py
│   ├── financial_analysis/
│   │   └── financial_analyzer.py
│   ├── integration.py
│   ├── learning/
│   │   ├── __init__.py
│   │   ├── enhanced_learning_system.py
│   │   ├── feedback_learner.py
│   │   ├── learning_manager.py
│   │   ├── mijngeldzaken_analyzer.py
│   │   └── waveapps_analyzer.py
│   ├── main.py
│   ├── manual_review/
│   │   └── manual_review_interface.py
│   ├── migration/
│   │   ├── data_migration.py
│   │   └── migration_wizard.py
│   ├── mobile_capture/
│   │   └── mobile_document_capture.py
│   ├── performance/
│   │   ├── __init__.py
│   │   ├── batch_processor.py
│   │   ├── cache_manager.py
│   │   └── performance_optimizer.py
│   ├── reconciliation/
│   │   └── automated_reconciliation.py
│   ├── security/
│   │   ├── __init__.py
│   │   └── security_manager.py
│   ├── validation/
│   │   ├── receipt_validator.py
│   │   └── validation_manager.py
│   └── workflow/
│       ├── __init__.py
│       ├── controller.py
│       └── logger.py
├── tests/
│   ├── __init__.py
│   ├── test_banking_api.py
│   ├── test_bilingual_processor.py
│   ├── test_budget_manager.py
│   ├── test_categorizers.py
│   ├── test_components.py
│   ├── test_compliance.py
│   ├── test_config_loader.py
│   ├── test_data_entry.py
│   ├── test_document_fetchers.py
│   ├── test_document_processors.py
│   ├── test_error_handling.py
│   ├── test_financial_analysis.py
│   ├── test_integration.py
│   ├── test_learning_modules.py
│   ├── test_manual_review.py
│   ├── test_migration.py
│   ├── test_mobile_capture.py
│   ├── test_performance.py
│   ├── test_photos_fetcher.py
│   ├── test_receipt_validator.py
│   ├── test_reconciliation.py
│   ├── test_security.py
│   └── test_workflow.py
├── Dockerfile
├── package.py
└── requirements.txt
```

## Setup and Installation

### Prerequisites
- Python 3.9+
- pip (Python package installer)
- Docker (optional, for containerized deployment)
- Google Cloud SDK (if deploying to Google Cloud Functions)

### Local Installation
1.  **Clone the repository (or extract the zip file):**
    ```bash
    git clone <repository_url>
    cd automated_bookkeeping
    ```
    (If you received a zip file, extract it to your desired location and navigate into the `automated_bookkeeping` directory.)

2.  **Create a virtual environment (recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure the application:**
    Copy `config/config_template.ini` to `config/config.ini` and fill in your credentials and settings.
    ```bash
    cp config/config_template.ini config/config.ini
    # Open config/config.ini and edit with your details
    ```
    **Security Note**: For sensitive credentials, it is highly recommended to use environment variables instead of directly editing `config.ini`. The `ConfigLoader` is designed to prioritize environment variables prefixed with `APP_` (e.g., `APP_GMAIL_CLIENT_ID` will override `gmail.client_id` in `config.ini`).

### Docker Installation
1.  **Build the Docker image:**
    ```bash
    docker build -t automated-bookkeeping .
    ```

2.  **Run the Docker container:**
    ```bash
    docker run -it --rm \\
        -v /path/to/your/local/data:/app/data \\
        -e APP_GMAIL_CLIENT_ID="your_client_id" \\
        -e APP_GMAIL_CLIENT_SECRET="your_client_secret" \\
        automated-bookkeeping
    ```
    (Replace `/path/to/your/local/data` with a path on your host machine to persist data like logs, downloaded documents, etc. Provide necessary environment variables for credentials.)

## Usage

### Running the Workflow Locally
To run the main automated bookkeeping workflow:
```bash
python src/main.py
```

### Running Tests
To run all unit and integration tests:
```bash
python -m unittest discover tests
```

### Building Deployment Packages
Use the `package.py` script to create deployable zip files:
```bash
python package.py
# This will create packages in the `dist/` directory
```

## Deployment

### Google Cloud Functions
1.  **Ensure `gcloud` CLI is configured and authenticated.**
2.  **Deploy the `process_document_cloud_function` (triggered by GCS events):**
    ```bash
    gcloud functions deploy process_document_cloud_function \\
        --runtime python39 \\
        --trigger-bucket YOUR_INPUT_BUCKET_NAME \\
        --entry-point process_document_cloud_function \\
        --source . \\
        --memory 256MB \\
        --timeout 300s \\
        --set-env-vars GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service_account_key.json
    ```
3.  **Deploy the `trigger_workflow_http` (HTTP trigger for full workflow):**
    ```bash
    gcloud functions deploy trigger_workflow_http \\
        --runtime python39 \\
        --trigger-http \\
        --entry-point trigger_workflow_http \\
        --source . \\
        --memory 512MB \\
        --timeout 540s \\
        --allow-unauthenticated # Or configure appropriate authentication
    ```
    (Adjust memory and timeout as needed. Ensure `requirements.txt` and `config.ini` are in the deployment package.)

## Contributing

Contributions are welcome! Please follow these steps:
1.  Fork the repository.
2.  Create a new branch (`git checkout -b feature/your-feature-name`).
3.  Make your changes.
4.  Write and run tests.
5.  Commit your changes (`git commit -m 'Add new feature'`).
6.  Push to the branch (`git push origin feature/your-feature-name`).
7.  Create a new Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details (if applicable).

## Contact

For questions or support, please contact [Your Name/Email/GitHub Profile].


