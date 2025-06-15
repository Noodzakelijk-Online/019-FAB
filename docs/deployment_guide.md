# Deployment Guide for Automated Bookkeeping Solution

This guide provides instructions for deploying the Automated Bookkeeping Solution to various environments, including local setups and Google Cloud Functions.

## 1. Local Deployment

Local deployment is suitable for development, testing, and running the solution on a dedicated machine or server within your own infrastructure.

### 1.1. Prerequisites

*   **Python 3.9+** installed.
*   **`pip`** (Python package installer).
*   **`git`** (if cloning from repository).
*   **Tesseract OCR**: Install Tesseract OCR engine and language packs (`eng`, `nld`) on your system. Refer to Tesseract's official documentation for installation instructions specific to your OS.
    *   **Ubuntu/Debian**: `sudo apt-get update && sudo apt-get install -y tesseract-ocr tesseract-ocr-eng tesseract-ocr-nld`
    *   **macOS (Homebrew)**: `brew install tesseract && brew install tesseract-lang`
    *   **Windows**: Download installer from [Tesseract-OCR GitHub](https://tesseract-ocr.github.io/tessdoc/Downloads.html).
*   **Playwright Browsers**: For `mijngeldzaken.nl` automation, Playwright requires browser binaries. After installing Python dependencies, run:
    ```bash
    playwright install --with-deps chromium
    ```

### 1.2. Deployment Steps

1.  **Obtain the Project Files:**

    *   **From a Zip Archive**: Extract the provided `automated_bookkeeping_local_YYYYMMDD_HHMMSS.zip` file to your desired deployment directory (e.g., `/opt/automated_bookkeeping`).
    *   **From Git Repository**: Clone the repository:
        ```bash
        git clone <repository_url>
        cd automated_bookkeeping
        ```

2.  **Set up Python Environment:**

    It is highly recommended to use a Python virtual environment.
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate.bat`
    ```

3.  **Install Python Dependencies:**

    Navigate to the project root directory and install the required Python packages:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure the Application:**

    Copy the `config_template.ini` to `config.ini` and edit it with your specific settings and credentials. Refer to the `user_guide.md` for detailed configuration instructions.
    ```bash
    cp config/config_template.ini config/config.ini
    # Edit config/config.ini
    ```
    **Security Best Practice**: For sensitive information (API keys, passwords), use environment variables. The `ConfigLoader` will automatically pick up environment variables prefixed with `APP_` (e.g., `APP_GMAIL_CLIENT_ID` will override `gmail.client_id` in `config.ini`).

5.  **Run the Application:**

    You can run the main workflow manually:
    ```bash
    python src/main.py
    ```
    For continuous operation, consider using process managers like `systemd` (Linux) or `Supervisor` to keep the script running and restart it on failures.

### 1.3. Running as a System Service (Linux example with systemd)

1.  **Create a systemd service file** (e.g., `/etc/systemd/system/bookkeeping.service`):
    ```ini
    [Unit]
    Description=Automated Bookkeeping Service
    After=network.target

    [Service]
    User=your_username
    WorkingDirectory=/path/to/your/automated_bookkeeping
    ExecStart=/path/to/your/automated_bookkeeping/venv/bin/python src/main.py
    Restart=always
    Environment="APP_GMAIL_CLIENT_ID=your_client_id" "APP_GMAIL_CLIENT_SECRET=your_client_secret" # Add all necessary env vars

    [Install]
    WantedBy=multi-user.target
    ```
    *   Replace `your_username` with your actual username.
    *   Replace `/path/to/your/automated_bookkeeping` with the actual path to your project directory.
    *   Add all required environment variables for credentials and sensitive settings.

2.  **Reload systemd, enable, and start the service:**
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable bookkeeping.service
    sudo systemctl start bookkeeping.service
    ```

3.  **Check service status:**
    ```bash
    sudo systemctl status bookkeeping.service
    ```

## 2. Docker Deployment

Docker provides a consistent and isolated environment for running the application, simplifying dependency management.

### 2.1. Prerequisites

*   **Docker** installed on your deployment machine.

### 2.2. Deployment Steps

1.  **Obtain the Project Files:**

    Ensure you have the entire project directory, including the `Dockerfile`.

2.  **Build the Docker Image:**

    Navigate to the project root directory (where `Dockerfile` is located) and build the image:
    ```bash
    docker build -t automated-bookkeeping:latest .
    ```
    This might take some time as it installs Tesseract and Playwright browsers.

3.  **Run the Docker Container:**

    ```bash
    docker run -d --name bookkeeping-app \\
        -v /path/on/host/for/data:/app/data \\
        -v /path/on/host/for/config:/app/config \\
        -e APP_GMAIL_CLIENT_ID="your_client_id" \\
        -e APP_GMAIL_CLIENT_SECRET="your_client_secret" \\
        # Add all other necessary APP_ environment variables
        automated-bookkeeping:latest
    ```
    *   `-d`: Runs the container in detached mode (in the background).
    *   `--name bookkeeping-app`: Assigns a name to your container for easy management.
    *   `-v /path/on/host/for/data:/app/data`: Mounts a host directory to `/app/data` inside the container. Use this to persist logs, downloaded documents, and other dynamic data.
    *   `-v /path/on/host/for/config:/app/config`: Mounts your `config` directory (containing `config.ini`) from the host to the container. This allows you to manage configuration externally.
    *   `-e APP_...`: Pass sensitive credentials and other configurations as environment variables. This is the recommended way for Docker deployments.

4.  **Check Container Logs:**

    ```bash
    docker logs bookkeeping-app
    ```

## 3. Google Cloud Functions Deployment

Google Cloud Functions (GCF) is a serverless execution environment for building and connecting cloud services. It's ideal for event-driven processing.

### 3.1. Prerequisites

*   **Google Cloud Project**: A Google Cloud Platform project with billing enabled.
*   **Google Cloud SDK (`gcloud`)**: Installed and configured on your local machine.
*   **Service Account**: A service account with necessary permissions (e.g., Cloud Functions Developer, Cloud Storage Admin, Gmail API, Drive API, Photos Library API, etc.). Download its JSON key file.
*   **Cloud Storage Bucket**: An input bucket to trigger document processing (if using GCS trigger).

### 3.2. Deployment Steps

1.  **Prepare Deployment Package:**

    Use the `package.py` script to create a cloud-optimized zip archive. Navigate to the project root and run:
    ```bash
    python package.py
    ```
    This will create a `automated_bookkeeping_cloud_YYYYMMDD_HHMMSS.zip` file in the `dist/` directory.

2.  **Upload Configuration and Credentials (Securely):**

    *   **`config.ini`**: For Cloud Functions, it's best to pass all configurations via environment variables during deployment or use Google Secret Manager. Avoid including `config.ini` directly in the deployment package if it contains sensitive data.
    *   **Credentials**: Store your Google API credentials (for Gmail, Drive, Photos, Vision API) securely, preferably in Google Secret Manager, and access them via environment variables or directly in your function code. For this example, we assume `GOOGLE_APPLICATION_CREDENTIALS` points to a service account key.

3.  **Deploy `process_document_cloud_function` (GCS Triggered):**

    This function is triggered when a new document is uploaded to a specified Google Cloud Storage bucket.
    ```bash
    gcloud functions deploy process_document_cloud_function \\
        --runtime python39 \\
        --trigger-bucket YOUR_INPUT_BUCKET_NAME \\
        --entry-point process_document_cloud_function \\
        --source dist/automated_bookkeeping_cloud_YYYYMMDD_HHMMSS.zip \\
        --memory 512MB \\
        --timeout 540s \\
        --set-env-vars GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service_account_key.json,APP_GMAIL_CLIENT_ID=...,APP_GMAIL_CLIENT_SECRET=... \\
        --service-account your-service-account@your-project-id.iam.gserviceaccount.com
    ```
    *   Replace `YOUR_INPUT_BUCKET_NAME` with the name of your GCS bucket.
    *   Replace `YYYYMMDD_HHMMSS` with the actual timestamp in your zip file name.
    *   Adjust `--memory` and `--timeout` as needed based on your document processing complexity.
    *   `--set-env-vars`: Provide all necessary configuration parameters as environment variables. Separate multiple variables with commas.
    *   `--service-account`: Specify the service account that the function will run as. This service account needs permissions to access GCS, Gmail API, Drive API, etc.

4.  **Deploy `trigger_workflow_http` (HTTP Triggered):**

    This function can be invoked via an HTTP request to start the entire automated bookkeeping workflow.
    ```bash
    gcloud functions deploy trigger_workflow_http \\
        --runtime python39 \\
        --trigger-http \\
        --entry-point trigger_workflow_http \\
        --source dist/automated_bookkeeping_cloud_YYYYMMDD_HHMMSS.zip \\
        --memory 1024MB \\
        --timeout 540s \\
        --allow-unauthenticated \\
        --set-env-vars GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service_account_key.json,APP_GMAIL_CLIENT_ID=...,APP_GMAIL_CLIENT_SECRET=... \\
        --service-account your-service-account@your-project-id.iam.gserviceaccount.com
    ```
    *   `--allow-unauthenticated`: Allows unauthenticated invocations. For production, consider removing this and implementing proper authentication (e.g., using Google Cloud IAM).
    *   Note the increased memory for the full workflow.

### 3.3. Monitoring and Logging

Google Cloud Functions automatically integrates with Google Cloud Logging. You can view function logs in the Google Cloud Console under "Logging > Logs Explorer".


