# CNAB PIX Payment System - Windows Installer
# Usage: Right-click > "Run with PowerShell" or: powershell -ExecutionPolicy Bypass -File install.ps1

param(
    [string]$InstallDir = "$env:LOCALAPPDATA\CNAB-PIX"
)

$ErrorActionPreference = "Stop"
$RepoURL = "https://github.com/ribamartins/cnab-vtex.git"
$MinPython = "3.12"

function Write-Step($msg) { Write-Host "`n>> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "   $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "   $msg" -ForegroundColor Yellow }
function Write-Fail($msg) { Write-Host "   $msg" -ForegroundColor Red }

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  CNAB PIX Payment System - Instalador"      -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Diretorio de instalacao: $InstallDir"

# --- 1. Check/Install Python ---
Write-Step "Verificando Python..."

$pythonCmd = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "Python (\d+\.\d+)") {
            $found = $Matches[1]
            if ([version]$found -ge [version]$MinPython) {
                $pythonCmd = $cmd
                Write-Ok "Python $found encontrado ($cmd)"
                break
            } else {
                Write-Warn "Python $found encontrado, mas versao minima e $MinPython"
            }
        }
    } catch {}
}

if (-not $pythonCmd) {
    Write-Warn "Python $MinPython+ nao encontrado. Instalando..."

    $installerUrl = "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe"
    $installerPath = "$env:TEMP\python-installer.exe"

    Write-Host "   Baixando Python 3.12.8..."
    Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath -UseBasicParsing

    Write-Host "   Instalando Python (isso pode levar alguns minutos)..."
    Start-Process -FilePath $installerPath -ArgumentList "/quiet", "InstallAllUsers=0", "PrependPath=1", "Include_pip=1" -Wait -NoNewWindow

    Remove-Item $installerPath -ErrorAction SilentlyContinue

    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "User") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "Machine")

    # Re-check
    foreach ($cmd in @("python", "python3", "py")) {
        try {
            $ver = & $cmd --version 2>&1
            if ($ver -match "Python (\d+\.\d+)" -and [version]$Matches[1] -ge [version]$MinPython) {
                $pythonCmd = $cmd
                break
            }
        } catch {}
    }

    if (-not $pythonCmd) {
        Write-Fail "Falha ao instalar Python. Instale manualmente: https://python.org/downloads/"
        Write-Host "   Marque 'Add Python to PATH' durante a instalacao."
        Read-Host "Pressione Enter para sair"
        exit 1
    }
    Write-Ok "Python instalado com sucesso"
}

# --- 2. Check/Install Git ---
Write-Step "Verificando Git..."

$gitAvailable = $false
try {
    $gitVer = & git --version 2>&1
    if ($gitVer -match "git version") {
        $gitAvailable = $true
        Write-Ok "Git encontrado: $gitVer"
    }
} catch {}

if (-not $gitAvailable) {
    Write-Warn "Git nao encontrado. Instalando..."

    $gitInstaller = "$env:TEMP\git-installer.exe"
    $gitUrl = "https://github.com/git-for-windows/git/releases/download/v2.47.1.windows.1/Git-2.47.1-64-bit.exe"

    Write-Host "   Baixando Git..."
    Invoke-WebRequest -Uri $gitUrl -OutFile $gitInstaller -UseBasicParsing

    Write-Host "   Instalando Git..."
    Start-Process -FilePath $gitInstaller -ArgumentList "/VERYSILENT", "/NORESTART", "/NOCANCEL", "/SP-", "/CLOSEAPPLICATIONS", "/RESTARTAPPLICATIONS", "/COMPONENTS=icons,ext\reg\shellhere,assoc,assoc_sh" -Wait -NoNewWindow

    Remove-Item $gitInstaller -ErrorAction SilentlyContinue

    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "User") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "Machine")

    try {
        $gitVer = & git --version 2>&1
        if ($gitVer -match "git version") {
            $gitAvailable = $true
            Write-Ok "Git instalado com sucesso"
        }
    } catch {}

    if (-not $gitAvailable) {
        Write-Fail "Falha ao instalar Git. Instale manualmente: https://git-scm.com/download/win"
        Read-Host "Pressione Enter para sair"
        exit 1
    }
}

# --- 3. Clone repository ---
Write-Step "Clonando repositorio..."

if (Test-Path "$InstallDir\src\main.py") {
    Write-Warn "Instalacao existente encontrada. Atualizando..."
    Push-Location $InstallDir
    & git pull origin main 2>&1
    Pop-Location
    Write-Ok "Repositorio atualizado"
} else {
    if (Test-Path $InstallDir) {
        Remove-Item $InstallDir -Recurse -Force
    }
    & git clone $RepoURL $InstallDir 2>&1
    Write-Ok "Repositorio clonado em $InstallDir"
}

# --- 4. Create virtual environment and install dependencies ---
Write-Step "Criando ambiente virtual..."

Push-Location $InstallDir

if (-not (Test-Path "venv")) {
    & $pythonCmd -m venv venv
    Write-Ok "Ambiente virtual criado"
} else {
    Write-Ok "Ambiente virtual existente"
}

Write-Step "Instalando dependencias..."
& venv\Scripts\pip.exe install --upgrade pip --quiet 2>&1
& venv\Scripts\pip.exe install -r requirements.txt --quiet 2>&1
Write-Ok "Dependencias instaladas"

Pop-Location

# --- 5. Create launcher script ---
Write-Step "Criando atalhos..."

$launcherPath = "$InstallDir\cnab-pix.bat"
@"
@echo off
cd /d "$InstallDir"
call venv\Scripts\activate.bat
set PYTHONPATH=%cd%\src
python src\main.py
"@ | Out-File -FilePath $launcherPath -Encoding ASCII

Write-Ok "Launcher criado: $launcherPath"

# Desktop shortcut
$desktopPath = [Environment]::GetFolderPath("Desktop")
$shortcutPath = "$desktopPath\CNAB PIX.lnk"

try {
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $launcherPath
    $shortcut.WorkingDirectory = $InstallDir
    $shortcut.Description = "CNAB PIX Payment System"
    $shortcut.Save()
    Write-Ok "Atalho criado na area de trabalho: CNAB PIX"
} catch {
    Write-Warn "Nao foi possivel criar atalho na area de trabalho"
}

# --- Done ---
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  Instalacao concluida!"                      -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Para iniciar o sistema:"
Write-Host "  - Duplo clique no atalho 'CNAB PIX' na area de trabalho"
Write-Host "  - Ou execute: $launcherPath"
Write-Host ""
Read-Host "Pressione Enter para sair"
