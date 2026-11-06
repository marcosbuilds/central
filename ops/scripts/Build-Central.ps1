$ErrorActionPreference = 'Stop'

$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$dotnet = Join-Path $root 'tools\dotnet\dotnet.exe'
$iscc = Join-Path $root 'tools\inno-setup\ISCC.exe'
$solution = Join-Path $root 'Central.sln'
$project = Join-Path $root 'app\desktop\Central.Desktop\Central.Desktop.csproj'
$publish = Join-Path $root 'artifacts\publish'
$publishedExe = Join-Path $publish 'Central.exe'
$syncthingSource = Join-Path $root 'tools\syncthing-v2.1.5\syncthing.exe'

if (-not (Test-Path $dotnet)) { throw "SDK local não encontrado: $dotnet" }
if (-not (Test-Path $iscc)) { throw "ISCC não encontrado: $iscc" }
if (-not (Test-Path $syncthingSource)) { throw "Syncthing empacotado não encontrado: $syncthingSource" }

function Invoke-Native {
    param(
        [Parameter(Mandatory)] [string] $FilePath,
        [Parameter(Mandatory)] [string[]] $Arguments
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao executar $FilePath (exit code $LASTEXITCODE)."
    }
}

$runningCentral = Get-Process -Name Central -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $publishedExe }
if ($runningCentral) {
    $runningCentral | Stop-Process -Force
}

Invoke-Native $dotnet @('restore', $solution)
Invoke-Native $dotnet @('build', $solution, '-c', 'Release', '--no-restore')
Invoke-Native $dotnet @('test', $solution, '-c', 'Release', '--no-build', '--no-restore')
Invoke-Native $dotnet @('publish', $project, '-c', 'Release', '-r', 'win-x64', '--self-contained', 'true', '-p:PublishSingleFile=true', '-p:IncludeNativeLibrariesForSelfExtract=true', '-p:DebugType=None', '-p:DebugSymbols=false', '-o', $publish)
Copy-Item -LiteralPath $syncthingSource -Destination (Join-Path $publish 'syncthing.exe') -Force

$installerScript = Join-Path $root 'ops\installer\Central.iss'
Invoke-Native $iscc @("/DSourceDir=$publish", $installerScript)

Write-Host "Artefatos prontos em $root\artifacts"
