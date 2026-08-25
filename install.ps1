# Palworld Editor - instalador (Windows, por usuario / per-user, sem admin)
# Uso / Usage:  powershell -ExecutionPolicy Bypass -File install.ps1
#
# Instala em %LOCALAPPDATA%\Programs\Palworld Editor, cria atalhos no Menu
# Iniciar e na Area de Trabalho, e registra em "Adicionar/Remover programas".

$ErrorActionPreference = "Stop"
$origem = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $origem
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
& $exe $arg -m pip install -r (Join-Path $origem "requirements.txt") --quiet
Write-Host "Dependencias OK." -ForegroundColor Green

# 3) Copiar o programa para a pasta de instalacao -----------------------
$destino = Join-Path $env:LOCALAPPDATA "Programs\Palworld Editor"
Write-Host "Instalando em: $destino" -ForegroundColor Cyan

# se ja existe uma instalacao, fecha o app e limpa a pasta antiga
Get-Process pythonw -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -and $_.Path -like "*Palworld Editor*" } |
    Stop-Process -Force -ErrorAction SilentlyContinue
if (Test-Path $destino) {
    Remove-Item -Recurse -Force $destino -ErrorAction SilentlyContinue
}
New-Item -ItemType Directory -Force -Path $destino | Out-Null

# copia tudo, menos o que nao deve ir junto
$ignorar = @(".git", "__pycache__", "backups", "config.json",
             "extracao_local.json", "teste_icones", "fmodel")
Get-ChildItem -Force $origem | Where-Object { $ignorar -notcontains $_.Name } | ForEach-Object {
    Copy-Item $_.FullName -Destination $destino -Recurse -Force
}
# remove __pycache__ que possa ter sido copiado
Get-ChildItem -Path $destino -Recurse -Force -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# 3b) Oodle (para editar pontos de tecnologia): procura um DLL ja existente
#     (FModel do usuario, ou um oo2core de jogo Unreal) e copia para dentro do app,
#     assim o editor le o save do jogador sem o usuario ter que apontar nada.
Write-Host "Procurando Oodle (para pontos de tecnologia)..." -ForegroundColor Cyan
$oodleAlvo = Join-Path $destino "oodle"
$fontes = @(
    (Join-Path $origem "fmodel"),
    (Join-Path $env:LOCALAPPDATA "FModel")
)
$dll = $null
foreach ($f in $fontes) {
    if (Test-Path $f) {
        $dll = Get-ChildItem -Path $f -Recurse -Force -ErrorAction SilentlyContinue `
                 -Include "oodle-data-shared.dll", "oo2core_9_win64.dll", "oo2core_8_win64.dll" |
               Select-Object -First 1
        if ($dll) { break }
    }
}
if ($dll) {
    New-Item -ItemType Directory -Force -Path $oodleAlvo | Out-Null
    Copy-Item $dll.FullName -Destination (Join-Path $oodleAlvo $dll.Name) -Force
    Write-Host "Oodle copiado: $($dll.Name)" -ForegroundColor Green
} else {
    Write-Host "Oodle nao encontrado - pontos de tecnologia pedirao o DLL uma vez." -ForegroundColor Yellow
}

$alvo    = Join-Path $destino "PalSaveEditor.pyw"
$ico     = Join-Path $destino "assets\logo.ico"
$pythonw = (& $exe $arg -c "import sys,os;print(os.path.join(os.path.dirname(sys.executable),'pythonw.exe'))").Trim()
if (-not (Test-Path $pythonw)) { $pythonw = "pythonw.exe" }
$versao = (Get-Content (Join-Path $destino "VERSION") -ErrorAction SilentlyContinue | Select-Object -First 1)
if (-not $versao) { $versao = "1.0.0" }

# 4) Atalhos (Menu Iniciar + Area de Trabalho) -------------------------
function New-Atalho($caminho) {
    $ws = New-Object -ComObject WScript.Shell
    $sc = $ws.CreateShortcut($caminho)
    $sc.TargetPath = $pythonw
    $sc.Arguments = '"' + $alvo + '"'
    $sc.WorkingDirectory = $destino
    if (Test-Path $ico) { $sc.IconLocation = "$ico,0" }  # o ",0" evita cair no icone do pythonw
    $sc.Description = "Palworld Editor"
    $sc.Save()
}
Write-Host "Criando atalhos..." -ForegroundColor Cyan
$menu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
New-Atalho (Join-Path $menu "Palworld Editor.lnk")                                  # Todos os programas
New-Atalho (Join-Path ([Environment]::GetFolderPath("Desktop")) "Palworld Editor.lnk")  # Area de Trabalho

# forca o Explorer a reler o icone (evita ficar mostrando o antigo em cache)
try {
    $sig = '[DllImport("shell32.dll")] public static extern void SHChangeNotify(int e, int f, IntPtr a, IntPtr b);'
    $sh = Add-Type -MemberDefinition $sig -Name Shell -Namespace Win32 -PassThru
    $sh::SHChangeNotify(0x08000000, 0, [IntPtr]::Zero, [IntPtr]::Zero)
} catch {}

# 5) Registrar em "Adicionar/Remover programas" ------------------------
$reg = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\PalworldEditor"
New-Item -Path $reg -Force | Out-Null
$uninst = 'powershell -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + (Join-Path $destino "uninstall.ps1") + '"'
Set-ItemProperty $reg "DisplayName"     "Palworld Editor"
Set-ItemProperty $reg "DisplayVersion"  $versao
Set-ItemProperty $reg "Publisher"       "disouz4-dev"
Set-ItemProperty $reg "DisplayIcon"     $ico
Set-ItemProperty $reg "InstallLocation" $destino
Set-ItemProperty $reg "UninstallString" $uninst
Set-ItemProperty $reg "URLInfoAbout"    "https://github.com/disouz4-dev/Palworld-Edit"
Set-ItemProperty $reg "NoModify" 1 -Type DWord
Set-ItemProperty $reg "NoRepair" 1 -Type DWord

Write-Host ""
Write-Host "== Pronto! ==" -ForegroundColor Green
Write-Host "Abra 'Palworld Editor' pelo Menu Iniciar (Todos os programas) ou pela Area de Trabalho." -ForegroundColor Green
Write-Host "Para remover: Configuracoes > Aplicativos > Palworld Editor > Desinstalar." -ForegroundColor Green
