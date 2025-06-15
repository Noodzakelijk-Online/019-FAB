# User Guide for Automated Bookkeeping Solution

## 1. Introduction

Welcome to the Automated Bookkeeping Solution! This guide will walk you through how to set up, configure, and use the system to automate your financial document processing and data entry.

## 2. System Overview

The Automated Bookkeeping Solution is designed to streamline your bookkeeping process by:

*   **Fetching Documents**: Automatically retrieves financial documents (receipts, invoices, statements) from various sources like Gmail, Google Drive, Google Photos, and Freshdesk.
*   **Processing Documents**: Extracts key information from these documents using advanced OCR (Optical Character Recognition) and data extraction techniques.
*   **Categorizing Transactions**: Categorizes transactions into predefined accounts (e.g., Personal, Business, Handicap-related) using a combination of rule-based and machine learning models.
*   **Automated Data Entry**: Enters the processed and categorized data into your chosen bookkeeping platforms, currently supporting mijngeldzaken.nl and Waveapps.
*   **Learning and Improvement**: Continuously learns from your data and feedback to improve categorization accuracy over time.

## 3. Getting Started

Before you can use the system, you need to complete the initial setup steps.

### 3.1. Prerequisites

Ensure you have the following installed on your system:

*   **Python 3.9 or higher**: Download from [python.org](https://www.python.org/downloads/).
*   **`pip`**: Python's package installer, usually comes with Python.
*   **`git`** (optional, if cloning from a repository): Download from [git-scm.com](https://git-scm.com/downloads).
*   **Docker** (optional, for containerized deployment): Download from [docker.com](https://www.docker.com/products/docker-desktop).
*   **Google Cloud SDK** (optional, if deploying to Google Cloud Functions): Follow instructions on [cloud.google.com](https://cloud.google.com/sdk/docs/install).

### 3.2. Installation

1.  **Download the Project:**

    If you received a zip archive, extract its contents to your desired directory. For example, `C:\bookkeeping_app` on Windows or `/home/user/bookkeeping_app` on Linux/macOS.

    If you are cloning from a Git repository:
    ```bash
    git clone <repository_url>
    cd automated_bookkeeping
    ```

2.  **Create a Python Virtual Environment (Recommended):**

    A virtual environment isolates your project's dependencies from other Python projects.
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install Dependencies:**

    Navigate to the project's root directory (where `requirements.txt` is located) and install the necessary Python packages:
    ```bash
    pip install -r requirements.txt
    ```

## 4. Configuration

The system's behavior is controlled by the `config/config.ini` file. A template `config_template.ini` is provided. You **must** copy this template and rename it to `config.ini`.

```bash
cp config/config_template.ini config/config.ini
```

Now, open `config/config.ini` in a text editor and fill in the required details for each section. Below is a breakdown of the key sections and parameters.

**Security Note**: For sensitive credentials (like API keys, passwords), it is highly recommended to use **environment variables** instead of directly writing them into `config.ini`. The system's `ConfigLoader` is designed to automatically override `config.ini` values with environment variables that are prefixed with `APP_` (e.g., `APP_GMAIL_CLIENT_ID` will override `gmail.client_id` in `config.ini`).

### 4.1. `[app]` Section

General application settings.

*   `log_file`: Path to the application log file. (e.g., `logs/app.log`)

### 4.2. `[gmail]` Section

Configuration for fetching documents from Gmail.

*   `credentials_file`: Path to your Google API credentials JSON file (downloaded from Google Cloud Console). (e.g., `credentials/gmail_credentials.json`)
*   `token_file`: Path where the OAuth 2.0 token will be stored after first authentication. (e.g., `tokens/gmail_token.json`)
*   `attachment_download_dir`: Directory to save downloaded Gmail attachments. (e.g., `downloads/gmail`)
*   `search_query`: Gmail search query to filter emails. Examples:
    *   `has:attachment from:"example@vendor.com" subject:"Invoice"`
    *   `label:receipts after:2025/01/01`

### 4.3. `[google_drive]` Section

Configuration for fetching documents from Google Drive.

*   `credentials_file`: Path to your Google API credentials JSON file. (e.g., `credentials/drive_credentials.json`)
*   `token_file`: Path where the OAuth 2.0 token will be stored. (e.g., `tokens/drive_token.json`)
*   `download_dir`: Directory to save downloaded Drive files. (e.g., `downloads/drive`)
*   `folder_id`: The ID of the specific Google Drive folder to monitor. You can find this in the URL when viewing the folder in Google Drive.
*   `file_types`: Comma-separated list of file extensions to download (e.g., `pdf,jpg,png`).

### 4.4. `[freshdesk]` Section

Configuration for fetching documents from Freshdesk.

*   `api_key`: Your Freshdesk API key.
*   `domain`: Your Freshdesk domain (e.g., `yourcompany.freshdesk.com`).
*   `download_dir`: Directory to save downloaded Freshdesk attachments. (e.g., `downloads/freshdesk`)
*   `ticket_status`: Comma-separated list of ticket statuses to fetch attachments from (e.g., `2,3` for Open, Pending).

### 4.5. `[google_photos]` Section

Configuration for fetching documents from Google Photos.

*   `credentials_file`: Path to your Google API credentials JSON file. (e.g., `credentials/photos_credentials.json`)
*   `token_file`: Path where the OAuth 2.0 token will be stored. (e.g., `tokens/photos_token.json`)
*   `album_name`: The name of the Google Photos album to monitor for receipts/documents.
*   `download_dir`: Directory to save downloaded Google Photos media. (e.g., `downloads/photos`)

### 4.6. `[processor]` Section

Settings for document processing.

*   `ocr_processor`: The primary OCR engine to use. Options: `vision` (Google Cloud Vision), `tesseract`, `dutch_ocr`, `handwritten_recognition`, `bilingual`.
*   `line_item_extraction_enabled`: `true` or `false`. Enable/disable line item extraction.
*   `template_matching_templates_dir`: Directory containing JSON templates for structured data extraction. (e.g., `templates/document_templates`)
*   `vendor_templates_file`: Path to a JSON file defining vendor-specific extraction rules. (e.g., `config/vendor_templates.json`)
*   `tesseract_cmd`: Path to the Tesseract executable (if not in system PATH). (e.g., `/usr/local/bin/tesseract`)
*   `tesseract_lang`: Default Tesseract language (e.g., `eng`, `nld`).
*   `dutch_ocr_lang`: Language for Dutch OCR processor (e.g., `nld`).
*   `handwritten_model_path`: Path to the trained model for handwritten recognition.

### 4.7. `[categorizer]` Section

Settings for document categorization.

*   `categorization_rules`: Path to a JSON file defining rule-based categorization rules. (e.g., `config/categorization_rules.json`)
*   `default_fallback_category`: The category to assign if no other categorization method yields a confident result. (e.g., `Manual Review`)
*   `ml_confidence_threshold`: Minimum confidence score for ML categorizer to accept a prediction (0.0 to 1.0).
*   `ml_model_path`: Path to the trained ML categorization model. (e.g., `models/ml_categorizer_model.joblib`)
*   `ml_vectorizer_path`: Path to the TF-IDF vectorizer used by the ML model. (e.g., `models/tfidf_vectorizer.joblib`)

### 4.8. `[mijngeldzaken]` Section

Settings for data entry into mijngeldzaken.nl.

*   `username`: Your mijngeldzaken.nl username.
*   `password`: Your mijngeldzaken.nl password.
*   `login_url`: The login page URL for mijngeldzaken.nl.
*   `import_url`: The URL for the CSV import page on mijngeldzaken.nl.
*   `csv_template`: JSON string defining the CSV structure and mapping from extracted data. Example: `{"columns": ["Date", "Description", "Amount", "Category"], "mapping": {"Date": "extracted_data.transaction_date", "Description": "extracted_data.description", "Amount": "extracted_data.total_amount", "Category": "category"}, "delimiter": ";"}`
*   `category_mapping`: JSON string mapping internal categories to mijngeldzaken.nl categories. Example: `{"Personal": "Huishouden", "Business": "Zakelijk"}`

### 4.9. `[waveapps_business]` Section

Settings for data entry into Waveapps Business account.

*   `access_token`: Your Waveapps Business API access token.
*   `business_id`: Your Waveapps Business ID.
*   `category_mapping`: JSON string mapping internal categories to Waveapps Business categories. Example: `{"Business": "Office Supplies", "Travel": "Travel Expenses"}`

### 4.10. `[waveapps_personal]` Section

Settings for data entry into Waveapps Personal account.

*   `access_token`: Your Waveapps Personal API access token.
*   `personal_id`: Your Waveapps Personal ID.
*   `category_mapping`: JSON string mapping internal categories to Waveapps Personal categories. Example: `{"Handicaps": "Medical Expenses", "Personal": "Household"}`
*   `handicap_tag`: A tag to append to descriptions for handicap-related expenses. (e.g., `#handicap`)

### 4.11. `[validation]` Section

Settings for data validation.

*   `receipt_validation_required_fields`: Comma-separated list of fields that must be present in extracted data for a receipt to be considered valid. (e.g., `vendor_name,total_amount,transaction_date`)
*   `btw_number_pattern`: Regular expression pattern for validating BTW (VAT) numbers. (e.g., `NL\d{9}B\d{2}`)

### 4.12. `[budget]` Section

Settings for budget management.

*   `budget_file`: Path to the JSON file storing budget definitions. (e.g., `data/budgets.json`)

### 4.13. `[banking]` Section

Settings for banking API integration.

*   `banking_api_endpoint`: URL of the banking API endpoint.
*   `banking_api_credentials`: JSON string with banking API credentials. Example: `{"client_id": "your_client_id", "client_secret": "your_client_secret"}`

### 4.14. `[reconciliation]` Section

Settings for automated reconciliation.

*   `reconciliation_threshold`: The maximum allowable difference between transaction amounts for them to be considered a match. (e.g., `0.05` for 5 cents)

### 4.15. `[manual_review]` Section

Settings for manual review interface.

*   `manual_review_queue_file`: Path to the JSON file storing documents awaiting manual review. (e.g., `data/manual_review_queue.json`)

### 4.16. `[backup]` Section

Settings for backup and restore.

*   `backup_base_dir`: Base directory where backups will be stored. (e.g., `backups`)
*   `backup_paths`: Comma-separated list of files/directories to include in backups. (e.g., `data,config/config.ini`)
*   `backup_config`: JSON string defining backup type. Example: `{"type": "zip"}`

### 4.17. `[error_handling]` Section

Settings for error handling and recovery.

*   `error_recovery_max_retries`: Maximum number of retries for failed operations.
*   `error_recovery_retry_delay_seconds`: Delay between retries in seconds.
*   `email_notifications_enabled`: `true` or `false`. Enable/disable email notifications for critical errors.

## 5. Running the Application

### 5.1. Running the Workflow Locally

To execute the main automated bookkeeping workflow, navigate to the project's root directory and run:

```bash
python src/main.py
```

This will initiate the document fetching, processing, categorization, and data entry pipeline based on your `config.ini` settings.

### 5.2. Running Tests

It's highly recommended to run the tests to ensure everything is set up correctly and functioning as expected. From the project's root directory:

```bash
python -m unittest discover tests
```

### 5.3. Building Deployment Packages

The `package.py` script can be used to create deployable zip archives for local or cloud environments.

To build packages:

```bash
python package.py
```

This will create `automated_bookkeeping_local_YYYYMMDD_HHMMSS.zip` and `automated_bookkeeping_cloud_YYYYMMDD_HHMMSS.zip` files in the `dist/` directory.

## 6. Advanced Usage and Customization

### 6.1. Customizing Categorization Rules

Edit the JSON file specified in `[categorizer] categorization_rules` to define or modify your rule-based categorization logic. This file typically contains rules based on keywords, vendors, or other extracted data points.

### 6.2. Training ML Categorizer

If you intend to use the ML Categorizer, you will need to train the model with your own historical data. The `LearningManager` module provides functionalities for this. Refer to the `technical_reference.md` for details on how to prepare your data and trigger model training.

### 6.3. Extending Document Fetchers/Processors/Data Entry Handlers

The system is designed with a modular architecture. You can extend its capabilities by creating new modules that adhere to the `base.py` interfaces in `src/document_fetchers`, `src/document_processors`, and `src/data_entry`. Refer to `module_interfaces.md` for detailed API specifications.

### 6.4. Manual Review Interface

Documents that cannot be automatically processed or categorized with high confidence are flagged for manual review. The `ManualReviewInterface` (though currently a placeholder in this version) is intended to provide a web-based interface to review these documents, correct errors, and provide feedback to the learning system.

## 7. Troubleshooting

*   **Check Logs**: Always start by examining the `app.log` file (or the path specified in `config.ini`) for error messages and warnings.
*   **Configuration Errors**: Double-check your `config.ini` file for typos, incorrect paths, or missing credentials. Ensure sensitive information is correctly set via environment variables if you choose that method.
*   **Dependency Issues**: If you encounter `ModuleNotFoundError` or similar, ensure all dependencies are installed (`pip install -r requirements.txt`) and your virtual environment is activated.
*   **Google API Authentication**: For Gmail, Drive, and Photos fetchers, the first run will typically open a browser window for OAuth 2.0 authentication. Ensure you complete this process. If issues persist, delete the `token.json` files and try again.
*   **Playwright Issues**: If mijngeldzaken.nl automation fails, ensure Playwright browsers are installed (`playwright install --with-deps chromium`) and that your internet connection is stable.

## 8. Support

For further assistance, please refer to the `technical_reference.md` and `deployment_guide.md` documents, or contact the development team.


