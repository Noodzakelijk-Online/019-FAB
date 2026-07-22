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
$defaultApiPort = 5001
$defaultWebPort = 3000

function Test-FabEndpoint {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [Parameter(Mandatory = $true)][string]$ExpectedService,
        [string]$ApiToken = "",
        [string]$ExpectedLocalApiEndpoint = ""
    )

    try {
        $request = @{
            Uri = $Url
            UseBasicParsing = $true
            TimeoutSec = 2
        }
        if ($ApiToken) {
            $request.Headers = @{ Authorization = "Bearer $ApiToken" }
        }
        $response = Invoke-RestMethod @request
        if ([string]$response.service -ne $ExpectedService) {
            return $false
        }
        if ($ExpectedLocalApiEndpoint -and ([string]$response.localApiEndpoint).TrimEnd("/") -ne $ExpectedLocalApiEndpoint.TrimEnd("/")) {
            return $false
        }
        return $true
    }
    catch {
        return $false
    }
}

function Test-TcpPortAvailable {
    param([Parameter(Mandatory = $true)][int]$Port)

    $listener = [System.Net.Sockets.TcpListener]::new(
        [System.Net.IPAddress]::Loopback,
        $Port
    )
    try {
        $listener.Start()
        return $true
    }
    catch {
        return $false
    }
    finally {
        $listener.Stop()
    }
}

function Find-AvailableFabPort {
    param(
        [Parameter(Mandatory = $true)][int]$StartPort,
        [int]$Attempts = 20
    )

    for ($port = $StartPort; $port -lt ($StartPort + $Attempts); $port++) {
        if (Test-TcpPortAvailable -Port $port) {
            return $port
        }
    }
    throw "No free loopback port was found from $StartPort through $($StartPort + $Attempts - 1)."
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
        [Parameter(Mandatory = $true)][string]$ExpectedService,
        [string]$ApiToken = "",
        [string]$ExpectedLocalApiEndpoint = "",
        [int]$TimeoutSeconds = 45
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        if (Test-FabEndpoint -Url $Url -ExpectedService $ExpectedService -ApiToken $ApiToken -ExpectedLocalApiEndpoint $ExpectedLocalApiEndpoint) {
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

$apiToken = & $python.Source -c "from src.config_loader import ConfigLoader; c=ConfigLoader('config/config.ini').get_all_config(); print(str(c.get('fab_local_api_token') or c.get('fab_operations_api_token') or c.get('operations_api_token') or ''))"
if ($LASTEXITCODE -ne 0) {
    throw "FAB could not read its local API configuration."
}
$apiToken = [string]$apiToken

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
$apiUrl = $null
$dashboardUrl = $null
if ($savedRuntime) {
    $apiPid = Get-FabProcessId -ProcessId $savedRuntime.apiPid -CommandMarker "src.operations.local_api"
    $workerPid = Get-FabProcessId -ProcessId $savedRuntime.workerPid -CommandMarker "src.run_worker"
    $webPid = Get-FabProcessId -ProcessId $savedRuntime.webPid -CommandMarker "pnpm"
    if ($apiPid -and $savedRuntime.apiUrl -and (Test-FabEndpoint -Url $savedRuntime.apiUrl -ExpectedService "fab-ledger-api" -ApiToken $apiToken)) {
        $apiUrl = [string]$savedRuntime.apiUrl
    }
    else {
        $apiPid = $null
    }
    if ($webPid -and $savedRuntime.dashboardUrl) {
        $savedDashboardUri = [System.Uri]$savedRuntime.dashboardUrl
        $savedWebIdentityUrl = "$($savedDashboardUri.GetLeftPart([System.UriPartial]::Authority))/api/fab/runtime"
        $savedApiBaseUrl = if ($apiUrl) { ([System.Uri]$apiUrl).GetLeftPart([System.UriPartial]::Authority) } else { "" }
        if ($savedApiBaseUrl -and (Test-FabEndpoint -Url $savedWebIdentityUrl -ExpectedService "fab-operator-dashboard" -ExpectedLocalApiEndpoint $savedApiBaseUrl)) {
            $dashboardUrl = [string]$savedRuntime.dashboardUrl
        }
        else {
            $webPid = $null
        }
    }
}

if (-not $apiPid) {
    $apiPort = Find-AvailableFabPort -StartPort $defaultApiPort
    $apiUrl = "http://127.0.0.1:$apiPort/api/health"
    $previousApiPort = $env:FAB_LOCAL_API_PORT
    try {
        $env:FAB_LOCAL_API_PORT = [string]$apiPort
        $apiProcess = Start-Process -FilePath $python.Source -ArgumentList @("-m", "src.operations.local_api") -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logsRoot "local-api.out.log") -RedirectStandardError (Join-Path $logsRoot "local-api.err.log") -PassThru
        $apiPid = $apiProcess.Id
    }
    finally {
        if ($null -eq $previousApiPort) {
            Remove-Item Env:FAB_LOCAL_API_PORT -ErrorAction SilentlyContinue
        }
        else {
            $env:FAB_LOCAL_API_PORT = $previousApiPort
        }
    }
}
$apiBaseUrl = ([System.Uri]$apiUrl).GetLeftPart([System.UriPartial]::Authority)

if (-not $workerPid) {
    $workerProcess = Start-Process -FilePath $python.Source -ArgumentList @("-m", "src.run_worker") -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logsRoot "worker.out.log") -RedirectStandardError (Join-Path $logsRoot "worker.err.log") -PassThru
    $workerPid = $workerProcess.Id
}

if (-not $webPid) {
    $webPort = Find-AvailableFabPort -StartPort $defaultWebPort
    $dashboardUrl = "http://127.0.0.1:$webPort/admin/operations"
    $webIdentityUrl = "http://127.0.0.1:$webPort/api/fab/runtime"
    $previousWebPort = $env:PORT
    $previousLocalApiUrl = $env:FAB_LOCAL_API_URL
    try {
        $env:PORT = [string]$webPort
        $env:FAB_LOCAL_API_URL = $apiBaseUrl
        $webProcess = Start-Process -FilePath $pnpm.Source -ArgumentList @("--dir", $webRoot, "dev") -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logsRoot "web.out.log") -RedirectStandardError (Join-Path $logsRoot "web.err.log") -PassThru
        $webPid = $webProcess.Id
    }
    finally {
        if ($null -eq $previousWebPort) {
            Remove-Item Env:PORT -ErrorAction SilentlyContinue
        }
        else {
            $env:PORT = $previousWebPort
        }
        if ($null -eq $previousLocalApiUrl) {
            Remove-Item Env:FAB_LOCAL_API_URL -ErrorAction SilentlyContinue
        }
        else {
            $env:FAB_LOCAL_API_URL = $previousLocalApiUrl
        }
    }
}
else {
    $dashboardUri = [System.Uri]$dashboardUrl
    $webIdentityUrl = "$($dashboardUri.GetLeftPart([System.UriPartial]::Authority))/api/fab/runtime"
}

Wait-FabEndpoint -Url $apiUrl -Name "FAB ledger API" -ExpectedService "fab-ledger-api" -ApiToken $apiToken
Wait-FabEndpoint -Url $webIdentityUrl -Name "FAB operator dashboard" -ExpectedService "fab-operator-dashboard" -ExpectedLocalApiEndpoint $apiBaseUrl -TimeoutSeconds 60
if (-not (Get-FabProcessId -ProcessId $workerPid -CommandMarker "src.run_worker")) {
    throw "FAB autonomous worker exited during startup. Check logs\worker.err.log."
}

try {
    $driveStatusRequest = @{
        Uri = "$apiBaseUrl/api/drive-wave/status"
        UseBasicParsing = $true
        TimeoutSec = 5
    }
    if ($apiToken) {
        $driveStatusRequest.Headers = @{ Authorization = "Bearer $apiToken" }
    }
    $driveStatus = Invoke-RestMethod @driveStatusRequest
    if ($driveStatus.status -eq "needs_authorization") {
        Write-Warning "Google Drive is configured but not authorized. Run Authorize-FAB-GoogleDrive.cmd after installing the OAuth desktop credentials file."
    }
}
catch {
    Write-Warning "FAB could not read Drive authorization status during startup."
}

[ordered]@{
    startedAt = (Get-Date).ToUniversalTime().ToString("o")
    root = $root
    apiPid = $apiPid
    workerPid = $workerPid
    webPid = $webPid
    apiUrl = $apiUrl
    apiBaseUrl = $apiBaseUrl
    dashboardUrl = $dashboardUrl
    webIdentityUrl = $webIdentityUrl
} | ConvertTo-Json | Set-Content -LiteralPath $runtimePath -Encoding utf8

Write-Host ""
Write-Host "FAB is ready." -ForegroundColor Green
Write-Host "Dashboard: $dashboardUrl"
Write-Host "Detailed ledger: $apiBaseUrl/"
Write-Host "Use Stop-FAB.cmd to stop the local services."

if (-not $NoBrowser) {
    Start-Process $dashboardUrl
}
