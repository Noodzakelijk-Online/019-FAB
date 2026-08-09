# FAB Local Windows 11 and ngrok Setup

FAB is local-first. The supported Windows runtime is the authenticated API, autonomous worker, and production operator dashboard started together by the repository launcher.

## Local Windows 11 mode

1. Install Python 3.13, Node.js, pnpm, Tesseract OCR with Dutch and English language data, and Poppler PDF tools. The launcher creates and validates an isolated `.venv`; it does not install packages into the global Python runtime.
2. Create `config/config.ini` from `config/config_template.ini`.
3. Set a random `operations.api_token` of at least 32 characters. Do not paste it into URLs, browser storage, logs, or Git.
4. Start FAB:

```powershell
.\Start-FAB.ps1 -NoBrowser
```

5. Run the sanitized readiness check:

```powershell
python -m src.run_fab_doctor
```

The first start installs the local Python requirements into `.venv` and the dashboard packages into `web/node_modules` when they are absent. The launcher prints the selected URLs. Defaults are:

- Operator dashboard: `http://127.0.0.1:3000/admin/operations`
- Local API: `http://127.0.0.1:5001`
- Authenticated constant-time liveness: `GET /api/live`
- Authenticated deep health: `GET /api/health`

API clients use `Authorization: Bearer <token>`. The API runs under Waitress with bounded threads; the worker and dashboard are separate managed processes. `Stop-FAB.ps1` stops only the FAB instance recorded for this checkout.

## Temporary ngrok verification

Start FAB locally, configure ngrok for the Windows user, then run:

```powershell
.\Test-FAB-Ngrok.ps1
```

The verifier creates an isolated temporary agent, exposes only the local API port, proves an unauthenticated request receives `401`, proves an authenticated `/api/live` request succeeds, and then removes its temporary files and endpoint.

If the ngrok account requires a second reserved endpoint, supply it explicitly:

```powershell
.\Test-FAB-Ngrok.ps1 -Url https://your-reserved-endpoint.example
```

`ERR_NGROK_334` means the account already has an endpoint online. Do not stop or pool an unrelated endpoint; reserve a separate FAB endpoint and rerun with `-Url`.

## Exposure rules

- Never expose FAB without a strong API token.
- Keep the API and dashboard listeners on loopback unless an explicitly reviewed reverse proxy is used.
- Do not put credentials, document identifiers, or tokens in a public URL.
- Treat ngrok as temporary supervised access, not as production hosting or provider acceptance.
- Stop the temporary tunnel when verification finishes.
