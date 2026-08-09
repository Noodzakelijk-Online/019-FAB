[CmdletBinding()]
param(
    [int]$TimeoutSeconds = 45,
    [string]$Url = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$runtimePath = Join-Path $root "data\fab-runtime.json"
$mainConfig = Join-Path $env:LOCALAPPDATA "ngrok\ngrok.yml"
$ngrok = Get-Command ngrok -ErrorAction Stop
$python = Get-Command python -ErrorAction Stop

if (-not (Test-Path -LiteralPath $runtimePath)) {
    throw "FAB is not running. Start it with Start-FAB.cmd first."
}
if (-not (Test-Path -LiteralPath $mainConfig)) {
    throw "ngrok is not configured for this Windows user."
}

$runtime = Get-Content -LiteralPath $runtimePath -Raw | ConvertFrom-Json
$apiBaseUrl = [string]$runtime.apiBaseUrl
$apiUri = [System.Uri]$apiBaseUrl
if ($apiUri.Host -notin @("127.0.0.1", "localhost", "::1")) {
    throw "FAB ngrok verification only accepts a loopback API endpoint."
}
if ($Url) {
    $requestedUrl = [System.Uri]$Url
    if ($requestedUrl.Scheme -ne "https" -or -not $requestedUrl.Host) {
        throw "-Url must be a complete HTTPS ngrok endpoint."
    }
}

$apiToken = & $python.Source -c "from src.config_loader import ConfigLoader; c=ConfigLoader('config/config.ini').get_all_config(); print(str(c.get('fab_local_api_token') or c.get('fab_operations_api_token') or c.get('operations_api_token') or ''))"
if ($LASTEXITCODE -ne 0 -or ([string]$apiToken).Length -lt 32) {
    throw "Configure a strong FAB API token before using ngrok."
}
$apiToken = [string]$apiToken

function Find-AvailableLoopbackPort {
    param([int]$StartPort)
    foreach ($port in $StartPort..($StartPort + 20)) {
        $listener = [System.Net.Sockets.TcpListener]::new(
            [System.Net.IPAddress]::Loopback,
            $port
        )
        try {
            $listener.Start()
            return $port
        }
        catch {
            continue
        }
        finally {
            $listener.Stop()
        }
    }
    throw "No free ngrok inspection port is available."
}

$inspectionPort = Find-AvailableLoopbackPort -StartPort 4041
$id = [Guid]::NewGuid().ToString("N")
$overlayPath = Join-Path $env:TEMP "fab-ngrok-$id.yml"
$stdoutPath = Join-Path $env:TEMP "fab-ngrok-$id.out.log"
$stderrPath = Join-Path $env:TEMP "fab-ngrok-$id.err.log"
$overlay = "version: 3`nagent:`n  web_addr: 127.0.0.1:$inspectionPort`n"
[System.IO.File]::WriteAllText(
    $overlayPath,
    $overlay,
    (New-Object System.Text.UTF8Encoding($false))
)

$process = $null
try {
    & $ngrok.Source config check --config $mainConfig --config $overlayPath | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "The isolated ngrok verification configuration is invalid."
    }

    $arguments = @(
        "http", $apiUri.Port,
        "--config", $mainConfig,
        "--config", $overlayPath,
        "--log", "stdout",
        "--log-format", "json",
        "--name", "fab-verification"
    )
    if ($Url) {
        $arguments += @("--url", $Url)
    }

    $process = Start-Process `
        -FilePath $ngrok.Source `
        -ArgumentList $arguments `
        -WindowStyle Hidden `
        -RedirectStandardOutput $stdoutPath `
        -RedirectStandardError $stderrPath `
        -PassThru

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $tunnel = $null
    do {
        Start-Sleep -Milliseconds 500
        try {
            $tunnels = Invoke-RestMethod `
                -Uri "http://127.0.0.1:$inspectionPort/api/tunnels" `
                -TimeoutSec 2
            $tunnel = @(
                $tunnels.tunnels |
                    Where-Object {
                        $_.public_url -like "https://*" -and
                        ([string]$_.config.addr) -match ":$($apiUri.Port)$"
                    }
            ) | Select-Object -First 1
        }
        catch {
            $tunnel = $null
        }
    } while (-not $tunnel -and -not $process.HasExited -and (Get-Date) -lt $deadline)

    if (-not $tunnel) {
        $reason = if ($process.HasExited) {
            $process.WaitForExit()
            $process.Refresh()
            $diagnostic = @(
                Get-Content -LiteralPath $stderrPath -ErrorAction SilentlyContinue
                Get-Content -LiteralPath $stdoutPath -ErrorAction SilentlyContinue
            ) | Select-String -Pattern "ERR_NGROK_[0-9]+|authentication failed|failed to start|address already in use|bind:" |
                Select-Object -Last 1 -ExpandProperty Line
            $classified = if ($diagnostic) {
                ([string]$diagnostic -replace 'https?://\S+', '<endpoint>').Trim()
            }
            else {
                "no classified agent diagnostic was emitted"
            }
            "ngrok exited with code $($process.ExitCode): $classified"
        }
        else {
            "the temporary endpoint did not become ready"
        }
        throw "FAB ngrok verification failed: $reason."
    }

    $liveUrl = "$($tunnel.public_url)/api/live"
    $unauthorizedStatus = 0
    try {
        Invoke-WebRequest -Uri $liveUrl -UseBasicParsing -TimeoutSec 15 | Out-Null
        $unauthorizedStatus = 200
    }
    catch {
        if ($_.Exception.Response) {
            $unauthorizedStatus = [int]$_.Exception.Response.StatusCode
        }
    }

    $authorized = Invoke-RestMethod `
        -Uri $liveUrl `
        -Headers @{ Authorization = "Bearer $apiToken" } `
        -TimeoutSec 20
    if (
        $unauthorizedStatus -ne 401 -or
        [string]$authorized.status -ne "ok" -or
        -not [bool]$authorized.authRequired
    ) {
        throw "FAB ngrok authentication did not fail closed."
    }

    Write-Host "FAB ngrok HTTPS verification passed." -ForegroundColor Green
    Write-Host "Unauthenticated request: 401"
    Write-Host "Authenticated liveness: ok"
    Write-Host "The temporary FAB tunnel will now be stopped."
}
finally {
    $apiToken = ""
    if ($process -and -not $process.HasExited) {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        Wait-Process -Id $process.Id -Timeout 10 -ErrorAction SilentlyContinue
    }
    foreach ($path in @($overlayPath, $stdoutPath, $stderrPath)) {
        if (Test-Path -LiteralPath $path) {
            Remove-Item -LiteralPath $path -Force
        }
    }
}
