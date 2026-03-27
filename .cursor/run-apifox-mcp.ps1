param(
    [Parameter(Mandatory = $true)][string]$ProjectId,
    [Parameter(Mandatory = $true)][string]$BranchId,
    [string]$ApifoxApiBaseUrl = "https://apifox.dragonpass.com.cn"
)

# MCP 由 Cursor 以非交互子进程拉起；此处不用 Write-Error，避免部分 PS 版本下
# PositionalParameterNotFound (WriteErrorCommand) 导致客户端只看到 ParameterBindingException。
# 错误信息用 UTF-8 写入 stderr，避免中文在 Cursor 日志里断码、误把后续输出粘成“脚本碎片”。
function Write-McpLaunchErr {
    param([string]$Message)
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Message + [Environment]::NewLine)
    [void][System.Console]::OpenStandardError().Write($bytes, 0, $bytes.Length)
}

if (-not $PSScriptRoot) {
    Write-McpLaunchErr "run-apifox-mcp.ps1: PSScriptRoot is empty; cannot locate repo .env."
    exit 1
}
$RepoRoot = Split-Path -Parent $PSScriptRoot
$EnvFile = Join-Path $RepoRoot ".env"

if (-not (Test-Path -LiteralPath $EnvFile)) {
    Write-McpLaunchErr "[apifox-mcp] .env not found: $EnvFile (copy .env.example to .env and set APIFOX_ACCESS_TOKEN)."
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

if ([string]::IsNullOrWhiteSpace($env:APIFOX_ACCESS_TOKEN)) {
    Write-McpLaunchErr "[apifox-mcp] Missing or empty APIFOX_ACCESS_TOKEN after loading: $EnvFile"
    exit 1
}

$npx = Get-Command npx -ErrorAction SilentlyContinue
if (-not $npx) {
    Write-McpLaunchErr "[apifox-mcp] npx not found in PATH; install Node.js."
    exit 1
}

& npx -y apifox-mcp-server@latest --project-id=$ProjectId --apifox-api-base-url=$ApifoxApiBaseUrl --branch-id=$BranchId
