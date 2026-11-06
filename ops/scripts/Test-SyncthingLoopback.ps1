$ErrorActionPreference = "Stop"

$exe = Join-Path (Split-Path -Parent $PSScriptRoot) "tools\syncthing-v2.1.5\syncthing.exe"
$base = Join-Path ([System.IO.Path]::GetTempPath()) ("central-sync-loopback-" + [guid]::NewGuid().ToString("N"))
$aHome = Join-Path $base "A"
$bHome = Join-Path $base "B"
$aShared = Join-Path $aHome "shared"
$bShared = Join-Path $bHome "shared"
$aLog = Join-Path $base "A.log"
$bLog = Join-Path $base "B.log"
$aProcess = $null
$bProcess = $null

function Stop-Node([System.Diagnostics.Process] $process) {
    if ($null -eq $process) { return }
    $processId = $process.Id
    try {
        if (-not $process.HasExited) {
            $process.Kill($true)
            $process.WaitForExit(5000) | Out-Null
        }
    } catch { }
    try {
        if (Get-Process -Id $processId -ErrorAction SilentlyContinue) {
            Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
        }
    } catch { }
    $process.Dispose()
}

function Invoke-NodeApi([string] $baseUrl, [string] $apiKey, [string] $path, [string] $method = "Get", [string] $body = $null) {
    $headers = @{ "X-API-Key" = $apiKey }
    $params = @{
        Uri = $baseUrl.TrimEnd("/") + "/" + $path.TrimStart("/")
        Headers = $headers
        Method = $method
        TimeoutSec = 5
    }
    if (-not [string]::IsNullOrEmpty($body)) {
        $params["ContentType"] = "application/json"
        $params["Body"] = $body
    }
    Invoke-RestMethod @params
}

function Wait-Node([string] $baseUrl, [string] $apiKey) {
    $lastError = "indisponível"
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        try { return Invoke-NodeApi $baseUrl $apiKey "rest/system/status" }
        catch {
            $lastError = $_.Exception.Message
            Start-Sleep -Milliseconds 250
        }
    }
    throw "Syncthing não respondeu em $($baseUrl): $lastError"
}

function Set-BooleanOption([xml] $document, [string] $name, [string] $value) {
    $node = $document.configuration.options.SelectSingleNode($name)
    if ($null -ne $node) { $node.InnerText = $value }
}

try {
    if (-not (Test-Path -LiteralPath $exe)) {
        throw "Syncthing empacotado não encontrado: $exe"
    }

    New-Item -ItemType Directory -Path $aHome, $bHome | Out-Null
    & $exe generate --home $aHome | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Falha ao gerar a configuração A" }
    & $exe generate --home $bHome | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Falha ao gerar a configuração B" }

    [xml]$aConfig = Get-Content -Raw (Join-Path $aHome "config.xml")
    [xml]$bConfig = Get-Content -Raw (Join-Path $bHome "config.xml")
    $aOwn = $aConfig.configuration.device
    $bOwn = $bConfig.configuration.device
    $aId = $aOwn.id
    $bId = $bOwn.id
    $aKey = $aConfig.configuration.gui.apikey
    $bKey = $bConfig.configuration.gui.apikey

    foreach ($spec in @(
        @{ Doc = $aConfig; Port = "8385"; Listen = "22001"; Name = "Loopback A" },
        @{ Doc = $bConfig; Port = "8386"; Listen = "22002"; Name = "Loopback B" }
    )) {
        $spec.Doc.configuration.gui.address = "127.0.0.1:$($spec.Port)"
        $spec.Doc.configuration.options.listenAddress = "tcp://127.0.0.1:$($spec.Listen)"
        $spec.Doc.configuration.device.name = $spec.Name
        Set-BooleanOption $spec.Doc "globalAnnounceEnabled" "false"
        Set-BooleanOption $spec.Doc "localAnnounceEnabled" "false"
        Set-BooleanOption $spec.Doc "relaysEnabled" "false"
        Set-BooleanOption $spec.Doc "natEnabled" "false"
        Set-BooleanOption $spec.Doc "crashReportingEnabled" "false"
        Set-BooleanOption $spec.Doc "startBrowser" "false"
        $spec.Doc.configuration.options.autoUpgradeIntervalH = "0"
    }

    $aRemote = $aOwn.CloneNode($true)
    $aRemote.SetAttribute("id", $bId)
    $aRemote.SetAttribute("name", "Loopback B")
    $aRemote.address = "tcp://127.0.0.1:22002"
    $aRemote.paused = "false"
    $aConfig.configuration.InsertBefore($aRemote, $aConfig.configuration.gui) | Out-Null

    $bRemote = $bOwn.CloneNode($true)
    $bRemote.SetAttribute("id", $aId)
    $bRemote.SetAttribute("name", "Loopback A")
    $bRemote.address = "tcp://127.0.0.1:22001"
    $bRemote.paused = "false"
    $bConfig.configuration.InsertBefore($bRemote, $bConfig.configuration.gui) | Out-Null

    $aFolder = $aConfig.configuration.defaults.folder.CloneNode($true)
    $aFolder.SetAttribute("id", "central-loopback")
    $aFolder.SetAttribute("label", "Central Loopback")
    $aFolder.SetAttribute("path", $aShared)
    $aFolder.SetAttribute("type", "sendreceive")
    foreach ($child in @($aFolder.device)) { [void]$aFolder.RemoveChild($child) }
    $aDeviceRef = $aConfig.CreateElement("device")
    $aDeviceRef.SetAttribute("id", $bId)
    $aDeviceRef.SetAttribute("introducedBy", "")
    [void]$aFolder.AppendChild($aDeviceRef)
    $aConfig.configuration.InsertBefore($aFolder, $aConfig.configuration.defaults) | Out-Null

    $bFolder = $bConfig.configuration.defaults.folder.CloneNode($true)
    $bFolder.SetAttribute("id", "central-loopback")
    $bFolder.SetAttribute("label", "Central Loopback")
    $bFolder.SetAttribute("path", $bShared)
    $bFolder.SetAttribute("type", "sendreceive")
    foreach ($child in @($bFolder.device)) { [void]$bFolder.RemoveChild($child) }
    $bDeviceRef = $bConfig.CreateElement("device")
    $bDeviceRef.SetAttribute("id", $aId)
    $bDeviceRef.SetAttribute("introducedBy", "")
    [void]$bFolder.AppendChild($bDeviceRef)
    $bConfig.configuration.InsertBefore($bFolder, $bConfig.configuration.defaults) | Out-Null

    $aConfig.Save((Join-Path $aHome "config.xml"))
    $bConfig.Save((Join-Path $bHome "config.xml"))
    New-Item -ItemType Directory -Path $aShared, $bShared | Out-Null

    $argumentsA = @("serve", "--home", ('"' + $aHome + '"'), "--no-browser", "--no-console", "--no-restart")
    $argumentsB = @("serve", "--home", ('"' + $bHome + '"'), "--no-browser", "--no-console", "--no-restart")
    $aProcess = Start-Process -FilePath $exe -ArgumentList $argumentsA -WindowStyle Hidden -RedirectStandardOutput $aLog -RedirectStandardError ($aLog + ".err") -PassThru
    $bProcess = Start-Process -FilePath $exe -ArgumentList $argumentsB -WindowStyle Hidden -RedirectStandardOutput $bLog -RedirectStandardError ($bLog + ".err") -PassThru
    $aStatus = Wait-Node "http://127.0.0.1:8385" $aKey
    $bStatus = Wait-Node "http://127.0.0.1:8386" $bKey
    if ($aStatus.myID -ne $aId -or $bStatus.myID -ne $bId -or $aId -eq $bId) {
        throw "Device IDs inválidos no loopback"
    }

    $aConnections = $null
    $bConnections = $null
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        $aConnections = Invoke-NodeApi "http://127.0.0.1:8385" $aKey "rest/system/connections"
        $bConnections = Invoke-NodeApi "http://127.0.0.1:8386" $bKey "rest/system/connections"
        $aPeer = $aConnections.connections.$bId
        $bPeer = $bConnections.connections.$aId
        if ($aPeer.connected -and $bPeer.connected) { break }
        Start-Sleep -Milliseconds 500
    }
    if (-not $aConnections.connections.$bId.connected -or -not $bConnections.connections.$aId.connected) {
        throw "Peers não conectaram no loopback"
    }

    $seed = "central loopback A $(Get-Date -Format o)"
    $aFile = Join-Path $aShared "roundtrip.txt"
    $bFile = Join-Path $bShared "roundtrip.txt"
    [IO.File]::WriteAllText($aFile, $seed)
    for ($attempt = 0; $attempt -lt 60 -and -not (Test-Path $bFile); $attempt++) { Start-Sleep -Milliseconds 500 }
    if (-not (Test-Path $bFile)) { throw "Arquivo A não chegou a B" }
    $hashA = (Get-FileHash $aFile -Algorithm SHA256).Hash
    $hashB = (Get-FileHash $bFile -Algorithm SHA256).Hash
    if ($hashA -ne $hashB) { throw "Hash A->B divergente" }

    $back = "central loopback B $(Get-Date -Format o)"
    [IO.File]::WriteAllText($bFile, $back)
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        if ((Get-Content -Raw $aFile) -eq $back) { break }
        Start-Sleep -Milliseconds 500
    }
    if ((Get-Content -Raw $aFile) -ne $back) { throw "Arquivo B não voltou a A" }

    $pauseBody = '{"paused":true}'
    Invoke-NodeApi "http://127.0.0.1:8385" $aKey "rest/config/folders/central-loopback" "Patch" $pauseBody | Out-Null
    Start-Sleep -Seconds 2
    $pausedMarker = Join-Path $aShared "paused-marker.txt"
    $pausedRemote = Join-Path $bShared "paused-marker.txt"
    [IO.File]::WriteAllText($pausedMarker, "paused")
    Start-Sleep -Seconds 4
    if (Test-Path $pausedRemote) { throw "A pausa não bloqueou a transferência" }
    Invoke-NodeApi "http://127.0.0.1:8385" $aKey "rest/config/folders/central-loopback" "Patch" '{"paused":false}' | Out-Null
    for ($attempt = 0; $attempt -lt 60 -and -not (Test-Path $pausedRemote); $attempt++) { Start-Sleep -Milliseconds 500 }
    if (-not (Test-Path $pausedRemote)) { throw "O arquivo não voltou após reconexão" }

    $conflictA = Join-Path $aShared "conflict.txt"
    $conflictB = Join-Path $bShared "conflict.txt"
    [IO.File]::WriteAllText($conflictA, "base")
    for ($attempt = 0; $attempt -lt 60 -and -not (Test-Path $conflictB); $attempt++) { Start-Sleep -Milliseconds 500 }
    if (-not (Test-Path $conflictB)) { throw "Base do conflito não foi compartilhada" }
    Stop-Node $aProcess
    Stop-Node $bProcess
    $aProcess = $null
    $bProcess = $null
    [IO.File]::WriteAllText($conflictA, "A-version")
    [IO.File]::WriteAllText($conflictB, "B-version")
    $aProcess = Start-Process -FilePath $exe -ArgumentList $argumentsA -WindowStyle Hidden -PassThru
    $bProcess = Start-Process -FilePath $exe -ArgumentList $argumentsB -WindowStyle Hidden -PassThru
    Wait-Node "http://127.0.0.1:8385" $aKey | Out-Null
    Wait-Node "http://127.0.0.1:8386" $bKey | Out-Null
    $conflictCopy = $null
    for ($attempt = 0; $attempt -lt 80; $attempt++) {
        $conflictCopy = Get-ChildItem -LiteralPath $aShared, $bShared -Filter "*sync-conflict*" -File -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($null -ne $conflictCopy) { break }
        Start-Sleep -Milliseconds 500
    }
    if ($null -eq $conflictCopy) { throw "Conflito controlado não gerou cópia sync-conflict" }

    Write-Output ("LOOPBACK PASS | deviceA={0} | deviceB={1} | A->B hash={2} | B->A=ok | pause/resume=ok | conflictCopy={3}" -f $aId, $bId, $hashA, $conflictCopy.FullName)
}
catch {
    if (Test-Path -LiteralPath $aLog) {
        Write-Output ("Syncthing A log:`n" + (Get-Content -Raw $aLog))
    }
    if (Test-Path -LiteralPath ($aLog + ".err")) {
        Write-Output ("Syncthing A stderr:`n" + (Get-Content -Raw ($aLog + ".err")))
    }
    if (Test-Path -LiteralPath $bLog) {
        Write-Output ("Syncthing B log:`n" + (Get-Content -Raw $bLog))
    }
    if (Test-Path -LiteralPath ($bLog + ".err")) {
        Write-Output ("Syncthing B stderr:`n" + (Get-Content -Raw ($bLog + ".err")))
    }
    throw
}
finally {
    Stop-Node $aProcess
    Stop-Node $bProcess
    Get-CimInstance Win32_Process |
        Where-Object { $_.Name -eq "syncthing.exe" -and $_.CommandLine -like "*$base*" } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    if (Test-Path -LiteralPath $base) {
        for ($attempt = 0; $attempt -lt 5; $attempt++) {
            try {
                Remove-Item -LiteralPath $base -Recurse -Force -ErrorAction Stop
                break
            }
            catch {
                Start-Sleep -Milliseconds 500
            }
        }
    }
}
