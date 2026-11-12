[CmdletBinding()]
param(
    [string]$OutputRoot = (Join-Path (Get-Location) 'artifacts\acl\deploy'),
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
    $relative = Get-RelativePath $botRoot $_.FullName
    $segments = $relative -split '[\\/]'
    ($segments | Where-Object { $_ -in $excludedDirectories }).Count -eq 0 -and
    $_.Extension.ToLowerInvariant() -notin $excludedExtensions -and
    $_.Name -notin @('.env', '.env.example')
}

foreach ($sourceFile in $sourceFiles) {
    $relative = Get-RelativePath $botRoot $sourceFile.FullName
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
        $relative = Get-RelativePath $assetRoot $_.FullName
        $destination = Join-Path $destinationAssetRoot $relative
        $parent = Split-Path -Parent $destination
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
        Copy-Item -LiteralPath $_.FullName -Destination $destination
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
