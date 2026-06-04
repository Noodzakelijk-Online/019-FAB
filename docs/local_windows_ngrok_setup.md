# FAB Local Windows 11 and ngrok Setup

FAB is local-first. ngrok mode is only for temporary testing, support, callbacks, or demonstrations.

## Local Windows 11 Mode

1. Install Python 3.10 or newer.
2. Clone the repository.
3. Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

4. Install dependencies:

```powershell
pip install -r requirements.txt
playwright install chromium
```

5. Install Tesseract OCR for Windows and make sure `tesseract.exe` is available on PATH, or configure `tesseract_cmd` in `config/config.ini`.

6. Create local config:

```powershell
copy config\config_template.ini config\config.ini
```

7. Edit `config/config.ini` and set a long random dashboard token.

8. Start the dashboard:

```powershell
python src\run_dashboard.py
```

9. Health check:

```text
http://127.0.0.1:5001/health
```

Protected endpoints require the configured dashboard token in the request header named `X-FAB-Token`.

## ngrok Mode

1. Start FAB locally first.
2. Start ngrok:

```powershell
ngrok http 5001
```

3. Copy the ngrok URL into `public_base_url` in `config/config.ini` if callbacks need a public base URL.

## Security Rules for ngrok

- Do not expose FAB without a configured dashboard token.
- Do not place private credentials in URLs.
- Stop ngrok when it is no longer needed.
- Treat ngrok as temporary access, not permanent production hosting.

## Current Dashboard Endpoints

- `GET /health` — unprotected health check.
- `GET /` — summary overview.
- `GET /documents` — recent documents.
- `GET /documents/<document_id>` — document detail.
- `GET /manual-review` — review items.
- `POST /manual-review/<item_id>/resolve` — resolve review item.
- `GET /audit-log` — recent audit log.
- `GET /posting-attempts` — posting attempts and dry runs.
