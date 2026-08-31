#Requires -Version 5.1
<#
.SYNOPSIS
  Batch Repo-first Generate or PushSteps and summarize every asset.

.DESCRIPTION
  Action defaults to Generate. Run, SyncCheck, and CheckRun are not exposed.
  DryRun prints the plan without invoking ApifoxRepoFirst.ps1.

.EXAMPLE
  .\scripts\ApifoxRepoFirstBatch.ps1 -Group smoke
  .\scripts\ApifoxRepoFirstBatch.ps1 -Assets local_offers_options,papi_2548
  .\scripts\ApifoxRepoFirstBatch.ps1 -Action PushSteps -Group payment -DryRun
#>
[CmdletBinding()]
param(
    [ValidateSet("Generate", "PushSteps")]
    [string]$Action = "Generate",

    [string[]]$Assets = @(),

    [ValidateSet("", "all", "payment", "smoke")]
    [string]$Group = "",

    [switch]$DryRun,

    [switch]$FailFast
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function GetRepoRoot {
    [CmdletBinding()]
    [OutputType([string])]
    param()

    return (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

function GetMappedAssetKeys {
    [CmdletBinding()]
    [OutputType([string[]])]
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    $mapper = Join-Path $RepoRoot "tools\apifox-cli\MapGeneratorAssets.py"
    if (-not (Test-Path -LiteralPath $mapper -PathType Leaf)) {
        throw "Asset mapper not found: $mapper"
    }

    $raw = & python $mapper --repo-root $RepoRoot @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Asset mapping failed: $($raw -join [Environment]::NewLine)"
    }

    $keys = @(
        $raw |
            ForEach-Object { ([string]$_).Trim() } |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    )
    return , $keys
}

function ResolveBatchAssets {
    [CmdletBinding()]
    [OutputType([string[]])]
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [string[]]$ExplicitAssets = @(),
        [string]$GroupName = ""
    )

    $known = GetMappedAssetKeys -RepoRoot $RepoRoot -Arguments @("--list-assets")
    $knownSet = @{}
    foreach ($knownAsset in $known) {
        $knownSet[$knownAsset] = $true
    }

    $requested = New-Object System.Collections.Generic.List[string]
    foreach ($asset in @($ExplicitAssets)) {
        $trimmed = ([string]$asset).Trim()
        if ($trimmed) {
            $requested.Add($trimmed)
        }
    }
    if (-not [string]::IsNullOrWhiteSpace($GroupName)) {
        $groupArgs = if ($GroupName -eq "all") {
            @("--list-assets")
        }
        else {
            @("--group", $GroupName)
        }
        $groupAssets = GetMappedAssetKeys -RepoRoot $RepoRoot -Arguments $groupArgs
        foreach ($asset in $groupAssets) {
            $requested.Add($asset)
        }
    }
    if ($requested.Count -eq 0) {
        throw "No assets selected; pass -Assets or -Group all|payment|smoke"
    }

    $result = New-Object System.Collections.Generic.List[string]
    $seen = @{}
    foreach ($asset in $requested) {
        if (-not $knownSet.ContainsKey($asset)) {
            throw "Unknown asset '$asset'; check .apifox/suites.yaml"
        }
        if (-not $seen.ContainsKey($asset)) {
            $seen[$asset] = $true
            $result.Add($asset)
        }
    }
    return , $result.ToArray()
}

function InvokeAssetAction {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][string]$RepoFirstScript,
        [Parameter(Mandatory = $true)][string]$Asset,
        [Parameter(Mandatory = $true)][ValidateSet("Generate", "PushSteps")]
        [string]$SelectedAction
    )

    if ($SelectedAction -eq "Generate") {
        # 复用主入口，确保反模式、suites 与最终 Collection 门禁不会被批处理绕过。
        & $RepoFirstScript -Action Generate -Asset $Asset
        return
    }
    # PushSteps reuses the single-asset entry and never forwards CheckRun.
    & $RepoFirstScript -Action PushSteps -Asset $Asset
}

$RepoRoot = GetRepoRoot
$RepoFirstScript = Join-Path $RepoRoot "scripts\ApifoxRepoFirst.ps1"
if (-not (Test-Path -LiteralPath $RepoFirstScript -PathType Leaf)) {
    throw "Single-asset entry not found: $RepoFirstScript"
}

$SelectedAssets = ResolveBatchAssets `
    -RepoRoot $RepoRoot `
    -ExplicitAssets $Assets `
    -GroupName $Group

Write-Host (
    "Batch Action={0} Assets={1} DryRun={2} FailFast={3}" -f
    $Action,
    ($SelectedAssets -join ","),
    [bool]$DryRun,
    [bool]$FailFast
) -ForegroundColor Yellow

$Results = New-Object System.Collections.Generic.List[object]
foreach ($AssetKey in $SelectedAssets) {
    $StartedAt = Get-Date
    if ($DryRun) {
        Write-Host (
            "[DRY-RUN] & `"{0}`" -Action {1} -Asset {2}" -f
            $RepoFirstScript,
            $Action,
            $AssetKey
        ) -ForegroundColor DarkGray
        $Results.Add([pscustomobject]@{
                Asset   = $AssetKey
                Action  = $Action
                Status  = "DRY-RUN"
                Seconds = 0
                Error   = ""
            })
        continue
    }

    try {
        Write-Host "[$AssetKey] Starting $Action ..." -ForegroundColor Cyan
        InvokeAssetAction `
            -RepoRoot $RepoRoot `
            -RepoFirstScript $RepoFirstScript `
            -Asset $AssetKey `
            -SelectedAction $Action
        $Elapsed = [Math]::Round(((Get-Date) - $StartedAt).TotalSeconds, 2)
        $Results.Add([pscustomobject]@{
                Asset   = $AssetKey
                Action  = $Action
                Status  = "SUCCESS"
                Seconds = $Elapsed
                Error   = ""
            })
    }
    catch {
        $Elapsed = [Math]::Round(((Get-Date) - $StartedAt).TotalSeconds, 2)
        $Message = $_.Exception.Message
        Write-Host "[$AssetKey] Failed: $Message" -ForegroundColor Red
        $Results.Add([pscustomobject]@{
                Asset   = $AssetKey
                Action  = $Action
                Status  = "FAILED"
                Seconds = $Elapsed
                Error   = $Message
            })
        if ($FailFast) {
            break
        }
    }
}

Write-Host "`n=== Batch Summary ===" -ForegroundColor Yellow
$Results | Format-Table Asset, Action, Status, Seconds, Error -AutoSize

$SuccessCount = @($Results | Where-Object { $_.Status -eq "SUCCESS" }).Count
$FailureCount = @($Results | Where-Object { $_.Status -eq "FAILED" }).Count
$DryRunCount = @($Results | Where-Object { $_.Status -eq "DRY-RUN" }).Count
Write-Host (
    "Total={0} Success={1} Failed={2} DryRun={3}" -f
    $Results.Count,
    $SuccessCount,
    $FailureCount,
    $DryRunCount
)

if ($FailureCount -gt 0) {
    throw "Batch failed for $FailureCount asset(s); see Batch Summary"
}
