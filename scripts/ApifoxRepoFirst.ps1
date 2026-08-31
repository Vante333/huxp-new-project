#Requires -Version 5.1
<#
.SYNOPSIS
  Apifox CLI · Repo-first：从仓库生成器同步 Postman Collection 到指定 Apifox 项目。

.DESCRIPTION
  默认资产 papi_2548（会籍 extensions），默认项目读 .apifox/settings.json（当前 346275）。
  凭据从仓库根 .env 读取 APIFOX_ACCESS_TOKEN，不写入本脚本。

.EXAMPLE
  .\scripts\ApifoxRepoFirst.ps1 -Action Generate
  .\scripts\ApifoxRepoFirst.ps1 -Action Import
  .\scripts\ApifoxRepoFirst.ps1 -Action Status
  .\scripts\ApifoxRepoFirst.ps1 -Action Run -ConfirmRun
  .\scripts\ApifoxRepoFirst.ps1 -Action Run -ConfirmRun -FullReports
  .\scripts\ApifoxRepoFirst.ps1 -Action PushSteps -CheckRun -ConfirmRun
  .\scripts\ApifoxRepoFirst.ps1 -Action SyncCheck -ConfirmRun
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("Generate", "Import", "Status", "WhoAmI", "Run", "Sync", "SyncCheck", "SyncTests", "PushSteps")]
    [string]$Action,

    # 资产 key：须存在于 .apifox/suites.yaml → assets.<key>（不再写死白名单）
    [string]$Asset = "papi_2548",

    [int]$ProjectId = 0,

    [string]$Branch = "",

    # apifox=场景+后置脚本（全量 CLI 推荐）；openapi=仅接口壳；postman=私有化常失败
    [ValidateSet("apifox", "openapi", "postman")]
    [string]$ImportFormat = "apifox",

    [switch]$SkipGenerate,

    [switch]$DryRun,

    # 推送后自动 apifox run 并汇总失败步骤（需 suites.yaml environment_id）
    [switch]$CheckRun,

    # 明确确认已核对数据集、业务 CSV 与 Environment；Run/SyncCheck/CheckRun 必填
    [switch]$ConfirmRun,

    # 默认复用该资产 suites.yaml 的 working_branch；勿为每次改脚本新建 AI 分支
    [string]$WorkingBranch = "",

    # 0 = 读 suites.yaml → assets.<key>.test_scenario_id
    [int]$ScenarioId = 0,

    # 0 = 读 suites.yaml → assets.<key>.environment_id
    [int]$EnvironmentId = 0,

    # 仅当长期工作分支不存在时才允许 create（默认关闭，防止刷出一堆 ai/*）
    [switch]$AllowCreateAiBranch,

    # 默认 cli,json；需要 HTML/JUnit 可视化时再加 -FullReports
    [switch]$FullReports
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Assert-RunExplicitlyConfirmed {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$SelectedAction,
        [Parameter(Mandatory = $true)][bool]$IsConfirmed
    )
    if ($IsConfirmed) {
        return
    }
    throw (
        "$SelectedAction 会执行在线 Apifox Run；请先确认：①现在要跑；" +
        "②鉴权数据集；③业务 CSV 已导入并勾选；④Environment。确认后显式加 -ConfirmRun。"
    )
}

function Get-RepoRoot {
    [CmdletBinding()]
    [OutputType([string])]
    param()
    return (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

function Import-DotEnvFile {
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)][string]$EnvFile)
    if (-not (Test-Path -LiteralPath $EnvFile)) {
        throw ".env not found: $EnvFile"
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
}

function Get-ApifoxSettings {
    [CmdletBinding()]
    [OutputType([hashtable])]
    param([Parameter(Mandatory = $true)][string]$RepoRoot)
    $path = Join-Path $RepoRoot ".apifox\settings.json"
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Missing $path"
    }
    $raw = Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json
    return @{
        ProjectId  = [int]$raw.projectId
        ApiBaseUrl = [string]$raw.apiBaseUrl
    }
}

function Resolve-RepoRelativePath {
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][string]$RelativePath
    )
    $norm = $RelativePath.Trim() -replace '/', '\'
    if ([System.IO.Path]::IsPathRooted($norm)) { return $norm }
    return (Join-Path $RepoRoot $norm)
}

function Get-SuitesYamlHelper {
    [CmdletBinding()]
    [OutputType([string])]
    param([Parameter(Mandatory = $true)][string]$RepoRoot)
    return (Join-Path $RepoRoot "tools\apifox-cli\ApifoxSuitesYaml.py")
}

function Get-SuitesAssetKeys {
    [CmdletBinding()]
    [OutputType([string[]])]
    param([Parameter(Mandatory = $true)][string]$RepoRoot)
    $helper = Get-SuitesYamlHelper -RepoRoot $RepoRoot
    if (-not (Test-Path -LiteralPath $helper)) {
        throw "Missing $helper"
    }
    $raw = & python $helper --repo-root $RepoRoot --list-keys 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "ApifoxSuitesYaml --list-keys failed: $raw"
    }
    $keys = @()
    foreach ($line in @($raw)) {
        $k = ([string]$line).Trim()
        if ($k) { $keys += $k }
    }
    return , $keys
}

function Get-SuitesAssetFields {
    [CmdletBinding()]
    [OutputType([hashtable])]
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][string]$AssetName
    )
    if (-not (Test-Path variable:script:SuitesAssetFieldsCache)) {
        $script:SuitesAssetFieldsCache = @{}
    }
    if ($script:SuitesAssetFieldsCache.ContainsKey($AssetName)) {
        return $script:SuitesAssetFieldsCache[$AssetName]
    }
    $helper = Get-SuitesYamlHelper -RepoRoot $RepoRoot
    $jsonText = & python $helper --repo-root $RepoRoot --asset $AssetName --format json 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "ApifoxSuitesYaml --asset $AssetName failed: $jsonText"
    }
    $obj = $jsonText | ConvertFrom-Json
    $fields = @{}
    foreach ($p in $obj.PSObject.Properties) {
        $fields[$p.Name] = [string]$p.Value
    }
    $script:SuitesAssetFieldsCache[$AssetName] = $fields
    return $fields
}

function Assert-ScenarioIdConfigured {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$AssetName,
        [Parameter(Mandatory = $true)][int]$ScenarioId
    )
    if ($ScenarioId -le 0) {
        throw "assets.$AssetName.test_scenario_id missing in .apifox/suites.yaml (or pass -ScenarioId)"
    }
}

function Get-AssetPaths {
    [CmdletBinding()]
    [OutputType([hashtable])]
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][string]$AssetName
    )
    $f = Get-SuitesAssetFields -RepoRoot $RepoRoot -AssetName $AssetName
    foreach ($req in @('generator', 'collection')) {
        if ([string]::IsNullOrWhiteSpace([string]$f[$req])) {
            throw "assets.$AssetName.$req is required in .apifox/suites.yaml"
        }
    }

    $collectionRel = [string]$f['collection']
    # 中间件默认落在 apifox-reports/<asset>/generated/（已 gitignore），不与正本/collection 混放。
    # suites.yaml 仍可显式覆盖 apifox_package / openapi_bridge。
    $artifactBase = $AssetName
    if ($collectionRel -match '([^/\\]+)\.postman_collection\.json$') {
        $artifactBase = $Matches[1]
    }
    $generatedRelDir = "apifox-reports/$AssetName/generated"

    $apifoxPkgRel = [string]$f['apifox_package']
    if ([string]::IsNullOrWhiteSpace($apifoxPkgRel)) {
        $apifoxPkgRel = "$generatedRelDir/$artifactBase.apifox-2.7.43-import.json"
    }

    $openApiRel = [string]$f['openapi_bridge']
    if ([string]::IsNullOrWhiteSpace($openApiRel)) {
        $openApiRel = "$generatedRelDir/$artifactBase.openapi.json"
    }

    $title = [string]$f['title']
    if ([string]::IsNullOrWhiteSpace($title)) { $title = $AssetName }
    $collectionName = [string]$f['collection_name']
    if ([string]::IsNullOrWhiteSpace($collectionName)) { $collectionName = $title }
    $scenarioName = [string]$f['scenario_name']
    if ([string]::IsNullOrWhiteSpace($scenarioName)) { $scenarioName = "$title · CLI sync" }

    $scenarioId = 0
    if (-not [string]::IsNullOrWhiteSpace([string]$f['test_scenario_id'])) {
        $scenarioId = [int]$f['test_scenario_id']
    }
    $environmentId = 0
    if (-not [string]::IsNullOrWhiteSpace([string]$f['environment_id'])) {
        $environmentId = [int]$f['environment_id']
    }

    $docPath = ''
    if (-not [string]::IsNullOrWhiteSpace([string]$f['doc'])) {
        $docPath = Resolve-RepoRelativePath -RepoRoot $RepoRoot -RelativePath ([string]$f['doc'])
    }

    $convertTags = [string]$f['convert_tags']
    if ([string]::IsNullOrWhiteSpace($convertTags)) {
        $convertTags = "cli-sync,repo-first,$AssetName"
    }

    return @{
        AssetKey         = $AssetName
        Name             = $title
        Generator        = Resolve-RepoRelativePath -RepoRoot $RepoRoot -RelativePath ([string]$f['generator'])
        Collection       = Resolve-RepoRelativePath -RepoRoot $RepoRoot -RelativePath $collectionRel
        OpenApi          = if ($openApiRel) { Resolve-RepoRelativePath -RepoRoot $RepoRoot -RelativePath $openApiRel } else { '' }
        ApifoxPackage    = Resolve-RepoRelativePath -RepoRoot $RepoRoot -RelativePath $apifoxPkgRel
        OpenApiConverter = Join-Path $RepoRoot "tools\apifox-cli\ConvertPostmanCollectionToOpenapi.py"
        ApifoxConverter  = Join-Path $RepoRoot "tools\apifox-cli\ConvertPostmanToApifoxScenario.py"
        TestsSyncer      = Join-Path $RepoRoot "tools\apifox-cli\SyncPostmanTestsViaCli.py"
        StepsPusher      = Join-Path $RepoRoot "tools\apifox-cli\PushApifoxScenarioSteps.py"
        FailureSummarizer = Join-Path $RepoRoot "tools\apifox-cli\SummarizeApifoxRunFailures.py"
        FailureTriage    = Join-Path $RepoRoot "tools\apifox-cli\TriageApifoxRunFailures.py"
        CatalogUpserter  = Join-Path $RepoRoot "tools\apifox-cli\UpsertApifoxCliCatalog.py"
        SuitesYamlHelper = Join-Path $RepoRoot "tools\apifox-cli\ApifoxSuitesYaml.py"
        GeneratorLinter  = Join-Path $RepoRoot "tools\apifox-cli\LintGeneratorAntiPatterns.py"
        SuitesLinter     = Join-Path $RepoRoot "tools\apifox-cli\LintSuitesYaml.py"
        CollectionValidator = Join-Path $RepoRoot "tools\apifox-cli\ValidatePostmanCollection.py"
        ReportDir        = Join-Path $RepoRoot (Join-Path "apifox-reports" $AssetName)
        Doc              = $docPath
        ModuleIdHint     = [string]$f['module_id']
        ModuleMapName    = $collectionName
        ScenarioName     = $scenarioName
        ConvertTags      = $convertTags
        TestScenarioId   = $scenarioId
        EnvironmentId    = $environmentId
        WorkingBranch    = [string]$f['working_branch']
        CliImportFormat  = [string]$f['cli_import_format']
    }
}

function Assert-ApifoxCli {
    [CmdletBinding()]
    param()
    $cmd = Get-Command apifox -ErrorAction SilentlyContinue
    if (-not $cmd) {
        throw "apifox CLI not found. Run: npm install -g apifox-cli@latest"
    }
}

function Get-ApifoxGlobalArgs {
    [CmdletBinding()]
    [OutputType([string[]])]
    param([Parameter(Mandatory = $true)][string]$ApiBaseUrl)
    if ([string]::IsNullOrWhiteSpace($env:APIFOX_ACCESS_TOKEN)) {
        throw "APIFOX_ACCESS_TOKEN is empty after loading .env"
    }
    $base = $ApiBaseUrl
    if (-not [string]::IsNullOrWhiteSpace($env:APIFOX_API_BASE_URL)) {
        $base = $env:APIFOX_API_BASE_URL.Trim()
    }
    return @(
        "--access-token", $env:APIFOX_ACCESS_TOKEN,
        "--api-base-url", $base
    )
}

function Invoke-ApifoxCli {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string[]]$CliArgs,
        [Parameter(Mandatory = $true)][string]$ApiBaseUrl
    )
    Assert-ApifoxCli
    $globalArgs = Get-ApifoxGlobalArgs -ApiBaseUrl $ApiBaseUrl
    # 打印时脱敏 token
    $safe = @()
    $skipNext = $false
    foreach ($a in ($globalArgs + $CliArgs)) {
        if ($skipNext) { $skipNext = $false; $safe += "***"; continue }
        if ($a -eq "--access-token") { $safe += $a; $skipNext = $true; continue }
        $safe += $a
    }
    Write-Host ("apifox " + ($safe -join " ")) -ForegroundColor DarkGray
    & apifox @globalArgs @CliArgs
    if ($LASTEXITCODE -ne 0) {
        throw "apifox exited with code $LASTEXITCODE"
    }
}

function Ensure-ApifoxAuth {
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)][string]$ApiBaseUrl)
    if ([string]::IsNullOrWhiteSpace($env:APIFOX_ACCESS_TOKEN)) {
        throw "APIFOX_ACCESS_TOKEN is empty after loading .env"
    }
    $base = $ApiBaseUrl
    if (-not [string]::IsNullOrWhiteSpace($env:APIFOX_API_BASE_URL)) {
        $base = $env:APIFOX_API_BASE_URL.Trim()
    }
    # 私有化必须带 --api-base-url，否则令牌会打到公有云而报「无效」
    Write-Host "Logging in against $base ..." -ForegroundColor Cyan
    & apifox auth login --api-base-url $base --with-token $env:APIFOX_ACCESS_TOKEN
    if ($LASTEXITCODE -ne 0) {
        throw "apifox auth login failed (exit $LASTEXITCODE). Check token is from $base account settings."
    }
}

function Invoke-OfflineGenerateGates {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][hashtable]$Paths,
        [Parameter(Mandatory = $true)][string]$RepoRoot
    )
    foreach ($tool in @($Paths.GeneratorLinter, $Paths.SuitesLinter, $Paths.CollectionValidator)) {
        if (-not (Test-Path -LiteralPath $tool)) {
            throw "Offline gate tool not found: $tool"
        }
    }

    Write-Host "Running offline generator anti-pattern lint ..." -ForegroundColor Cyan
    & python -X utf8 $Paths.GeneratorLinter
    if ($LASTEXITCODE -ne 0) {
        throw "Generator anti-pattern lint failed with exit code $LASTEXITCODE"
    }

    Write-Host "Running offline suites.yaml lint ..." -ForegroundColor Cyan
    & python -X utf8 $Paths.SuitesLinter --repo-root $RepoRoot
    if ($LASTEXITCODE -ne 0) {
        throw "suites.yaml lint failed with exit code $LASTEXITCODE"
    }
}

function Invoke-ValidateGeneratedCollection {
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)][hashtable]$Paths)
    Write-Host "Validating generated Postman Collection offline ..." -ForegroundColor Cyan
    & python -X utf8 $Paths.CollectionValidator --input $Paths.Collection
    if ($LASTEXITCODE -ne 0) {
        throw "Postman Collection validation failed with exit code $LASTEXITCODE"
    }
}

function Invoke-GenerateCollection {
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)][hashtable]$Paths)
    if (-not (Test-Path -LiteralPath $Paths.Generator)) {
        throw "Generator not found: $($Paths.Generator)"
    }
    Invoke-OfflineGenerateGates -Paths $Paths -RepoRoot (Get-RepoRoot)
    Write-Host "Generating $($Paths.Name) ..." -ForegroundColor Cyan
    python $Paths.Generator
    if ($LASTEXITCODE -ne 0) {
        throw "Generator failed with exit code $LASTEXITCODE"
    }
    if (-not (Test-Path -LiteralPath $Paths.Collection)) {
        throw "Collection not written: $($Paths.Collection)"
    }
    Invoke-ValidateGeneratedCollection -Paths $Paths
    $len = (Get-Item -LiteralPath $Paths.Collection).Length
    Write-Host "OK: $($Paths.Collection) ($len bytes)" -ForegroundColor Green
}

function Invoke-BuildOpenApiBridge {
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)][hashtable]$Paths)
    if (-not (Test-Path -LiteralPath $Paths.Collection)) {
        throw "Collection missing; run -Action Generate first: $($Paths.Collection)"
    }
    Write-Host "Converting Postman → OpenAPI (interface shell only) ..." -ForegroundColor Cyan
    python $Paths.OpenApiConverter --input $Paths.Collection --output $Paths.OpenApi
    if ($LASTEXITCODE -ne 0) {
        throw "OpenAPI convert failed with exit code $LASTEXITCODE"
    }
}

function Invoke-BuildApifoxScenarioPackage {
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)][hashtable]$Paths)
    if (-not (Test-Path -LiteralPath $Paths.Collection)) {
        throw "Collection missing; run -Action Generate first: $($Paths.Collection)"
    }
    Write-Host "Converting Postman → Apifox scenario package (with Tests) ..." -ForegroundColor Cyan
    $tags = if ($Paths.ConvertTags) { [string]$Paths.ConvertTags } else { "cli-sync,repo-first,$($Paths.AssetKey)" }
    python $Paths.ApifoxConverter `
        --input $Paths.Collection `
        --output $Paths.ApifoxPackage `
        --collection-name $Paths.ModuleMapName `
        --scenario-name $Paths.ScenarioName `
        --tags $tags
    if ($LASTEXITCODE -ne 0) {
        throw "Apifox package convert failed with exit code $LASTEXITCODE"
    }
}

function Invoke-ImportCollection {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][hashtable]$Paths,
        [Parameter(Mandatory = $true)][int]$TargetProjectId,
        [Parameter(Mandatory = $true)][string]$ApiBaseUrl,
        [Parameter(Mandatory = $true)][string]$Format,
        [string]$BranchName
    )
    if (-not (Test-Path -LiteralPath $Paths.Collection)) {
        throw "Collection missing; run -Action Generate first: $($Paths.Collection)"
    }

    $fileToImport = $Paths.Collection
    $format = $Format
    if ($format -eq "openapi") {
        Invoke-BuildOpenApiBridge -Paths $Paths
        $fileToImport = $Paths.OpenApi
    }
    elseif ($format -eq "apifox") {
        Invoke-BuildApifoxScenarioPackage -Paths $Paths
        $fileToImport = $Paths.ApifoxPackage
    }

    $importArgs = @(
        "import",
        "--project", "$TargetProjectId",
        "--format", $format,
        "--file", $fileToImport
    )
    if ($format -eq "apifox" -and $Paths.ModuleIdHint) {
        $importArgs += @(
            "--module-map",
            ("{0}={1}" -f $Paths.ModuleMapName, $Paths.ModuleIdHint)
        )
    }
    if (-not [string]::IsNullOrWhiteSpace($BranchName)) {
        $importArgs += @("--branch", $BranchName)
    }
    Write-Host "Importing ($format) into Apifox project $TargetProjectId ..." -ForegroundColor Cyan
    if ($format -eq "postman") {
        Write-Host "NOTE: private deploy may reject postman; prefer -ImportFormat apifox." -ForegroundColor Yellow
    }
    try {
        Invoke-ApifoxCli -CliArgs $importArgs -ApiBaseUrl $ApiBaseUrl
    }
    catch {
        if ($format -eq "apifox") {
            Write-Host "Apifox-format import failed; falling back to openapi shell + SyncTests path." -ForegroundColor Yellow
            Write-Host $_ -ForegroundColor DarkYellow
            Invoke-ImportCollection -Paths $Paths -TargetProjectId $TargetProjectId -ApiBaseUrl $ApiBaseUrl -Format "openapi" -BranchName $BranchName
            return
        }
        throw
    }
    Write-Host "Import finished. Project=$TargetProjectId format=$format file=$fileToImport" -ForegroundColor Green
    if ($format -eq "apifox") {
        Write-Host "Check 自动化测试 for scenario: $($Paths.ScenarioName) (steps include postProcessors/customScript)." -ForegroundColor Green
    }
}

function Invoke-SyncTestsToEndpoints {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][hashtable]$Paths,
        [Parameter(Mandatory = $true)][int]$TargetProjectId,
        [Parameter(Mandatory = $true)][string]$ApiBaseUrl,
        [switch]$DryRunFlag
    )
    Write-Host "Syncing Postman Tests → endpoint postProcessors via CLI ..." -ForegroundColor Cyan
    $pyArgs = @(
        $Paths.TestsSyncer,
        "--project", "$TargetProjectId",
        "--api-base-url", $ApiBaseUrl,
        "--collection", $Paths.Collection
    )
    if ($DryRunFlag) { $pyArgs += "--dry-run" }
    python @pyArgs
    if ($LASTEXITCODE -ne 0) {
        throw "SyncPostmanTestsViaCli failed with exit code $LASTEXITCODE"
    }
}

function Get-ConfiguredWorkingBranch {
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][string]$AssetName,
        [string]$Override = ""
    )
    if (-not [string]::IsNullOrWhiteSpace($Override)) {
        return $Override.Trim()
    }
    $fields = Get-SuitesAssetFields -RepoRoot $RepoRoot -AssetName $AssetName
    $wb = [string]$fields['working_branch']
    if (-not [string]::IsNullOrWhiteSpace($wb) -and $wb -ne "null") {
        return $wb.Trim()
    }
    throw "assets.$AssetName.working_branch missing in .apifox/suites.yaml (do not rely on silent fallback)"
}

function Invoke-EnsureAiBranch {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][int]$TargetProjectId,
        [Parameter(Mandatory = $true)][string]$ApiBaseUrl,
        [Parameter(Mandatory = $true)][string]$BranchName,
        [switch]$AllowCreate
    )
    Write-Host "Using shared AI branch $BranchName (reuse only; do not create dated branches) ..." -ForegroundColor Cyan
    try {
        Invoke-ApifoxCli -CliArgs @(
            "branch", "get", $BranchName,
            "--project", "$TargetProjectId",
            "--type", "ai"
        ) -ApiBaseUrl $ApiBaseUrl
    }
    catch {
        if (-not $AllowCreate) {
            throw @"
AI branch '$BranchName' not found. Reuse the shared working_branch in .apifox/suites.yaml.
Do not create a new ai/* branch for each script change. If this is first-time bootstrap, re-run with -AllowCreateAiBranch.
"@
        }
        Write-Host "AllowCreateAiBranch: creating $BranchName once from main ..." -ForegroundColor Yellow
        Invoke-ApifoxCli -CliArgs @(
            "branch", "create",
            "--project", "$TargetProjectId",
            "--type", "ai",
            "--name", $BranchName,
            "--from", "main"
        ) -ApiBaseUrl $ApiBaseUrl
    }
}

function Invoke-PushScenarioSteps {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][hashtable]$Paths,
        [Parameter(Mandatory = $true)][int]$TargetProjectId,
        [Parameter(Mandatory = $true)][string]$ApiBaseUrl,
        [Parameter(Mandatory = $true)][string]$BranchName,
        [Parameter(Mandatory = $true)][int]$TargetScenarioId,
        [switch]$DryRunFlag
    )
    # 始终从最新 collection 重建包，避免沿用旧步骤名
    Invoke-BuildApifoxScenarioPackage -Paths $Paths
    Write-Host "Pushing steps+Tests into scenario $TargetScenarioId on $BranchName ..." -ForegroundColor Cyan
    $pyArgs = @(
        $Paths.StepsPusher,
        "--project", "$TargetProjectId",
        "--scenario-id", "$TargetScenarioId",
        "--api-base-url", $ApiBaseUrl,
        "--package", $Paths.ApifoxPackage,
        "--branch", $BranchName,
        "--scenario-name", $Paths.ScenarioName
    )
    $fields = Get-SuitesAssetFields -RepoRoot (Get-RepoRoot) -AssetName $Paths.AssetKey
    if (-not [string]::IsNullOrWhiteSpace([string]$fields['use_data_set_id'])) {
        $ds = 0
        [void][int]::TryParse([string]$fields['use_data_set_id'], [ref]$ds)
        if ($ds -gt 0) { $pyArgs += @("--use-data-set-id", "$ds") }
    }
    if (-not [string]::IsNullOrWhiteSpace([string]$fields['environment_id'])) {
        $eid = 0
        [void][int]::TryParse([string]$fields['environment_id'], [ref]$eid)
        if ($eid -gt 0) { $pyArgs += @("--environment-id", "$eid") }
    }
    if ($DryRunFlag) { $pyArgs += "--dry-run" }
    # 2026-08-24：yaml 漏写时默认绑真实接口再按 UI 解绑，否则 Headers 参数值列空，
    # UI 改 Body 会发出空鉴权头（201.000.001 invalid secret）。显式 customHttp 才关闭。
    $pushMode = [string]$fields['push_mode']
    $unbindRaw = [string]$fields['unbind_after_push']
    if ([string]::IsNullOrWhiteSpace($pushMode)) {
        $pushMode = "http"
        Write-Host "suites.yaml 未写 push_mode，默认 http（见 apifox-cli-repo-first reference「场景 Headers 参数值为空」）" -ForegroundColor Yellow
    }
    $pyArgs += @("--mode", $pushMode)
    $unbindOn = $false
    if ($unbindRaw -in @('true', '1', 'yes')) {
        $unbindOn = $true
    }
    elseif ($unbindRaw -in @('false', '0', 'no')) {
        $unbindOn = $false
    }
    elseif ([string]::IsNullOrWhiteSpace($unbindRaw) -and ($pushMode -eq 'http')) {
        $unbindOn = $true
        Write-Host "suites.yaml 未写 unbind_after_push，http 模式默认解绑" -ForegroundColor Yellow
    }
    if ($unbindOn) { $pyArgs += "--unbind-after" }
    python @pyArgs
    if ($LASTEXITCODE -ne 0) {
        throw "PushApifoxScenarioSteps failed with exit code $LASTEXITCODE"
    }
}

function Invoke-ShowStatus {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][int]$TargetProjectId,
        [Parameter(Mandatory = $true)][string]$ApiBaseUrl,
        [Parameter(Mandatory = $true)][hashtable]$Paths
    )
    Write-Host "=== Repo asset ===" -ForegroundColor Cyan
    Write-Host "AssetKey: $($Paths.AssetKey)"
    Write-Host "Name: $($Paths.Name)"
    Write-Host "ScenarioName: $($Paths.ScenarioName)"
    Write-Host "Generator: $($Paths.Generator)"
    Write-Host "Collection: $($Paths.Collection) exists=$(Test-Path -LiteralPath $Paths.Collection)"
    Write-Host "ApifoxPackage (ephemeral): $($Paths.ApifoxPackage)"
    Write-Host "OpenApi (ephemeral): $($Paths.OpenApi)"
    Write-Host "ReportDir: $($Paths.ReportDir)"
    if ($Paths.Doc) { Write-Host "Doc: $($Paths.Doc)" }
    Write-Host "=== Apifox ===" -ForegroundColor Cyan
    Write-Host "ProjectId: $TargetProjectId ApiBaseUrl: $ApiBaseUrl"
    Invoke-ApifoxCli -CliArgs @("project", "get", "$TargetProjectId") -ApiBaseUrl $ApiBaseUrl
    Write-Host "--- endpoint list (top) ---" -ForegroundColor DarkGray
    Invoke-ApifoxCli -CliArgs @("endpoint", "list", "--project", "$TargetProjectId") -ApiBaseUrl $ApiBaseUrl
}

function Get-SuiteRunContext {
    [CmdletBinding()]
    [OutputType([hashtable])]
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][string]$AssetName,
        [Parameter(Mandatory = $true)][int]$TargetProjectId,
        [int]$OverrideEnvId = 0,
        [int]$OverrideScenarioId = 0,
        [string]$OverrideBranch = ""
    )
    $fields = Get-SuitesAssetFields -RepoRoot $RepoRoot -AssetName $AssetName
    $configuredScenario = 0
    if (-not [string]::IsNullOrWhiteSpace([string]$fields['test_scenario_id'])) {
        $configuredScenario = [int]$fields['test_scenario_id']
    }
    if ($OverrideScenarioId -le 0 -and $configuredScenario -le 0) {
        throw @"
.apifox/suites.yaml 尚未填写 assets.$AssetName.test_scenario_id。
请在 Apifox 项目 $TargetProjectId 中把导入集合整理为「场景用例」，
在 CI/CD 面板复制场景 ID，写入 suites.yaml 后再 -Action Run。
"@
    }
    $scenarioId = if ($OverrideScenarioId -gt 0) { $OverrideScenarioId } else { $configuredScenario }
    $envId = 0
    if ($OverrideEnvId -gt 0) {
        $envId = $OverrideEnvId
    }
    elseif (-not [string]::IsNullOrWhiteSpace([string]$fields['environment_id'])) {
        $envId = [int]$fields['environment_id']
    }
    $branch = $OverrideBranch
    if ([string]::IsNullOrWhiteSpace($branch)) {
        $wb = [string]$fields['working_branch']
        if ($wb -and $wb -ne "null") { $branch = $wb }
    }
    return @{
        ScenarioId = $scenarioId
        EnvironmentId = $envId
        Branch = $branch
        ReportDir = Join-Path $RepoRoot (Join-Path "apifox-reports" $AssetName)
    }
}

function Clear-StaleApifoxRunReports {
    <#
      每次 Run 后只保留本资产「当前 stamp」的报告文件，删掉同目录下更早的
      <asset>-yyyyMMdd-HHmmss(.html|.json|.xml|-failures.json) 等，避免 apifox-reports 膨胀。
      不碰 generated/、last-failures.md、leftover-failures.md 及其它非本前缀文件。
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$ReportDir,
        [Parameter(Mandatory = $true)][string]$SafeAsset,
        [Parameter(Mandatory = $true)][string]$KeepPrefix
    )
    if ([string]::IsNullOrWhiteSpace($ReportDir) -or -not (Test-Path -LiteralPath $ReportDir)) {
        return
    }
    if ([string]::IsNullOrWhiteSpace($KeepPrefix)) {
        return
    }
    $pattern = '^' + [regex]::Escape($SafeAsset) + '-\d{8}-\d{6}'
    $removed = 0
    Get-ChildItem -LiteralPath $ReportDir -File -ErrorAction SilentlyContinue | ForEach-Object {
        $name = $_.Name
        $full = $_.FullName
        if ($name -notmatch $pattern) { return }
        if ($name.StartsWith($KeepPrefix, [System.StringComparison]::OrdinalIgnoreCase)) { return }
        try {
            Remove-Item -LiteralPath $full -Force -ErrorAction Stop
            $removed++
        }
        catch {
            Write-Host "Warn: could not prune ${full}: $_" -ForegroundColor DarkYellow
        }
    }
    if ($removed -gt 0) {
        Write-Host "Pruned $removed older run report(s) under $ReportDir (kept $KeepPrefix*)." -ForegroundColor DarkGray
    }
}

function Invoke-SummarizeRunFailures {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][hashtable]$Paths,
        [Parameter(Mandatory = $true)][string]$ReportDir,
        [string]$ReportPrefix = "",
        [switch]$FailOnError
    )
    if (-not (Test-Path -LiteralPath $Paths.FailureSummarizer)) {
        throw "Missing $($Paths.FailureSummarizer)"
    }
    $pyArgs = @(
        $Paths.FailureSummarizer,
        "--report-dir", $ReportDir,
        "--write-md", (Join-Path $ReportDir "last-failures.md")
    )
    if (-not [string]::IsNullOrWhiteSpace($ReportPrefix)) {
        $pyArgs += @("--prefix", $ReportPrefix)
    }
    if ($FailOnError) { $pyArgs += "--fail-on-error" }
    Write-Host "Summarizing failures from $ReportDir ..." -ForegroundColor Cyan
    # python stdout 必须进 Host，否则会混进函数返回值，导致 ``$code -ne 0`` 把全绿当失败
    & python @pyArgs | ForEach-Object { Write-Host $_ }
    $code = $LASTEXITCODE
    if ($null -eq $code) { $code = 0 }
    $md = Join-Path $ReportDir "last-failures.md"
    if (Test-Path -LiteralPath $md) {
        $text = Get-Content -LiteralPath $md -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
        # 汇总已写「失败: 0」且无失败章节：以报告为准，勿被 shim/残留 exit 抬成失败
        if ($text -and ($text -match '失败:\s*0') -and ($text -notlike '*## 失败步骤*')) {
            return 0
        }
    }
    return [int]$code
}

function Invoke-RunMappedSuite {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][int]$TargetProjectId,
        [Parameter(Mandatory = $true)][string]$ApiBaseUrl,
        [Parameter(Mandatory = $true)][hashtable]$Paths,
        [Parameter(Mandatory = $true)][string]$AssetName,
        [int]$OverrideEnvId = 0,
        [int]$OverrideScenarioId = 0,
        [string]$OverrideBranch = "",
        [switch]$SummarizeOnly,
        [switch]$FailOnFailures,
        [switch]$FullReports
    )
    $ctx = Get-SuiteRunContext -RepoRoot $RepoRoot -AssetName $AssetName -TargetProjectId $TargetProjectId `
        -OverrideEnvId $OverrideEnvId -OverrideScenarioId $OverrideScenarioId -OverrideBranch $OverrideBranch
    if (-not $SummarizeOnly) {
        if ($ctx.EnvironmentId -le 0) {
            throw "suites.yaml assets.$AssetName.environment_id missing (or pass -EnvironmentId)."
        }
        if (-not (Test-Path -LiteralPath $ctx.ReportDir)) {
            New-Item -ItemType Directory -Path $ctx.ReportDir | Out-Null
        }
        $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
        # 日常 cli+json 足够 Summarize/Triage；html/junit 体积大，需看图时用 -FullReports
        $reporters = if ($FullReports) { 'cli,html,json,junit' } else { 'cli,json' }
        $safeAsset = ($AssetName -replace '[^\w\-]', '_')
        $outFile = "$safeAsset-$stamp"
        $failFile = "$safeAsset-$stamp-failures"
        $script:LastApifoxReportPrefix = $outFile
        Write-Host "Reporters=$reporters out=$outFile" -ForegroundColor DarkGray
        $runArgs = @(
            'run',
            '-t', "$($ctx.ScenarioId)",
            '--project', "$TargetProjectId",
            '-e', "$($ctx.EnvironmentId)",
            '-r', $reporters,
            '--out-dir', $ctx.ReportDir,
            '--out-file', $outFile,
            '--out-json-failures-separated', $failFile,
            # ignore: keep running remaining steps after assertion failures
            '--on-error', 'ignore'
        )
        if (-not [string]::IsNullOrWhiteSpace($ctx.Branch)) {
            $runArgs += @('--branch', $ctx.Branch)
        }
        Write-Host "Running scenario $($ctx.ScenarioId) env=$($ctx.EnvironmentId) branch=$($ctx.Branch) ..." -ForegroundColor Cyan
        try {
            Invoke-ApifoxCli -CliArgs $runArgs -ApiBaseUrl $ApiBaseUrl
        }
        catch {
            # apifox run often exits non-zero when cases fail; still parse reports
            Write-Host 'apifox run exited with errors; will parse report anyway.' -ForegroundColor Yellow
            Write-Host $_ -ForegroundColor DarkYellow
        }
        # 新报告已落盘后再剪旧 stamp，保证 Summarize/Triage 仍能读到本次前缀
        Clear-StaleApifoxRunReports -ReportDir $ctx.ReportDir -SafeAsset $safeAsset -KeepPrefix $outFile
    }
    $prefix = ''
    if (Get-Variable -Name LastApifoxReportPrefix -Scope Script -ErrorAction SilentlyContinue) {
        $prefix = [string]$script:LastApifoxReportPrefix
    }
    $code = Invoke-SummarizeRunFailures -Paths $Paths -ReportDir $ctx.ReportDir -ReportPrefix $prefix -FailOnError:$FailOnFailures
    if ($FailOnFailures -and $code -ne 0) {
        throw "Scenario run has failures. See $($ctx.ReportDir)\last-failures.md"
    }
    if ($code -eq 0) {
        Write-Host 'Run check OK: no failures to show (code issues auto-fixed or all passed).' -ForegroundColor Green
    }
    return @{
        ExitCode = $code
        ReportDir = $ctx.ReportDir
        ReportPrefix = $prefix
        ScenarioId = $ctx.ScenarioId
    }
}

function Invoke-UpsertCliCatalog {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][hashtable]$Paths,
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][string]$AssetName
    )
    if (-not (Test-Path -LiteralPath $Paths.CatalogUpserter)) {
        Write-Host "Catalog upserter missing: $($Paths.CatalogUpserter)" -ForegroundColor Yellow
        return
    }
    Write-Host "Upserting Apifox CLI skill catalog for asset=$AssetName ..." -ForegroundColor Cyan
    python $Paths.CatalogUpserter --asset $AssetName --repo-root $RepoRoot
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Catalog upsert failed (exit $LASTEXITCODE); SyncCheck itself succeeded." -ForegroundColor Yellow
    }
}

function Invoke-TriageAndRerunLoop {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][int]$TargetProjectId,
        [Parameter(Mandatory = $true)][string]$ApiBaseUrl,
        [Parameter(Mandatory = $true)][hashtable]$Paths,
        [Parameter(Mandatory = $true)][string]$WorkingBranchName,
        [Parameter(Mandatory = $true)][int]$TargetScenarioId,
        [Parameter(Mandatory = $true)][string]$AssetName,
        [int]$OverrideEnvId = 0,
        [switch]$FullReports
    )
    # 首次：推送后跑，失败不直接抛（留给通用 triage；规则在 suites.yaml）
    Invoke-PushScenarioSteps -Paths $Paths -TargetProjectId $TargetProjectId -ApiBaseUrl $ApiBaseUrl -BranchName $WorkingBranchName -TargetScenarioId $TargetScenarioId
    $null = Invoke-RunMappedSuite -RepoRoot $RepoRoot -TargetProjectId $TargetProjectId -ApiBaseUrl $ApiBaseUrl -Paths $Paths `
        -AssetName $AssetName -OverrideEnvId $OverrideEnvId -OverrideScenarioId $TargetScenarioId -OverrideBranch $WorkingBranchName `
        -FullReports:$FullReports

    $prefix = ''
    if (Get-Variable -Name LastApifoxReportPrefix -Scope Script -ErrorAction SilentlyContinue) {
        $prefix = [string]$script:LastApifoxReportPrefix
    }
    $reportDir = [string]$Paths.ReportDir
    if (-not (Test-Path -LiteralPath $reportDir)) {
        New-Item -ItemType Directory -Path $reportDir | Out-Null
    }
    $triageArgs = @(
        $Paths.FailureTriage,
        '--report-dir', $reportDir,
        '--prefix', $prefix,
        '--asset', $AssetName,
        '--repo-root', $RepoRoot
    )
    Write-Host 'Triaging failures (script patterns vs leftover; see suites.yaml triage)...' -ForegroundColor Cyan
    python @triageArgs
    $triageCode = $LASTEXITCODE

    if ($triageCode -eq 0) {
        Write-Host 'Triage OK: no leftover failures.' -ForegroundColor Green
        Invoke-UpsertCliCatalog -Paths $Paths -RepoRoot $RepoRoot -AssetName $AssetName
        return
    }
    if ($triageCode -eq 10) {
        # 仅匹配 script_name_patterns：再 Generate+Push+Run 一轮（不改生成器文件）
        Write-Host 'Script-like failures: regenerate + push + re-run once (no generator patch)...' -ForegroundColor Yellow
        Invoke-GenerateCollection -Paths $Paths
        Invoke-PushScenarioSteps -Paths $Paths -TargetProjectId $TargetProjectId -ApiBaseUrl $ApiBaseUrl -BranchName $WorkingBranchName -TargetScenarioId $TargetScenarioId
        $null = Invoke-RunMappedSuite -RepoRoot $RepoRoot -TargetProjectId $TargetProjectId -ApiBaseUrl $ApiBaseUrl -Paths $Paths `
            -AssetName $AssetName -OverrideEnvId $OverrideEnvId -OverrideScenarioId $TargetScenarioId -OverrideBranch $WorkingBranchName `
            -FullReports:$FullReports
        $prefix2 = ''
        if (Get-Variable -Name LastApifoxReportPrefix -Scope Script -ErrorAction SilentlyContinue) {
            $prefix2 = [string]$script:LastApifoxReportPrefix
        }
        python @(
            $Paths.FailureTriage,
            '--report-dir', $reportDir,
            '--prefix', $prefix2,
            '--asset', $AssetName,
            '--repo-root', $RepoRoot
        )
        $triageCode2 = $LASTEXITCODE
        if ($triageCode2 -eq 0) {
            Write-Host 'Re-run OK: script-like failures cleared after regenerate+push.' -ForegroundColor Green
            Invoke-UpsertCliCatalog -Paths $Paths -RepoRoot $RepoRoot -AssetName $AssetName
            return
        }
        if ($triageCode2 -eq 1) {
            throw "Leftover (non-script) failures remain. See $reportDir\leftover-failures.md"
        }
        if ($triageCode2 -eq 10) {
            throw "Script-like failures remain after one re-run cycle. Fix generator in-repo; see $reportDir\last-failures.md"
        }
        throw "Triage failed with exit $triageCode2"
    }
    if ($triageCode -eq 1) {
        throw "Leftover (non-script) failures. See $reportDir\leftover-failures.md"
    }
    throw "Triage failed with exit $triageCode"
}

# ---- main ----
$RepoRoot = Get-RepoRoot
if ($Action -eq "Run" -or $Action -eq "SyncCheck" -or $CheckRun) {
    Assert-RunExplicitlyConfirmed -SelectedAction $Action -IsConfirmed ([bool]$ConfirmRun)
}
if ($Action -ne "Generate") {
    Import-DotEnvFile -EnvFile (Join-Path $RepoRoot ".env")
}
$settings = Get-ApifoxSettings -RepoRoot $RepoRoot
$targetProjectId = if ($ProjectId -gt 0) { $ProjectId } else { $settings.ProjectId }
$knownAssets = Get-SuitesAssetKeys -RepoRoot $RepoRoot
if ($knownAssets -notcontains $Asset) {
    throw "Unknown -Asset '$Asset'. Known assets in .apifox/suites.yaml: $($knownAssets -join ', ')"
}
$paths = Get-AssetPaths -RepoRoot $RepoRoot -AssetName $Asset
if ($ScenarioId -le 0) { $ScenarioId = [int]$paths.TestScenarioId }
if ($EnvironmentId -le 0 -and $paths.EnvironmentId -gt 0) { $EnvironmentId = [int]$paths.EnvironmentId }
# suites.yaml cli_import_format 优先；命令行 -ImportFormat 作回退
$effectiveImportFormat = $ImportFormat
if (-not [string]::IsNullOrWhiteSpace([string]$paths.CliImportFormat)) {
    $effectiveImportFormat = [string]$paths.CliImportFormat
}

$apiBaseUrl = $settings.ApiBaseUrl
$WorkingBranch = Get-ConfiguredWorkingBranch -RepoRoot $RepoRoot -AssetName $Asset -Override $WorkingBranch
Write-Host "RepoRoot=$RepoRoot ProjectId=$targetProjectId ApiBaseUrl=$apiBaseUrl Asset=$Asset Action=$Action Branch=$WorkingBranch ScenarioId=$ScenarioId ImportFormat=$effectiveImportFormat" -ForegroundColor Yellow

switch ($Action) {
    "Generate" {
        Invoke-GenerateCollection -Paths $paths
    }
    "WhoAmI" {
        Assert-ApifoxCli
        Ensure-ApifoxAuth -ApiBaseUrl $apiBaseUrl
        Invoke-ApifoxCli -CliArgs @("auth", "whoami") -ApiBaseUrl $apiBaseUrl
    }
    "Import" {
        Assert-ApifoxCli
        Ensure-ApifoxAuth -ApiBaseUrl $apiBaseUrl
        if (-not $SkipGenerate) {
            Invoke-GenerateCollection -Paths $paths
        }
        Invoke-ImportCollection -Paths $paths -TargetProjectId $targetProjectId -ApiBaseUrl $apiBaseUrl -Format $effectiveImportFormat -BranchName $Branch
    }
    "Sync" {
        Assert-ApifoxCli
        Ensure-ApifoxAuth -ApiBaseUrl $apiBaseUrl
        Assert-ScenarioIdConfigured -AssetName $Asset -ScenarioId $ScenarioId
        Invoke-GenerateCollection -Paths $paths
        Invoke-ImportCollection -Paths $paths -TargetProjectId $targetProjectId -ApiBaseUrl $apiBaseUrl -Format $effectiveImportFormat -BranchName $Branch
        Invoke-EnsureAiBranch -TargetProjectId $targetProjectId -ApiBaseUrl $apiBaseUrl -BranchName $WorkingBranch -AllowCreate:$AllowCreateAiBranch
        Invoke-PushScenarioSteps -Paths $paths -TargetProjectId $targetProjectId -ApiBaseUrl $apiBaseUrl -BranchName $WorkingBranch -TargetScenarioId $ScenarioId
        Write-Host "Full CLI sync done. Remote step names verified as purpose-first Chinese." -ForegroundColor Green
        if ($CheckRun) {
            Invoke-RunMappedSuite -RepoRoot $RepoRoot -TargetProjectId $targetProjectId -ApiBaseUrl $apiBaseUrl -Paths $paths `
                -AssetName $Asset -OverrideEnvId $EnvironmentId -OverrideScenarioId $ScenarioId -OverrideBranch $WorkingBranch `
                -FailOnFailures -FullReports:$FullReports
        }
        else {
            Write-Host "Tip: add -CheckRun to auto-run UAT and list failed steps." -ForegroundColor Yellow
        }
    }
    "SyncCheck" {
        Assert-ApifoxCli
        Ensure-ApifoxAuth -ApiBaseUrl $apiBaseUrl
        Assert-ScenarioIdConfigured -AssetName $Asset -ScenarioId $ScenarioId
        Invoke-GenerateCollection -Paths $paths
        Invoke-EnsureAiBranch -TargetProjectId $targetProjectId -ApiBaseUrl $apiBaseUrl -BranchName $WorkingBranch -AllowCreate:$AllowCreateAiBranch
        # 生成 → 推送 → 跑 → triage → SCRIPT 再重跑一轮 → leftover
        Invoke-TriageAndRerunLoop -RepoRoot $RepoRoot -TargetProjectId $targetProjectId -ApiBaseUrl $apiBaseUrl -Paths $paths `
            -WorkingBranchName $WorkingBranch -TargetScenarioId $ScenarioId -AssetName $Asset -OverrideEnvId $EnvironmentId `
            -FullReports:$FullReports
    }
    "Status" {
        Assert-ApifoxCli
        Ensure-ApifoxAuth -ApiBaseUrl $apiBaseUrl
        Invoke-ShowStatus -TargetProjectId $targetProjectId -ApiBaseUrl $apiBaseUrl -Paths $paths
    }
    "Run" {
        Assert-ApifoxCli
        Ensure-ApifoxAuth -ApiBaseUrl $apiBaseUrl
        Assert-ScenarioIdConfigured -AssetName $Asset -ScenarioId $ScenarioId
        Invoke-RunMappedSuite -RepoRoot $RepoRoot -TargetProjectId $targetProjectId -ApiBaseUrl $apiBaseUrl -Paths $paths `
            -AssetName $Asset -OverrideEnvId $EnvironmentId -OverrideScenarioId $ScenarioId -OverrideBranch $WorkingBranch `
            -FailOnFailures -FullReports:$FullReports
    }
    "SyncTests" {
        Assert-ApifoxCli
        Ensure-ApifoxAuth -ApiBaseUrl $apiBaseUrl
        if (-not $SkipGenerate) {
            Invoke-GenerateCollection -Paths $paths
        }
        Invoke-SyncTestsToEndpoints -Paths $paths -TargetProjectId $targetProjectId -ApiBaseUrl $apiBaseUrl -DryRunFlag:$DryRun
    }
    "PushSteps" {
        Assert-ApifoxCli
        Ensure-ApifoxAuth -ApiBaseUrl $apiBaseUrl
        Assert-ScenarioIdConfigured -AssetName $Asset -ScenarioId $ScenarioId
        if (-not $SkipGenerate) {
            Invoke-GenerateCollection -Paths $paths
            Invoke-BuildApifoxScenarioPackage -Paths $paths
        }
        Invoke-EnsureAiBranch -TargetProjectId $targetProjectId -ApiBaseUrl $apiBaseUrl -BranchName $WorkingBranch -AllowCreate:$AllowCreateAiBranch
        Invoke-PushScenarioSteps -Paths $paths -TargetProjectId $targetProjectId -ApiBaseUrl $apiBaseUrl -BranchName $WorkingBranch -TargetScenarioId $ScenarioId -DryRunFlag:$DryRun
        if ($CheckRun -and -not $DryRun) {
            Invoke-RunMappedSuite -RepoRoot $RepoRoot -TargetProjectId $targetProjectId -ApiBaseUrl $apiBaseUrl -Paths $paths `
                -AssetName $Asset -OverrideEnvId $EnvironmentId -OverrideScenarioId $ScenarioId -OverrideBranch $WorkingBranch `
                -FailOnFailures -FullReports:$FullReports
        }
        elseif (-not $CheckRun) {
            Write-Host "Tip: add -CheckRun to auto-run UAT and list failed steps after push." -ForegroundColor Yellow
        }
    }
}
