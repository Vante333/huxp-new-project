param(
    [string]$JsonFile,
    [switch]$Persist
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Set-EnvValue {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Value,
        [switch]$PersistToUser
    )

    # Set for current PowerShell session.
    Set-Item -Path "Env:$Name" -Value $Value

    if ($PersistToUser) {
        [Environment]::SetEnvironmentVariable($Name, $Value, "User")
    }
}

function Read-InputJson {
    param([string]$Path)

    if ($Path) {
        if (-not (Test-Path -LiteralPath $Path)) {
            throw "JSON file not found: $Path"
        }
        return Get-Content -LiteralPath $Path -Raw
    }

    $stdin = [Console]::In.ReadToEnd()
    if ([string]::IsNullOrWhiteSpace($stdin)) {
        throw "Please provide -JsonFile or pipe JSON into script."
    }
    return $stdin
}

$rawJson = Read-InputJson -Path $JsonFile
$payload = $rawJson | ConvertFrom-Json

$target = $payload.data.entitlements.moduleExclusiveEntitlements | Where-Object { $_.module -eq 1 } | Select-Object -First 1
if (-not $target) {
    throw "moduleExclusiveEntitlements does not contain module=1."
}

$detail = $target.details
$fields = @(
    "cardholderExclusiveEntitlements",
    "guestsExclusiveEntitlements",
    "sharedEntitlements",
    "purchasedEntitlements"
)

$prefix = "MODULE1_"
$written = @()

foreach ($field in $fields) {
    $value = [int]$detail.$field
    if ($value -ne 0) {
        $envName = "$prefix$($field.ToUpper())"
        Set-EnvValue -Name $envName -Value "$value" -PersistToUser:$Persist
        $written += [PSCustomObject]@{
            name  = $envName
            value = $value
        }
    }
}

if ($written.Count -eq 0) {
    Write-Host "No non-zero fields found for module=1."
    exit 0
}

Write-Host "Environment variables set:"
$written | ForEach-Object { Write-Host ("  {0}={1}" -f $_.name, $_.value) }

if ($Persist) {
    Write-Host "Persisted to user environment variables."
} else {
    Write-Host "Applied to current session only."
}
