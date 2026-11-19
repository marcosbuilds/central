[CmdletBinding()]
param(
    [string]$OutputRoot = '',
    [string]$Commit = '',
    [string]$DeployDate = ''
)

$ErrorActionPreference = 'Stop'

function Get-RelativePath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$BasePath,
        [Parameter(Mandatory = $true)]
        [string]$TargetPath
    )

    # System.IO.Path.GetRelativePath is unavailable in Windows PowerShell 5.1.
    # URI resolution keeps this script usable on the provider workstation as
    # well as in PowerShell 7 without changing the package layout.
    $base = [IO.Path]::GetFullPath($BasePath).TrimEnd('\', '/') + [IO.Path]::DirectorySeparatorChar
    $target = [IO.Path]::GetFullPath($TargetPath)
    $baseUri = New-Object System.Uri($base)
    $targetUri = New-Object System.Uri($target)
    $relativeUri = $baseUri.MakeRelativeUri($targetUri)
    return [Uri]::UnescapeDataString($relativeUri.ToString()).Replace('/', [IO.Path]::DirectorySeparatorChar)
}

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path

$headCommit = (& git -C $repositoryRoot rev-parse --verify HEAD 2>$null).Trim()
$headShortCommit = (& git -C $repositoryRoot rev-parse --short HEAD 2>$null).Trim()
if ($LASTEXITCODE -ne 0 -or -not $headCommit -or -not $headShortCommit) {
    throw 'The repository must have a checked-out Git commit.'
}

if (-not $Commit) {
    $Commit = $headShortCommit
}
if (-not $Commit -or $Commit -notmatch '^[0-9a-fA-F]+$') {
    throw 'Commit must be a short hexadecimal Git revision.'
}
$resolvedCommit = (& git -C $repositoryRoot rev-parse --verify ("{0}^{{commit}}" -f $Commit) 2>$null).Trim()
if ($LASTEXITCODE -ne 0 -or $resolvedCommit -ne $headCommit) {
    throw 'Commit must resolve to the checked-out HEAD; checkout the desired revision before packaging.'
}
$Commit = $headShortCommit
$dirtyTrackedFiles = @(& git -C $repositoryRoot status --porcelain --untracked-files=no)
if ($dirtyTrackedFiles.Count -gt 0) {
    throw 'The working tree has tracked changes; commit or discard them before packaging.'
}
if (-not $DeployDate) {
    $DeployDate = Get-Date -Format 'yyyy-MM-dd'
}
if ($DeployDate -notmatch '^\d{4}-\d{2}-\d{2}$') {
    throw 'DeployDate must use yyyy-MM-dd.'
}
if (-not $OutputRoot) {
    $OutputRoot = Join-Path $repositoryRoot 'artifacts\acl\deploy'
}
if (-not [IO.Path]::IsPathRooted($OutputRoot)) {
    $OutputRoot = Join-Path $repositoryRoot $OutputRoot
}

$deployDirectory = Join-Path (Join-Path (Join-Path $OutputRoot $DeployDate) 'deploys') $Commit
if (Test-Path -LiteralPath $deployDirectory) {
    throw "Refusing to overwrite an existing package: $deployDirectory"
}

New-Item -ItemType Directory -Force -Path $deployDirectory | Out-Null

$excludedDirectories = @('__pycache__', 'site')
$excludedExtensions = @('.pyc', '.pyo', '.pyd', '.sqlite3')
$trackedBotFiles = @(& git -C $repositoryRoot ls-files --full-name -- bot)
if ($LASTEXITCODE -ne 0) {
    throw 'Could not enumerate tracked bot files.'
}
$sourceFiles = foreach ($relativeFromRepository in $trackedBotFiles) {
    $relative = $relativeFromRepository.Substring(4)
    $segments = $relative -split '[\\/]'
    $sourcePath = Join-Path $repositoryRoot $relativeFromRepository
    if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
        throw "Tracked bot file is missing from the checkout: $relativeFromRepository"
    }
    $sourceFile = Get-Item -LiteralPath $sourcePath
    if (($segments | Where-Object { $_ -in $excludedDirectories }).Count -eq 0 -and
        $sourceFile.Extension.ToLowerInvariant() -notin $excludedExtensions -and
        $sourceFile.Name -notin @('.env', '.env.example')) {
        $sourceFile
    }
}

foreach ($sourceFile in $sourceFiles) {
    $relative = (Get-RelativePath $repositoryRoot $sourceFile.FullName).Substring(4)
    $destination = Join-Path $deployDirectory $relative
    $parent = Split-Path -Parent $destination
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    Copy-Item -LiteralPath $sourceFile.FullName -Destination $destination
}

foreach ($requirementsName in @('requirements.txt', 'requirements-aclclouds.txt')) {
    $requirements = Join-Path $repositoryRoot $requirementsName
    $trackedRequirement = @(& git -C $repositoryRoot ls-files --full-name -- $requirementsName)
    if ($LASTEXITCODE -ne 0) {
        throw "Could not inspect tracked requirements: $requirementsName"
    }
    if ($trackedRequirement.Count -gt 0) {
        Copy-Item -LiteralPath $requirements -Destination (Join-Path $deployDirectory $requirementsName)
    }
}

$trackedAssetFiles = @(& git -C $repositoryRoot ls-files --full-name -- assets/bot)
if ($LASTEXITCODE -ne 0) {
    throw 'Could not enumerate tracked bot artwork.'
}
if ($trackedAssetFiles.Count -gt 0) {
    $destinationAssetRoot = Join-Path $deployDirectory 'assets\bot'
    foreach ($relativeFromRepository in $trackedAssetFiles) {
        $relative = $relativeFromRepository.Substring('assets/bot/'.Length)
        $sourcePath = Join-Path $repositoryRoot $relativeFromRepository
        if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
            throw "Tracked artwork is missing from the checkout: $relativeFromRepository"
        }
        $destination = Join-Path $destinationAssetRoot $relative
        $parent = Split-Path -Parent $destination
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
        Copy-Item -LiteralPath $sourcePath -Destination $destination
    }
}

$forbidden = Get-ChildItem -LiteralPath $deployDirectory -File -Recurse | Where-Object {
    $relative = Get-RelativePath $deployDirectory $_.FullName
    $relative -match '(^|[\\/])site([\\/]|$)' -or
    $_.Extension.ToLowerInvariant() -in $excludedExtensions -or
    $_.Name -in @('.env', '.env.example')
}
if ($forbidden) {
    throw 'The package contains a forbidden frontend, secret, database, or bytecode path.'
}

$manifest = @{
    kind = 'peace-acl-backend'
    commit = $Commit
    date = $DeployDate
    startup = 'python -u main.py'
    frontend = 'excluded; Netlify publishes bot/site'
    files = @(
        Get-ChildItem -LiteralPath $deployDirectory -File -Recurse | ForEach-Object {
            [ordered]@{
                path = (Get-RelativePath $deployDirectory $_.FullName).Replace('\', '/')
                sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
            }
        }
    )
}
$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $deployDirectory 'DEPLOYMENT-MANIFEST.json') -Encoding UTF8

Write-Output ("ACL backend package created: {0}" -f $deployDirectory)
Write-Output ("Files: {0}" -f ((Get-ChildItem -LiteralPath $deployDirectory -File -Recurse).Count))
