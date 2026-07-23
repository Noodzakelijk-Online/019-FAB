[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$runtimePath = Join-Path $root "data\fab-runtime.json"
$workerRuntimePath = Join-Path $root "data\fab-worker-runtime.json"

Set-Location -LiteralPath $root

function Get-FabInstanceId {
    param([Parameter(Mandatory = $true)][string]$Path)

    $normalized = [System.IO.Path]::GetFullPath($Path).TrimEnd("\", "/").Replace("\", "/")
    if ($env:OS -eq "Windows_NT") {
        $normalized = $normalized.ToLowerInvariant()
    }
    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($normalized)
        return ([System.BitConverter]::ToString($sha256.ComputeHash($bytes))).Replace("-", "").ToLowerInvariant()
    }
    finally {
        $sha256.Dispose()
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

function Test-FabEndpoint {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [Parameter(Mandatory = $true)][string]$ExpectedService,
        [string]$ApiToken = "",
        [string]$ExpectedInstanceRoot = "",
        [switch]$AllowLegacyInstance
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
        if ($ExpectedInstanceRoot) {
            $instanceIdProperty = $response.PSObject.Properties["instanceId"]
            $instanceId = if ($instanceIdProperty) { [string]$instanceIdProperty.Value } else { "" }
            if (-not $instanceId -and $AllowLegacyInstance) {
                $legacyRootProperty = $response.PSObject.Properties["instanceRoot"]
                $legacyRoot = if ($legacyRootProperty) { [string]$legacyRootProperty.Value } else { "" }
                if (-not $legacyRoot) {
                    return $false
                }
                $actualLegacyRoot = [System.IO.Path]::GetFullPath($legacyRoot).TrimEnd("\", "/")
                $expectedLegacyRoot = [System.IO.Path]::GetFullPath($ExpectedInstanceRoot).TrimEnd("\", "/")
                return $actualLegacyRoot -eq $expectedLegacyRoot
            }
            $expectedInstanceId = Get-FabInstanceId -Path $ExpectedInstanceRoot
            if (-not $instanceId -or $instanceId -ne $expectedInstanceId) {
                return $false
            }
        }
        return $true
    }
    catch {
        return $false
    }
}

function Find-RunningFabApiProcessIds {
    param(
        [Parameter(Mandatory = $true)][string]$ExpectedRoot,
        [string]$ApiToken = ""
    )

    $matches = [System.Collections.Generic.List[int]]::new()
    $processes = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -eq "python.exe" -and
            $_.CommandLine -and
            $_.CommandLine -like "*src.operations.local_api*"
        }
    foreach ($process in $processes) {
        $listeners = Get-NetTCPConnection -State Listen -OwningProcess $process.ProcessId -ErrorAction SilentlyContinue |
            Where-Object { $_.LocalAddress -in @("127.0.0.1", "::1") } |
            Sort-Object LocalPort -Unique
        foreach ($listener in $listeners) {
            $url = "http://127.0.0.1:$($listener.LocalPort)/api/health"
            if (Test-FabEndpoint -Url $url -ExpectedService "fab-ledger-api" -ApiToken $ApiToken -ExpectedInstanceRoot $ExpectedRoot -AllowLegacyInstance) {
                $matches.Add([int]$process.ProcessId)
                break
            }
        }
    }
    return @($matches | Select-Object -Unique)
}

function Get-FabWorkerRuntimeProcessId {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$ExpectedRoot
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return $null
    }
    try {
        $runtime = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
        $actualRoot = [System.IO.Path]::GetFullPath([string]$runtime.instanceRoot).TrimEnd("\", "/")
        $expected = [System.IO.Path]::GetFullPath($ExpectedRoot).TrimEnd("\", "/")
        if ($actualRoot -ne $expected) {
            return $null
        }
        return Get-FabProcessId -ProcessId $runtime.pid -CommandMarker "src.run_worker"
    }
    catch {
        return $null
    }
}

function Stop-FabProcessTree {
    param(
        [AllowNull()][object]$ProcessId,
        [Parameter(Mandatory = $true)][string]$CommandMarker,
        [Parameter(Mandatory = $true)][string]$Name
    )

    if (-not $ProcessId) {
        return
    }

    $rootProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction SilentlyContinue
    if (-not $rootProcess) {
        return
    }
    if (-not $rootProcess.CommandLine -or $rootProcess.CommandLine -notlike "*$CommandMarker*") {
        Write-Warning "Refusing to stop PID $ProcessId because it no longer matches $Name."
        return
    }

    $processIds = [System.Collections.Generic.List[int]]::new()
    $pending = [System.Collections.Generic.Queue[int]]::new()
    $pending.Enqueue([int]$ProcessId)
    while ($pending.Count -gt 0) {
        $currentId = $pending.Dequeue()
        $processIds.Add($currentId)
        Get-CimInstance Win32_Process -Filter "ParentProcessId = $currentId" -ErrorAction SilentlyContinue | ForEach-Object {
            $pending.Enqueue([int]$_.ProcessId)
        }
    }

    for ($index = $processIds.Count - 1; $index -ge 0; $index--) {
        Stop-Process -Id $processIds[$index] -Force -ErrorAction SilentlyContinue
    }
    Write-Host "Stopped $Name."
}

$runtime = $null
if (Test-Path -LiteralPath $runtimePath) {
    try {
        $runtime = Get-Content -LiteralPath $runtimePath -Raw | ConvertFrom-Json
    }
    catch {
        Write-Warning "Ignoring unreadable runtime metadata at $runtimePath."
    }
}

$apiToken = ""
try {
    $python = Get-Command python -ErrorAction Stop
    $apiToken = & $python.Source -c "from src.config_loader import ConfigLoader; c=ConfigLoader('config/config.ini').get_all_config(); print(str(c.get('fab_local_api_token') or c.get('fab_operations_api_token') or c.get('operations_api_token') or ''))"
}
catch {
    Write-Warning "FAB could not read its API token while recovering runtime ownership."
}
$apiToken = [string]$apiToken

$apiPid = $null
$workerPid = $null
$webPid = $null
if ($runtime) {
    $runtimeOwned = $false
    try {
        $runtimeOwned = (
            [System.IO.Path]::GetFullPath([string]$runtime.root).TrimEnd("\", "/") -eq
            [System.IO.Path]::GetFullPath($root).TrimEnd("\", "/")
        )
    }
    catch {
        $runtimeOwned = $false
    }
    $apiPid = Get-FabProcessId -ProcessId $runtime.apiPid -CommandMarker "src.operations.local_api"
    $workerPid = Get-FabProcessId -ProcessId $runtime.workerPid -CommandMarker "src.run_worker"
    $webPid = Get-FabProcessId -ProcessId $runtime.webPid -CommandMarker "pnpm"
    if (
        -not $runtime.apiUrl -or
        -not (Test-FabEndpoint -Url $runtime.apiUrl -ExpectedService "fab-ledger-api" -ApiToken $apiToken -ExpectedInstanceRoot $root -AllowLegacyInstance:$runtimeOwned)
    ) {
        $apiPid = $null
    }
    if (
        $webPid -and $runtime.webIdentityUrl -and
        -not (Test-FabEndpoint -Url $runtime.webIdentityUrl -ExpectedService "fab-operator-dashboard" -ExpectedInstanceRoot $root -AllowLegacyInstance:$runtimeOwned)
    ) {
        $webPid = $null
    }
}
$apiPids = [System.Collections.Generic.List[int]]::new()
if ($apiPid) {
    $apiPids.Add([int]$apiPid)
}
foreach ($discoveredApiPid in @(Find-RunningFabApiProcessIds -ExpectedRoot $root -ApiToken $apiToken)) {
    if (-not $apiPids.Contains([int]$discoveredApiPid)) {
        $apiPids.Add([int]$discoveredApiPid)
    }
}
$managedWorkerPid = Get-FabWorkerRuntimeProcessId -Path $workerRuntimePath -ExpectedRoot $root
if ($managedWorkerPid) {
    $workerPid = $managedWorkerPid
}
elseif (Test-Path -LiteralPath $workerRuntimePath) {
    $workerPid = $null
}

if (-not $runtime -and $apiPids.Count -eq 0 -and -not $workerPid) {
    Write-Host "No owned FAB services were found. The managed services are already stopped."
}

Stop-FabProcessTree -ProcessId $webPid -CommandMarker "pnpm" -Name "FAB dashboard"
Stop-FabProcessTree -ProcessId $workerPid -CommandMarker "src.run_worker" -Name "FAB autonomous worker"
foreach ($ownedApiPid in $apiPids) {
    Stop-FabProcessTree -ProcessId $ownedApiPid -CommandMarker "src.operations.local_api" -Name "FAB ledger API"
}

try {
    $python = Get-Command python -ErrorAction Stop
    $cleanupScript = @"
from src.config_loader import ConfigLoader
from src.operations.local_ledger import LocalOperationsLedger, default_ledger_path

config = ConfigLoader(config_file='config/config.ini').get_all_config()
ledger_path = str(
    config.get('fab_local_ledger_path')
    or config.get('operations_ledger_path')
    or default_ledger_path()
)
ledger = LocalOperationsLedger(ledger_path)
released = [
    lease_name
    for lease_name in ('local_connector_intake', 'local_autonomous_cycle')
    if ledger.force_release_runtime_lease(
        lease_name,
        actor='Stop-FAB.ps1',
        reason='owned_services_stopped',
    )
]
print(chr(44).join(released))
"@
    $releasedLeases = & $python.Source -c $cleanupScript
    if ($LASTEXITCODE -ne 0) {
        throw "Lease cleanup exited with code $LASTEXITCODE."
    }
    if ($releasedLeases) {
        Write-Host "Released stopped FAB runtime leases: $releasedLeases"
    }
}
catch {
    Write-Warning "FAB services stopped, but runtime lease cleanup failed: $($_.Exception.Message)"
}

Remove-Item -LiteralPath $runtimePath -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $workerRuntimePath -Force -ErrorAction SilentlyContinue
Write-Host "FAB local services are stopped."
