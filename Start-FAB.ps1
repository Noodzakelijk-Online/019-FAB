[CmdletBinding()]
param(
    [switch]$NoBrowser
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$webRoot = Join-Path $root "web"
$dataRoot = Join-Path $root "data"
$logsRoot = Join-Path $root "logs"
$runtimePath = Join-Path $dataRoot "fab-runtime.json"
$apiUrl = "http://127.0.0.1:5001/api/health"
$dashboardUrl = "http://127.0.0.1:3000/admin/operations"

function Test-FabEndpoint {
    param([Parameter(Mandatory = $true)][string]$Url)

    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 500
    }
    catch {
        $errorResponse = $_.Exception.Response
        if ($errorResponse -and [int]$errorResponse.StatusCode -in @(401, 403)) {
            return $true
        }
        return $false
    }
}

function Get-FabProcessId {
    param(
        [AllowNull()][object]$ProcessId,
        [Parameter(Mandatory = $true)][string]$CommandMarker
    )

    if (-not $ProcessId) {
        return $null
    }

    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction SilentlyContinue
    if (-not $process -or -not $process.CommandLine -or $process.CommandLine -notlike "*$CommandMarker*") {
        return $null
    }

    return [int]$process.ProcessId
}

function Wait-FabEndpoint {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [Parameter(Mandatory = $true)][string]$Name,
        [int]$TimeoutSeconds = 45
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        if (Test-FabEndpoint -Url $Url) {
            return
        }
        Start-Sleep -Milliseconds 500
    } while ((Get-Date) -lt $deadline)

    throw "$Name did not become ready at $Url within $TimeoutSeconds seconds. Check $logsRoot."
}

Set-Location -LiteralPath $root

$python = Get-Command python -ErrorAction Stop
$pnpm = Get-Command pnpm.cmd -ErrorAction Stop

& $python.Source -c "import flask, PIL, pytesseract, pdf2image, langdetect, googleapiclient" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing FAB local runtime dependencies..."
    & $python.Source -m pip install -r (Join-Path $root "requirements-local.txt")
    if ($LASTEXITCODE -ne 0) {
        throw "FAB local runtime dependency installation failed with exit code $LASTEXITCODE."
    }
}

if (-not (Test-Path -LiteralPath (Join-Path $root "config\config.ini"))) {
    Copy-Item -LiteralPath (Join-Path $root "config\config_template.ini") -Destination (Join-Path $root "config\config.ini")
}
if (-not (Test-Path -LiteralPath (Join-Path $webRoot ".env"))) {
    Copy-Item -LiteralPath (Join-Path $webRoot ".env.example") -Destination (Join-Path $webRoot ".env")
}

@(
    $dataRoot,
    (Join-Path $dataRoot "backups"),
    (Join-Path $dataRoot "reports"),
    (Join-Path $dataRoot "source_downloads"),
    (Join-Path $dataRoot "exports"),
    (Join-Path $root "downloads\sort-out"),
    $logsRoot
) | ForEach-Object {
    New-Item -ItemType Directory -Path $_ -Force | Out-Null
}

$tesseractCandidates = @(
    "C:\Program Files\Tesseract-OCR\tesseract.exe",
    "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    (Join-Path $env:LOCALAPPDATA "Programs\Tesseract-OCR\tesseract.exe")
)
$tesseractPath = $tesseractCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $tesseractPath -and (Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Host "Installing the local Tesseract OCR engine..."
    & winget install --id tesseract-ocr.tesseract --exact --source winget --silent --accept-source-agreements --accept-package-agreements --disable-interactivity | Out-Host
    $tesseractPath = $tesseractCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if (-not $tesseractPath) {
    Write-Warning "Tesseract OCR is not installed. Receipt OCR will remain unavailable until it is installed."
}
else {
    $tessdataRoot = Join-Path $dataRoot "tessdata"
    New-Item -ItemType Directory -Path $tessdataRoot -Force | Out-Null
    $installedTessdata = Join-Path (Split-Path -Parent $tesseractPath) "tessdata"
    foreach ($languageFile in @("eng.traineddata", "osd.traineddata")) {
        $sourceLanguage = Join-Path $installedTessdata $languageFile
        $targetLanguage = Join-Path $tessdataRoot $languageFile
        if ((Test-Path -LiteralPath $sourceLanguage) -and -not (Test-Path -LiteralPath $targetLanguage)) {
            Copy-Item -LiteralPath $sourceLanguage -Destination $targetLanguage
        }
    }

    $dutchLanguage = Join-Path $tessdataRoot "nld.traineddata"
    if (-not (Test-Path -LiteralPath $dutchLanguage)) {
        Write-Host "Installing Dutch OCR language data..."
        $dutchLanguageUrl = "https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/87416418657359cb625c412a48b6e1d6d41c29bd/nld.traineddata"
        Invoke-WebRequest -Uri $dutchLanguageUrl -OutFile $dutchLanguage -UseBasicParsing
    }
    $dutchLanguageHash = (Get-FileHash -LiteralPath $dutchLanguage -Algorithm SHA256).Hash
    if ($dutchLanguageHash -ne "CED0E5E046A84C908A6AA7ACCBEF9A232C4A5D9A8276691B81C6EE64D02963F6") {
        Remove-Item -LiteralPath $dutchLanguage -Force
        throw "Dutch OCR language data failed checksum verification."
    }
}

$popplerPath = & $python.Source -c "from src.utils.tesseract_runtime import resolve_poppler_path; print(resolve_poppler_path({}) or '')"
if (-not $popplerPath -and (Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Host "Installing Poppler PDF rendering tools..."
    & winget install --id oschwartz10612.Poppler --exact --source winget --silent --accept-source-agreements --accept-package-agreements --disable-interactivity | Out-Host
    $popplerPath = & $python.Source -c "from src.utils.tesseract_runtime import resolve_poppler_path; print(resolve_poppler_path({}) or '')"
}
if (-not $popplerPath) {
    Write-Warning "Poppler is not installed. Image OCR will work, but PDF OCR will remain unavailable."
}

if (-not (Test-Path -LiteralPath (Join-Path $webRoot "node_modules"))) {
    Write-Host "Installing FAB dashboard dependencies..."
    & $pnpm.Source --dir $webRoot install --frozen-lockfile
    if ($LASTEXITCODE -ne 0) {
        throw "Dashboard dependency installation failed with exit code $LASTEXITCODE."
    }
}

$savedRuntime = $null
if (Test-Path -LiteralPath $runtimePath) {
    try {
        $savedRuntime = Get-Content -LiteralPath $runtimePath -Raw | ConvertFrom-Json
    }
    catch {
        Write-Warning "Ignoring unreadable runtime metadata at $runtimePath."
    }
}

$apiPid = $null
$workerPid = $null
$webPid = $null
if ($savedRuntime) {
    $apiPid = Get-FabProcessId -ProcessId $savedRuntime.apiPid -CommandMarker "src.operations.local_api"
    $workerPid = Get-FabProcessId -ProcessId $savedRuntime.workerPid -CommandMarker "src.run_worker"
    $webPid = Get-FabProcessId -ProcessId $savedRuntime.webPid -CommandMarker "pnpm"
}

if (-not (Test-FabEndpoint -Url $apiUrl)) {
    $apiProcess = Start-Process -FilePath $python.Source -ArgumentList @("-m", "src.operations.local_api") -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logsRoot "local-api.out.log") -RedirectStandardError (Join-Path $logsRoot "local-api.err.log") -PassThru
    $apiPid = $apiProcess.Id
}

if (-not $workerPid) {
    $workerProcess = Start-Process -FilePath $python.Source -ArgumentList @("-m", "src.run_worker") -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logsRoot "worker.out.log") -RedirectStandardError (Join-Path $logsRoot "worker.err.log") -PassThru
    $workerPid = $workerProcess.Id
}

if (-not (Test-FabEndpoint -Url $dashboardUrl)) {
    $webProcess = Start-Process -FilePath $pnpm.Source -ArgumentList @("--dir", $webRoot, "dev") -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logsRoot "web.out.log") -RedirectStandardError (Join-Path $logsRoot "web.err.log") -PassThru
    $webPid = $webProcess.Id
}

Wait-FabEndpoint -Url $apiUrl -Name "FAB ledger API"
Wait-FabEndpoint -Url $dashboardUrl -Name "FAB operator dashboard" -TimeoutSeconds 60
if (-not (Get-FabProcessId -ProcessId $workerPid -CommandMarker "src.run_worker")) {
    throw "FAB autonomous worker exited during startup. Check logs\worker.err.log."
}

[ordered]@{
    startedAt = (Get-Date).ToUniversalTime().ToString("o")
    root = $root
    apiPid = $apiPid
    workerPid = $workerPid
    webPid = $webPid
    apiUrl = $apiUrl
    dashboardUrl = $dashboardUrl
} | ConvertTo-Json | Set-Content -LiteralPath $runtimePath -Encoding utf8

Write-Host ""
Write-Host "FAB is ready." -ForegroundColor Green
Write-Host "Dashboard: $dashboardUrl"
Write-Host "Detailed ledger: http://127.0.0.1:5001/"
Write-Host "Use Stop-FAB.cmd to stop the local services."

if (-not $NoBrowser) {
    Start-Process $dashboardUrl
}
