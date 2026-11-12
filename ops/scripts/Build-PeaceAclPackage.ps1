[CmdletBinding()]
param(
    [string]$OutputRoot = (Join-Path (Get-Location) 'artifacts\acl\deploy'),
    [string]$Commit = '',
    [string]$DeployDate = ''
)

$ErrorActionPreference = 'Stop'

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$botRoot = Join-Path $repositoryRoot 'bot'
$assetRoot = Join-Path $repositoryRoot 'assets\bot'

if (-not $Commit) {
    $Commit = (& git -C $repositoryRoot rev-parse --short HEAD).Trim()
}
if (-not $Commit -or $Commit -notmatch '^[0-9a-fA-F]+$') {
    throw 'Commit must be a short hexadecimal Git revision.'
}
if (-not $DeployDate) {
    $DeployDate = Get-Date -Format 'yyyy-MM-dd'
}
if ($DeployDate -notmatch '^\d{4}-\d{2}-\d{2}$') {
    throw 'DeployDate must use yyyy-MM-dd.'
}

$deployDirectory = Join-Path (Join-Path (Join-Path $OutputRoot $DeployDate) 'deploys') $Commit
if (Test-Path -LiteralPath $deployDirectory) {
    throw "Refusing to overwrite an existing package: $deployDirectory"
}

New-Item -ItemType Directory -Force -Path $deployDirectory | Out-Null

$excludedDirectories = @('__pycache__', 'site')
$excludedExtensions = @('.pyc', '.pyo', '.pyd', '.sqlite3')
$sourceFiles = Get-ChildItem -LiteralPath $botRoot -File -Recurse | Where-Object {
    $relative = [IO.Path]::GetRelativePath($botRoot, $_.FullName)
    $segments = $relative -split '[\\/]'
    ($segments | Where-Object { $_ -in $excludedDirectories }).Count -eq 0 -and
    $_.Extension.ToLowerInvariant() -notin $excludedExtensions -and
    $_.Name -notin @('.env', '.env.example')
}

foreach ($sourceFile in $sourceFiles) {
    $relative = [IO.Path]::GetRelativePath($botRoot, $sourceFile.FullName)
    $destination = Join-Path $deployDirectory $relative
    $parent = Split-Path -Parent $destination
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    Copy-Item -LiteralPath $sourceFile.FullName -Destination $destination
}

foreach ($requirementsName in @('requirements.txt', 'requirements-aclclouds.txt')) {
    $requirements = Join-Path $repositoryRoot $requirementsName
    if (Test-Path -LiteralPath $requirements) {
        Copy-Item -LiteralPath $requirements -Destination (Join-Path $deployDirectory $requirementsName)
    }
}

if (Test-Path -LiteralPath $assetRoot) {
    $destinationAssetRoot = Join-Path $deployDirectory 'assets\bot'
    Get-ChildItem -LiteralPath $assetRoot -File -Recurse | ForEach-Object {
        $relative = [IO.Path]::GetRelativePath($assetRoot, $_.FullName)
        $destination = Join-Path $destinationAssetRoot $relative
        $parent = Split-Path -Parent $destination
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
        Copy-Item -LiteralPath $_.FullName -Destination $destination
    }
}

$forbidden = Get-ChildItem -LiteralPath $deployDirectory -File -Recurse | Where-Object {
    $relative = [IO.Path]::GetRelativePath($deployDirectory, $_.FullName)
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
                path = [IO.Path]::GetRelativePath($deployDirectory, $_.FullName).Replace('\', '/')
                sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
            }
        }
    )
}
$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $deployDirectory 'DEPLOYMENT-MANIFEST.json') -Encoding UTF8

Write-Output ("ACL backend package created: {0}" -f $deployDirectory)
Write-Output ("Files: {0}" -f ((Get-ChildItem -LiteralPath $deployDirectory -File -Recurse).Count))
