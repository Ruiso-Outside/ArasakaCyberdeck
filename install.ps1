# ============================================================
#   ARASAKA CYBERDECK // instalador Windows
#   Uso:  clique duas vezes em install.bat
#         (ou: powershell -ExecutionPolicy Bypass -File install.ps1)
# ============================================================
$ErrorActionPreference = 'Stop'
$App  = 'arasaka-cyberdeck'
$Dir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$Data = Join-Path $env:LOCALAPPDATA $App
$Bin  = Join-Path $Data 'bin'

function Step($t) { Write-Host ""; Write-Host "[$script:n] $t" -ForegroundColor Red; $script:n++ }
function Ok($t)   { Write-Host "     ■ $t" -ForegroundColor Gray }
function Warn($t) { Write-Host "     !! $t" -ForegroundColor Yellow }
$script:n = 1

Write-Host ""
Write-Host "   A R A S A K A   C Y B E R D E C K" -ForegroundColor Red
Write-Host "   Lancador rapido" -ForegroundColor DarkGray

if (-not (Test-Path (Join-Path $Dir 'arasaka_cyberdeck\app.py'))) { throw "Arquivos do app nao encontrados em $Dir" }

Step "Python"
$py = $null
foreach ($c in @('py', 'python', 'python3')) {
    $cmd = Get-Command $c -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source -notlike '*WindowsApps*') { $py = $cmd.Source; break }
}
if (-not $py) {
    Warn "Python nao encontrado. Instalando com winget..."
    winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
    $py = (Get-Command py -ErrorAction SilentlyContinue).Source
    if (-not $py) { throw "Instale o Python 3.9+ (python.org) e rode de novo." }
}
$ver = & $py -c "import sys; print('%d.%d' % sys.version_info[:2])"
Ok "Python $ver ($py)"

Step "Ambiente Python (PySide6 / Qt 6)"
New-Item -ItemType Directory -Force -Path $Data, $Bin | Out-Null
$vpy = Join-Path $Data 'venv\Scripts\python.exe'
if (-not (Test-Path $vpy)) { & $py -m venv (Join-Path $Data 'venv') }
& $vpy -m pip install -q --upgrade pip 2>$null | Out-Null
Write-Host "     › baixando PySide6 (~120 MB na primeira vez)..."
& $vpy -m pip install -q --upgrade "PySide6-Essentials>=6.5"
if ($LASTEXITCODE -ne 0) { throw "falha ao instalar as dependencias do Python" }
Ok ("PySide6 " + (& $vpy -c "import PySide6; print(PySide6.__version__)"))

Step "Arquivos do app"
$appDir = Join-Path $Data 'app'
if (Test-Path $appDir) { Remove-Item -Recurse -Force $appDir }
New-Item -ItemType Directory -Force -Path $appDir | Out-Null
Copy-Item -Recurse (Join-Path $Dir 'arasaka_cyberdeck') $appDir
Get-ChildItem -Recurse -Directory -Filter '__pycache__' $appDir | Remove-Item -Recurse -Force
$pyw = Join-Path $Data 'venv\Scripts\pythonw.exe'
# lancador: roda "python -m arasaka_cyberdeck" sem janela de console, de qualquer diretorio
$launch = Join-Path $Data 'launch.pyw'
Set-Content -Encoding UTF8 -Path $launch -Value @"
import runpy, sys
sys.path.insert(0, r"$appDir")
sys.argv[0] = "arasaka_cyberdeck"
runpy.run_module("arasaka_cyberdeck", run_name="__main__", alter_sys=True)
"@
Set-Content -Encoding ASCII -Path (Join-Path $Bin "$App.cmd") -Value "@echo off`r`nstart `"`" `"$pyw`" `"$launch`" %*"

# icone .ico gerado a partir do SVG
$ico = Join-Path $Data "$App.ico"
$svg = Join-Path $appDir 'arasaka_cyberdeck\assets\arasaka-cyberdeck.svg'
if (Test-Path $svg) {
    & $vpy -c "import sys; from PySide6.QtGui import QGuiApplication, QIcon; a=QGuiApplication(sys.argv); QIcon(sys.argv[1]).pixmap(256,256).save(sys.argv[2])" $svg $ico 2>$null
}

# PATH do usuario
$up = [Environment]::GetEnvironmentVariable('Path', 'User')
if (-not ($up -split ';' | Where-Object { $_ -eq $Bin })) {
    [Environment]::SetEnvironmentVariable('Path', ($up.TrimEnd(';') + ';' + $Bin), 'User')
    Ok "comando 'arasaka-cyberdeck' adicionado ao PATH (abra um novo terminal)"
}

# atalhos
$ws = New-Object -ComObject WScript.Shell
$menu = Join-Path ([Environment]::GetFolderPath('Programs')) 'Arasaka Cyberdeck.lnk'
$desk = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Arasaka Cyberdeck.lnk'
foreach ($lnk in @($menu, $desk)) {
    $s = $ws.CreateShortcut($lnk)
    $s.TargetPath = $pyw
    $s.Arguments = "`"$launch`""
    $s.WorkingDirectory = $env:USERPROFILE
    if (Test-Path $ico) { $s.IconLocation = $ico }
    $s.Description = 'Arasaka Cyberdeck - Lancador rapido'
    $s.Save()
}
Ok "atalhos no Menu Iniciar e na Area de Trabalho"

# atalho de teclado: o Windows abre o atalho do Menu Iniciar com Ctrl+Alt+Espaco (como no Linux)
$s = $ws.CreateShortcut($menu)
$s.Arguments = "`"$launch`" --toggle"
$s.Hotkey = 'CTRL+ALT+SPACE'
$s.Save()
Ok "Ctrl+Alt+Espaco abre e fecha o Cyberdeck"

Write-Host ""
Write-Host " ■ INSTALACAO CONCLUIDA" -ForegroundColor Red
Write-Host "   Abra 'Arasaka Cyberdeck' no Menu Iniciar."
Write-Host ""
