# Requirements Analysis

This document outlines the detailed requirements for the Automated Bookkeeping Solution.

## Project Goal
Develop a fully automated system to fetch financial documents, extract relevant data, categorize them based on predefined rules (Personal, Business, Handicap-related), and enter the data into mijngeldzaken.nl (via automated browser upload) and two separate Waveapps accounts (preferably via API).

## Current Context
- Date: Monday, March 31, 2025
- User Location: Doornenburg, Gelderland, Netherlands

## Core Constraints & Technologies
- **Programming Language**: Python is strongly recommended due to library support for APIs, OCR, and browser automation.
- **No New Third-Party Tools**: Only use the APIs and capabilities of Gmail, Google Drive, Google Photos, Freshdesk, mijngeldzaken.nl, Waveapps, and potentially Google Cloud services (like Cloud Vision API). No external services like Zapier, Make, Dext, Nanonets etc.
- **Execution Environment**: The solution should be able to run both locally and in cloud environments (Google Cloud Functions, Google Cloud Run).
- **Security**: Secure storage and handling of all credentials (API keys, OAuth 2.0 tokens, website passwords) is critical. Use environment variables, secrets managers, or other secure methods – no hardcoding.

## Detailed Requirements

### 1. Document Fetching (Input Sources)

#### Gmail
- Use Gmail API (OAuth 2.0).
- Monitor inbox based on user-defined criteria (e.g., specific labels, senders, subjects) for emails with attachments (PDF, JPG, PNG etc.).
- Download qualifying attachments.

#### Google Drive
- Use Google Drive API (OAuth 2.0).
- Monitor a specific user-defined folder for new files.
- Download new files.

#### Freshdesk
- Use Freshdesk API (API Key).
- Monitor for new tickets/attachments based on user-defined criteria (tags, groups, keywords etc.). Define polling strategy or investigate webhooks.
- Download relevant attachments.

#### Google Photos
- Use Google Photos API (OAuth 2.0).
- Scan the entire Google Photos library for financial documents.

### 2. Document Processing (OCR & Data Extraction)

- Handle various input file types (PDF, image formats). PDF processing may require conversion to images for Tesseract.
- **OCR Method**: Google Cloud Vision API (primary) with Tesseract OCR (fallback).
- **Data Extraction**: Extract at minimum: Vendor Name, Transaction Date, Total Amount, Currency. Attempt extraction of: VAT/Tax amount, Description/Line Items.
- **Advanced Document Processing**: Specialized OCR models trained on Dutch financial documents, handwritten receipt recognition, vendor-specific template matching for common Dutch suppliers.
- **Bilingual Support**: Dual-language OCR processing optimized for both Dutch and English documents with language detection.

### 3. Categorization Logic

- Implement Python logic to assign one category (A, B, or C) based on extracted data.
- **Categories & Destinations**:
    - A (Personal): Target mijngeldzaken.nl. (Examples: Groceries, living costs).
    - B (Business): Target Waveapps.com (Business Account). (Examples: Business software, services).
    - C (Handicaps): Target Waveapps.com (Personal Account). (Examples: VA costs, specific guidance, special subscriptions).
- Use configurable lists/dictionaries for keywords, vendor names associated with each category.
- Implement fallback for uncategorized items (e.g., log and notify user for manual review).
- **Machine Learning Categorization**: Implement a model that learns from past categorizations to improve accuracy over time.
- **Learning from Existing Data**: Learn from existing data in WaveApps and Mijngeldzaken.nl accounts to improve accuracy and reduce manual work.

### 4. Data Entry & Formatting

#### Destination A (mijngeldzaken.nl)
- **CSV Generation**: Format extracted Category A data into a CSV file.
- **Automated Upload (Browser Automation)**: Use Playwright library in Python to automate login, navigation, upload, and confirmation.

#### Destination B (Waveapps.com - Business Account)
- **Primary Method**: API Integration using Waveapps API.
- **Fallback Method**: CSV Export if API is insufficient.

#### Destination C (Waveapps.com - Personal Account)
- **Primary Method**: API Integration using Waveapps API.
- **Fallback Method**: CSV Export if API fails.

### 5. Workflow Orchestration & Error Handling

- Develop a main script to manage the flow: Fetch -> Process -> Categorize -> Enter/Format.
- Implement comprehensive logging for traceability and debugging.
- Implement robust error handling for all stages (API timeouts, OCR failures, categorization misses, login errors, upload failures).
- Implement state management to prevent duplicate processing of documents (e.g., track file IDs, move processed files).
- Consider an email notification system (via Gmail API) for critical errors or items needing manual review.
- **Enhanced Error Handling and Recovery**: Build a more robust system for handling failures with retry mechanisms and manual review workflows.

### 6. Additional Improvements

#### Receipt Validation
- Implement a validation system that checks for legal compliance of receipts (proper BTW numbers, required information).
- Flag potentially fraudulent or incomplete receipts that might cause issues during tax audits.

#### Historical Data Migration
- Add tools to import historical data from existing spreadsheets or other accounting systems.
- This would provide more training data for the machine learning system from day one.

#### Expense Policy Enforcement
- Add capability to check expenses against household budgets (spending limits, approved vendors).
- Flag expenses that violate policies for review.

#### Integration with Banking APIs
- Direct integration with Dutch banking APIs (when available) for real-time transaction data.
- This would improve the reconciliation process and reduce the need for manual bank statement imports.

#### Advanced Reporting
- More sophisticated financial reporting capabilities beyond basic tax reports.
- Cash flow forecasting based on recurring expenses and historical patterns.

#### User Interface for Manual Review
- A simple web interface for reviewing documents that couldn't be automatically processed.
- This would streamline the manual review process for edge cases.

#### Backup and Disaster Recovery
- More robust backup strategies for processed documents and extracted data.
- Automated recovery procedures in case of system failure.


