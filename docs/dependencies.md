# Dependencies

This document lists the external libraries and tools required for the Automated Bookkeeping Solution.

## Python Libraries

The following Python libraries are used in the project. They are listed in `requirements.txt` for easy installation using `pip`.

- `google-api-python-client`: For interacting with Google APIs (Gmail, Drive, Photos).
- `google-auth-oauthlib`: For OAuth 2.0 authentication with Google services.
- `google-cloud-vision`: Google Cloud Vision API client library for OCR.
- `Pillow`: Python Imaging Library (PIL) fork, used for image processing.
- `pytesseract`: Python wrapper for Tesseract OCR.
- `opencv-python`: OpenCV library for advanced image processing (e.g., deskewing, noise reduction).
- `python-freshdesk`: For interacting with the Freshdesk API.
- `playwright`: For browser automation (mijngeldzaken.nl).
- `pandas`: For data manipulation, especially for CSV generation and historical data analysis.
- `numpy`: For numerical operations, often used with pandas and image processing.
- `scikit-learn`: For machine learning models in categorization and learning modules.
- `tensorflow` or `pytorch`: (Optional, depending on specific ML model implementation) For deep learning models.
- `cryptography`: For secure credential encryption.
- `python-dotenv`: For loading environment variables.
- `fastapi` or `flask`: (Optional, for manual review UI or local API) For building web interfaces.
- `uvicorn`: (If using FastAPI) ASGI server.
- `requests`: For general HTTP requests to various APIs (e.g., Waveapps).
- `beautifulsoup4` or `lxml`: For parsing HTML/XML if needed (e.g., for specific web scraping scenarios, though Playwright handles most of this).
- `schedule`: For scheduling recurring tasks.
- `APScheduler`: (Alternative to schedule) For more advanced scheduling.
- `pyyaml`: For parsing YAML configuration files (if used).
- `loguru`: (Optional) For enhanced logging.
- `pytest`: For unit and integration testing.

## External Tools / Services

- **Google Cloud Platform (GCP)**:
    - Google Cloud Vision API (for primary OCR).
    - Google Cloud Storage (for temporary storage of documents, if needed).
    - Google Cloud Functions / Cloud Run (for cloud deployment).
    - Google Secret Manager (for secure credential storage in cloud).
- **Tesseract OCR Engine**: Required if Tesseract is used as a fallback OCR method. Needs to be installed in the execution environment.
- **Waveapps API**: For integration with Waveapps accounting software.
- **mijngeldzaken.nl**: The web application for which browser automation is performed.
- **Dutch Banking APIs**: Specific APIs for Dutch banks for real-time transaction data (availability varies by bank).

## Development Tools

- `git`: Version control.
- `docker`: For containerization and creating reproducible environments.
- `black`, `flake8`: Code formatting and linting tools.
- `mypy`: Static type checker.

## Installation

All Python dependencies can be installed using pip:

```bash
pip install -r requirements.txt
```

External tools like Tesseract OCR Engine might require separate installation steps depending on the operating system and deployment environment.

