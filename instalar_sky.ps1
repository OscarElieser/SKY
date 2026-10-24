# SKY IA v12.3 - Instalador unico para Windows 10/11
# Deja listo: Python + dependencias, Ollama + modelo del cerebro, voz natural Piper,
# escucha local (faster-whisper), manos libres (Vosk), permisos del agente y .env.
# Uso: doble clic en INSTALAR_SKY_WINDOWS.bat (no requiere administrador).
# Se puede ejecutar varias veces: salta lo que ya esta instalado.

param(
    [string]$Modelo = "",          # ej. qwen2.5:7b ; vacio = elegir segun la memoria del equipo
    [switch]$SinOllama,
    [switch]$SinVoz,
    [switch]$Local,                # activa SKY_LOCAL_ONLY=1 (nada sale del equipo)
    [switch]$Siempre               # SKY 24/7: arranca con Windows y el equipo no se suspende enchufado
)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$Raiz = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Raiz
$Neuralt = Join-Path $env:USERPROFILE ".neuralt"
New-Item -ItemType Directory -Force -Path $Neuralt | Out-Null

function Paso($t) { Write-Host ""; Write-Host "== $t" -ForegroundColor Cyan }
function Ok($t)   { Write-Host "   [OK] $t" -ForegroundColor Green }
function Aviso($t){ Write-Host "   [!]  $t" -ForegroundColor Yellow }

function Descargar($url, $destino) {
    if (Test-Path $destino) { return }
    Write-Host "   Descargando $url"
    $tmp = "$destino.part"
    for ($i = 1; $i -le 3; $i++) {
        try { Invoke-WebRequest -Uri $url -OutFile $tmp -UseBasicParsing; Move-Item -Force $tmp $destino; return }
        catch { if ($i -eq 3) { throw } ; Start-Sleep -Seconds 3 }
    }
}

function Set-EnvValue($clave, $valor) {
    $envPath = Join-Path $Raiz ".env"
    if (-not (Test-Path $envPath)) {
        if (Test-Path (Join-Path $Raiz ".env.example")) { Copy-Item (Join-Path $Raiz ".env.example") $envPath }
        else { New-Item -ItemType File -Path $envPath | Out-Null }
    }
    $lineas = @(Get-Content $envPath -Encoding UTF8)
    $patron = "^\s*#?\s*" + [regex]::Escape($clave) + "="
    $nueva = "$clave=$valor"
    $hecho = $false
    for ($i = 0; $i -lt $lineas.Count; $i++) {
        if ($lineas[$i] -match $patron -and -not $hecho) { $lineas[$i] = $nueva; $hecho = $true }
    }
    if (-not $hecho) { $lineas += $nueva }
    [IO.File]::WriteAllLines($envPath, $lineas, (New-Object Text.UTF8Encoding($false)))
}

function Tiene($cmd) { return [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }

# ------------------------------------------------------------------ 1. Python
Paso "Python"
$py = $null
foreach ($c in @("py -3.12", "py -3.11", "python")) {
    try { $v = & cmd /c "$c --version 2>&1"; if ($v -match "Python 3\.(1[0-3])") { $py = $c; break } } catch {}
}
if (-not $py) {
    if (Tiene "winget") {
        winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements --silent
        $py = "py -3.12"
    } else { throw "Instala Python 3.12 desde https://www.python.org/downloads/ y vuelve a ejecutar este instalador." }
}
Ok "Usando: $py"

# ------------------------------------------------------------------ 2. Entorno y dependencias
Paso "Entorno virtual y dependencias (puede tardar varios minutos la primera vez)"
$venvPy = Join-Path $Raiz ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) { & cmd /c "$py -m venv .venv"; if ($LASTEXITCODE) { throw "No se pudo crear .venv" } }
& $venvPy -m pip install --upgrade pip --quiet
& $venvPy -m pip install -r requirements.txt --quiet
if ($LASTEXITCODE) { throw "Fallo la instalacion de requirements.txt" }
& $venvPy -m pip install --quiet faster-whisper vosk sounddevice pyttsx3 psutil pywin32
if ($LASTEXITCODE) { Aviso "Alguna dependencia opcional de voz no se instalo; SKY seguira funcionando." } else { Ok "Dependencias instaladas" }

# ------------------------------------------------------------------ 3. Ollama + modelo del cerebro
if (-not $SinOllama) {
    Paso "Ollama (IA local) y modelo del cerebro"
    $ollama = (Get-Command ollama -ErrorAction SilentlyContinue).Source
    if (-not $ollama) {
        $cand = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
        if (Test-Path $cand) { $ollama = $cand }
    }
    if (-not $ollama -and (Tiene "winget")) {
        winget install -e --id Ollama.Ollama --accept-package-agreements --accept-source-agreements --silent
        $cand = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
        if (Test-Path $cand) { $ollama = $cand }
    }
    if ($ollama) {
        if (-not $Modelo) {
            $gb = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB)
            $Modelo = if ($gb -ge 30) { "qwen2.5:14b" } elseif ($gb -ge 14) { "qwen2.5:7b" } else { "qwen2.5:3b" }
            Ok "Memoria: $gb GB -> modelo $Modelo"
        }
        try { Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -UseBasicParsing -TimeoutSec 2 | Out-Null }
        catch { Start-Process -WindowStyle Hidden -FilePath $ollama -ArgumentList "serve"; Start-Sleep -Seconds 4 }
        & $ollama pull $Modelo
        if ($LASTEXITCODE) { Aviso "No se pudo descargar $Modelo. Ejecuta luego: ollama pull $Modelo" } else { Ok "Modelo $Modelo listo" }
        Set-EnvValue "OLLAMA_MODEL" $Modelo
    } else { Aviso "Instala Ollama desde https://ollama.com/download y luego: ollama pull qwen2.5:7b" }
}

# ------------------------------------------------------------------ 4. Voz: Piper, faster-whisper y Vosk
if (-not $SinVoz) {
    Paso "Voz natural local (Piper, espanol)"
    $piperDir = Join-Path $Neuralt "piper"
    $voces = Join-Path $piperDir "voces"
    New-Item -ItemType Directory -Force -Path $voces | Out-Null
    $piperExe = Join-Path $piperDir "piper\piper.exe"
    if (-not (Test-Path $piperExe)) {
        $zip = Join-Path $piperDir "piper_windows_amd64.zip"
        Descargar "https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_windows_amd64.zip" $zip
        Expand-Archive -Force -Path $zip -DestinationPath $piperDir
        Remove-Item -Force $zip
    }
    $vozBase = "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_MX/claude/high/es_MX-claude-high.onnx"
    Descargar $vozBase (Join-Path $voces "es_MX-claude-high.onnx")
    Descargar "$vozBase.json" (Join-Path $voces "es_MX-claude-high.onnx.json")
    if (Test-Path $piperExe) {
        Set-EnvValue "SKY_PIPER_BIN" $piperExe
        Set-EnvValue "SKY_PIPER_VOICE" (Join-Path $voces "es_MX-claude-high.onnx")
        Ok "Piper listo"
    } else { Aviso "Piper no quedo instalado" }

    Paso "Escucha local (faster-whisper, modelo small)"
    $sttDir = Join-Path $Neuralt "whisper-small"
    if (-not (Test-Path (Join-Path $sttDir "model.bin"))) {
        & $venvPy -c "from faster_whisper import download_model; download_model('small', output_dir=r'$sttDir')"
    }
    if (Test-Path (Join-Path $sttDir "model.bin")) { Set-EnvValue "SKY_STT_MODEL_DIR" $sttDir; Ok "Escucha local lista" }
    else { Aviso "No se pudo descargar el modelo de faster-whisper; el HUD usara el dictado del navegador." }

    Paso "Manos libres en segundo plano (Vosk espanol)"
    $voskDir = Join-Path $Raiz "modelos\vosk-model-es"
    if (-not (Test-Path $voskDir)) {
        New-Item -ItemType Directory -Force -Path (Join-Path $Raiz "modelos") | Out-Null
        $vz = Join-Path $Raiz "modelos\vosk-model-small-es-0.42.zip"
        Descargar "https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip" $vz
        Expand-Archive -Force -Path $vz -DestinationPath (Join-Path $Raiz "modelos")
        Rename-Item (Join-Path $Raiz "modelos\vosk-model-small-es-0.42") "vosk-model-es"
        Remove-Item -Force $vz
    }
    Ok "Vosk listo"
}

# ------------------------------------------------------------------ 5. Permisos y privacidad
Paso "Permisos del agente y privacidad"
if (-not (Test-Path (Join-Path $Neuralt "device_agent_policy.json"))) {
    & $venvPy agente_dispositivo.py --perfil multimedia --solo-config | Out-Null
    Ok "Perfil 'multimedia' (cambialo con SKY_INICIAR.bat -> 6)"
} else { Ok "Se conserva tu politica de permisos" }
if ($Local) { Set-EnvValue "SKY_LOCAL_ONLY" "1"; Ok "Modo 100 % local activado" }

# ------------------------------------------------------------------ 5b. SKY siempre encendida (opcional)
if ($Siempre) {
    Paso "SKY 24/7 en este equipo"
    try {
        powercfg /change standby-timeout-ac 0 | Out-Null
        powercfg /change hibernate-timeout-ac 0 | Out-Null
        Ok "Enchufado, el equipo ya no se suspende (la pantalla si puede apagarse)"
    } catch { Aviso "No pude cambiar el plan de energia: hacelo en Configuracion > Sistema > Inicio/apagado" }
    & $venvPy iniciar_sky_autonomo.py --install-startup
    Ok "SKY arranca sola al iniciar sesion y reinicia sus servicios si se caen"
}

# ------------------------------------------------------------------ 6. Diagnostico
Paso "Diagnostico final"
& $venvPy sky_diagnostico.py
Write-Host ""
Write-Host "SKY esta instalado. Abri SKY_INICIAR.bat y elegi la opcion 0." -ForegroundColor Cyan
