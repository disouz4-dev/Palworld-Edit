# Palworld Editor - instalador automatico / automatic installer (Windows)
# Uso / Usage:  powershell -ExecutionPolicy Bypass -File install.ps1

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $raiz
Write-Host "== Palworld Editor - instalacao ==" -ForegroundColor Cyan

# 1) Python -------------------------------------------------------------
function Get-Python {
    foreach ($c in @("py -3", "python", "python3")) {
        try {
            $exe, $arg = $c.Split(" ", 2)
            $v = & $exe $arg --version 2>&1
            if ($LASTEXITCODE -eq 0 -and $v -match "Python 3") { return $c }
        } catch {}
    }
    return $null
}

$py = Get-Python
if (-not $py) {
    Write-Host "Python nao encontrado. Instalando..." -ForegroundColor Yellow
    $ok = $false
    try {
        winget install -e --id Python.Python.3.12 --scope user `
              --accept-source-agreements --accept-package-agreements
        $ok = $true
    } catch {}
    if (-not $ok) {
        $url = "https://www.python.org/ftp/python/3.12.6/python-3.12.6-amd64.exe"
        $tmp = Join-Path $env:TEMP "python-setup.exe"
        Write-Host "Baixando Python de python.org..."
        Invoke-WebRequest -Uri $url -OutFile $tmp
        Start-Process -Wait -FilePath $tmp -ArgumentList `
            "/quiet InstallAllUsers=0 PrependPath=1 Include_pip=1"
    }
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","User") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path","Machine")
    $py = Get-Python
    if (-not $py) {
        Write-Host "Nao consegui instalar o Python automaticamente." -ForegroundColor Red
        Write-Host "Instale manualmente em https://www.python.org/downloads/ e rode de novo."
        exit 1
    }
}
$exe, $arg = $py.Split(" ", 2)
Write-Host "Python OK: $(& $exe $arg --version)" -ForegroundColor Green

# 2) Dependencias -------------------------------------------------------
Write-Host "Instalando dependencias..." -ForegroundColor Cyan
& $exe $arg -m pip install --upgrade pip --quiet
& $exe $arg -m pip install -r (Join-Path $raiz "requirements.txt") --quiet
Write-Host "Dependencias OK." -ForegroundColor Green

# 3) Atalho na area de trabalho ----------------------------------------
Write-Host "Criando atalho na Area de Trabalho..." -ForegroundColor Cyan
$pythonw = (& $exe $arg -c "import sys,os;print(os.path.join(os.path.dirname(sys.executable),'pythonw.exe'))").Trim()
if (-not (Test-Path $pythonw)) { $pythonw = "pythonw.exe" }
$lnk = Join-Path ([Environment]::GetFolderPath("Desktop")) "Palworld Editor.lnk"
$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut($lnk)
$sc.TargetPath = $pythonw
$sc.Arguments = '"' + (Join-Path $raiz "PalSaveEditor.pyw") + '"'
$sc.WorkingDirectory = $raiz
$ico = Join-Path $raiz "assets\logo.ico"
if (Test-Path $ico) { $sc.IconLocation = $ico }
$sc.Description = "Palworld Editor"
$sc.Save()

Write-Host ""
Write-Host "== Pronto! ==" -ForegroundColor Green
Write-Host "Abra 'Palworld Editor' na sua Area de Trabalho." -ForegroundColor Green
