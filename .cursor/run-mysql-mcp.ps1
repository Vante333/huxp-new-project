# MySQL MCP：由 Cursor 以非交互子进程拉起；从仓库根 .env 读 MYSQL_*。
# 使用仓库内 mysql_mcp_server_local.py，由 uv 拉取 mcp / pymysql（避免 Windows 上 mysql-connector-python 偶发崩溃）。

function Write-McpLaunchErr {
    param([string]$Message)
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Message + [Environment]::NewLine)
    [void][System.Console]::OpenStandardError().Write($bytes, 0, $bytes.Length)
}

if (-not $PSScriptRoot) {
    Write-McpLaunchErr "run-mysql-mcp.ps1: PSScriptRoot is empty; cannot locate repo .env."
    exit 1
}
$RepoRoot = Split-Path -Parent $PSScriptRoot
$EnvFile = Join-Path $RepoRoot ".env"

if (-not (Test-Path -LiteralPath $EnvFile)) {
    Write-McpLaunchErr "[mysql-mcp] .env not found: $EnvFile (copy .env.example to .env and set MYSQL_* variables)."
    exit 1
}

Get-Content -LiteralPath $EnvFile -Encoding UTF8 | ForEach-Object {
    $line = $_.Trim()
    if ($line -eq "" -or $line.StartsWith("#")) { return }
    $eq = $line.IndexOf("=")
    if ($eq -lt 1) { return }
    $key = $line.Substring(0, $eq).Trim()
    $val = $line.Substring($eq + 1).Trim()
    if (
        ($val.Length -ge 2 -and $val.StartsWith('"') -and $val.EndsWith('"')) -or
        ($val.Length -ge 2 -and $val.StartsWith("'") -and $val.EndsWith("'"))
    ) {
        $val = $val.Substring(1, $val.Length - 2)
    }
    Set-Item -Path "env:$key" -Value $val
}

$required = @("MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE")
foreach ($name in $required) {
    $v = [Environment]::GetEnvironmentVariable($name, "Process")
    if ([string]::IsNullOrWhiteSpace($v)) {
        Write-McpLaunchErr "[mysql-mcp] Missing or empty $name after loading: $EnvFile"
        exit 1
    }
}

# 默认与 mysql_mcp_server 一致
if ([string]::IsNullOrWhiteSpace($env:MYSQL_HOST)) {
    Set-Item -Path "env:MYSQL_HOST" -Value "localhost"
}
if ([string]::IsNullOrWhiteSpace($env:MYSQL_PORT)) {
    Set-Item -Path "env:MYSQL_PORT" -Value "3306"
}

$uvx = Get-Command uvx -ErrorAction SilentlyContinue
if (-not $uvx) {
    Write-McpLaunchErr "[mysql-mcp] uvx not found in PATH. Install uv (https://docs.astral.sh/uv/) or add Python Scripts to system PATH."
    exit 1
}

$uvxExe = $uvx.Source
$uvxDir = Split-Path -Parent $uvxExe
$uvExe = Join-Path $uvxDir "uv.exe"
if (-not (Test-Path -LiteralPath $uvExe)) {
    Write-McpLaunchErr "[mysql-mcp] uv.exe not found next to uvx: $uvExe"
    exit 1
}

if (-not ($env:PATH -split [IO.Path]::PathSeparator | Where-Object { $_ -eq $uvxDir })) {
    $env:PATH = $uvxDir + [IO.Path]::PathSeparator + $env:PATH
}

$localScript = Join-Path $PSScriptRoot "mysql_mcp_server_local.py"
if (-not (Test-Path -LiteralPath $localScript)) {
    Write-McpLaunchErr "[mysql-mcp] missing: $localScript"
    exit 1
}

Set-Location -LiteralPath $RepoRoot
& $uvExe run --with "mcp>=1.0.0" --with "pymysql>=1.1.0" python $localScript
exit $LASTEXITCODE
