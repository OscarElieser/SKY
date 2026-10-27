#Requires -Version 5.1
<#
.SYNOPSIS
  Instala en UNA ejecucion las dependencias declaradas de SKY IA en Windows.
.DESCRIPTION
  Completo: todos los manifiestos Python opcionales en requirements_sky_all.txt.
  Base/Casa: solo requirements.txt. Reutiliza .venv y no borra datos/secretos.
  -Herramientas agrega programas externos mediante winget con confirmacion
  previa del usuario; -ModeloOllama incluye un modelo segun la RAM.
  No expone puertos, no inicia SKY ni activa funciones con privilegios.
.EJEMPLO
  .\INSTALAR_DEPENDENCIAS_SKY.ps1 -Perfil Completo -Herramientas
.EJEMPLO
  .\INSTALAR_DEPENDENCIAS_SKY.ps1 -Perfil Casa
.EJEMPLO
  .\INSTALAR_DEPENDENCIAS_SKY.ps1 -Perfil Completo -SoloVerificar
#>
[CmdletBinding()]
param(
    [ValidateSet("Base", "Casa", "Completo")]
    [string]$Perfil = "Completo",
    [switch]$Herramientas,
    [switch]$ModeloOllama,
    [switch]$OmitirNode,
    [switch]$SoloVerificar
)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $Root
$PythonVenv = Join-Path $Root ".venv\Scripts\python.exe"
$Pending = New-Object 'System.Collections.Generic.List[string]'

function Notice([string]$Text) { Write-Host "[SKY] $Text" -ForegroundColor Cyan }
function Warn([string]$Text) { Write-Warning $Text; $Pending.Add($Text) }
function Require-Exit([string]$Step) {
    if ($LASTEXITCODE -ne 0) { throw "$Step fallo (exit code $LASTEXITCODE)" }
}
function Existing([string]$Command) {
    return [bool](Get-Command $Command -ErrorAction SilentlyContinue)
}

$Manifest = if ($Perfil -eq "Completo") {
    Join-Path $Root "requirements_sky_all.txt"
} else { Join-Path $Root "requirements.txt" }
if (-not (Test-Path -LiteralPath $Manifest)) { throw "Falta el manifiesto: $Manifest" }
Notice "Perfil: $Perfil. Origen: $Manifest"
if ($Perfil -eq "Completo") {
    Notice "Instalacion completa: entrenamiento, GPU/IA, multimedia, documentacion, conectores y voz."
    Notice "Puede ocupar varios GB. Algunas integraciones externas exigen claves, licencias o servicios independientes."
}

# Verificar es siempre read-only: ni winget, ni pip install, ni modelos.
if ($SoloVerificar) {
    if (-not (Test-Path -LiteralPath $PythonVenv)) {
        throw "No existe .venv. Verificacion: sin crear ni instalar nada."
    }
    $Auditor = Join-Path $Root "scripts\sky_dependencias_todas.py"
    & $PythonVenv $Auditor --manifest $Manifest
    $Result = $LASTEXITCODE
    & $PythonVenv -m pip check
    $PipCheck = $LASTEXITCODE
    if ($Result -ne 0) { exit $Result }
    exit $PipCheck
}

# Herramientas fuera del proyecto: instalarlas SOLO si se solicito -Herramientas.
if ($Herramientas) {
    if (-not (Existing "winget")) {
        Warn "winget no disponible. Instala App Installer y repeti el comando para herramientas externas."
    } else {
        $Tools = @(
            @{ Name = "Python 3.12"; Command = "python"; Id = "Python.Python.3.12" },
            @{ Name = "Git"; Command = "git"; Id = "Git.Git" },
            @{ Name = "Node.js / npm"; Command = "node"; Id = "OpenJS.NodeJS.LTS" },
            @{ Name = "Java JDK 17"; Command = "javac"; Id = "EclipseAdoptium.Temurin.17.JDK" },
            @{ Name = "FFmpeg"; Command = "ffmpeg"; Id = "Gyan.FFmpeg" },
            @{ Name = "Tailscale"; Command = "tailscale"; Id = "Tailscale.Tailscale" },
            @{ Name = "Ollama"; Command = "ollama"; Id = "Ollama.Ollama" },
            @{ Name = "Flutter SDK"; Command = "flutter"; Id = "Google.Flutter" },
            @{ Name = "Android Studio"; Command = "studio64"; Id = "Google.AndroidStudio" }
        )
        foreach ($Item in $Tools) {
            if (Existing $Item.Command) {
                Notice "$($Item.Name) detectado: no se reinstala."
                continue
            }
            Notice "Instalando programa externo: $($Item.Name) [$($Item.Id)]"
            & winget install --exact --id $Item.Id --accept-package-agreements --accept-source-agreements
            if ($LASTEXITCODE -ne 0) {
                Warn "No se pudo instalar automaticamente $($Item.Name). Revisalo en winget/instalador oficial."
            } else {
                Notice "$($Item.Name): instalacion solicitada; puede requerir nueva terminal y configuracion."
            }
        }
    }
}

# Crear el entorno de SKY solo si no existe. Nunca borrar ni reemplazar .venv.
if (-not (Test-Path -LiteralPath $PythonVenv)) {
    Notice "Creando .venv por primera vez. Se busca Python 3.12 / 3.11."
    $Created = $false
    if (Existing "py") {
        & py -3.12 --version 2>$null
        if ($LASTEXITCODE -eq 0) {
            & py -3.12 -m venv (Join-Path $Root ".venv")
            Require-Exit "Crear entorno con Python 3.12"
            $Created = $true
        } else {
            & py -3.11 --version 2>$null
            if ($LASTEXITCODE -eq 0) {
                & py -3.11 -m venv (Join-Path $Root ".venv")
                Require-Exit "Crear entorno con Python 3.11"
                $Created = $true
            }
        }
    }
    if (-not $Created -and (Existing "python")) {
        $Version = & python --version 2>&1
        if ("$Version" -match "^Python 3\.(11|12)\.") {
            & python -m venv (Join-Path $Root ".venv")
            Require-Exit "Crear entorno Python"
            $Created = $true
        }
    }
    if (-not $Created) {
        $Candidates = @(
            (Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"),
            "C:\Program Files\Python312\python.exe"
        )
        foreach ($Candidate in $Candidates) {
            if (Test-Path -LiteralPath $Candidate) {
                & $Candidate -m venv (Join-Path $Root ".venv")
                Require-Exit "Crear entorno Python con el ejecutable instalado"
                $Created = $true
                break
            }
        }
    }
    if (-not $Created) {
        throw "Python 3.11/3.12 no disponible. Instala Python 3.12 oficialmente y vuelve a ejecutar. No se modifico .venv."
    }
} else {
    Notice "Entorno .venv detectado: se conserva. No se usa el pip global."
}
& $PythonVenv --version
Require-Exit "Python de SKY"

# UNA resolucion pip para el perfil solicitado: utiliza la cache y respeta paquetes compatibles.
Notice "Resolviendo dependencias Python desde un unico manifiesto. No se fuerza --upgrade."
& $PythonVenv -m pip install --disable-pip-version-check -r $Manifest
Require-Exit "Instalar dependencias del manifiesto"
& $PythonVenv -m pip check
Require-Exit "Verificar compatibilidad Python"
Notice "Paquetes Python instalados/verificados con pip check."

# Paquetes JavaScript declarados por el repositorio, sin reescribir package.json o lock.
if ($Perfil -eq "Completo" -and -not $OmitirNode) {
    $Npm = Get-Command "npm.cmd" -ErrorAction SilentlyContinue
    if (-not $Npm) {
        Warn "npm no disponible en esta terminal. Reiniciarla tras instalar Node y volver a ejecutar."
    } else {
        foreach ($Folder in @("sky_d3", "sky_remotion", "templates\sky_design_react")) {
            $Project = Join-Path $Root $Folder
            if (-not (Test-Path -LiteralPath (Join-Path $Project "package.json"))) {
                throw "Falta package.json en $Folder; no se borran modulos."
            }
            $NpmPath = $Npm.Source
            $NodeReady = $false
            if (Test-Path -LiteralPath (Join-Path $Project "node_modules")) {
                & $NpmPath --prefix $Project ls --depth=0 --silent 2>$null
                $NodeReady = ($LASTEXITCODE -eq 0)
            }
            if ($NodeReady) {
                Notice "Node: $Folder validado, no requiere instalar otra vez."
            } else {
                Notice "Node: instalando requisitos ausentes en $Folder"
                & $NpmPath --prefix $Project install --no-save --no-package-lock --no-audit --no-fund
                if ($LASTEXITCODE -ne 0) { Warn "npm fallo en $Folder; revisar ese modulo." }
            }
        }
    }
}

# Flutter es el SDK independiente de Dart; pubspec.yaml versiona la plantilla.
if ($Perfil -eq "Completo") {
    if (Existing "flutter") {
        Notice "Flutter: resolviendo pubspec de plantilla (sin cambiar fuentes)."
        Push-Location (Join-Path $Root "templates\sky_design_flutter")
        try {
            & flutter pub get
            if ($LASTEXITCODE -ne 0) { Warn "flutter pub get fallo; revisar SDK/red." }
        } finally { Pop-Location }
    } else { Warn "Flutter SDK no aparece en PATH. La plantilla Flutter no pudo preparar paquetes." }
    Notice "Android requiere ademas SDK 35, build-tools 35.0.0, JDK17 y Gradle 8.11.1."
    Notice "Android Studio instala SDK/licencias por separado; no se acepta licencias ni se ejecuta Gradle automaticamente."
}

# Modelos grandes: opcionales, no se requiere GPU ni se fuerza un modelo de 7B en 8 GB.
if ($ModeloOllama) {
    if (-not (Existing "ollama")) {
        Warn "Ollama no aparece en esta terminal; no se descargaron modelos."
    } else {
        $GB = 8
        try { $GB = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB) } catch { }
        $Model = if ($GB -ge 16) { "qwen2.5:7b" } else { "qwen2.5:3b" }
        $ModelNames = @(& ollama list 2>$null)
        $Installed = $false
        if ($LASTEXITCODE -eq 0) {
            foreach ($Entry in $ModelNames) {
                if ((("$Entry".Trim()) -split '\s+')[0] -eq $Model) { $Installed = $true; break }
            }
        }
        if ($Installed) { Notice "Modelo $Model ya disponible: sin descargar." }
        else {
            Notice "Descargando modelo local opcional $Model (RAM: $GB GB)."
            & ollama pull $Model
            if ($LASTEXITCODE -ne 0) { Warn "No se pudo descargar el modelo $Model." }
        }
    }
}
if ($Pending.Count -gt 0) {
    Write-Host ""
    Write-Warning "$($Pending.Count) tareas opcionales pendientes. El nucleo Python se verifico; NO se garantiza instalacion total."
    foreach ($Item in $Pending) { Write-Host "  - $Item" }
    exit 2
}
Notice "Instalacion declarada finalizada. No se iniciaron servicios ni se habilito acceso remoto."
