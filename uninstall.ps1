# Palworld Editor - desinstalador (Windows, por usuario / per-user)
# Remove atalhos, o registro em "Adicionar/Remover programas" e a pasta do programa.

$ErrorActionPreference = "SilentlyContinue"
$destino = Join-Path $env:LOCALAPPDATA "Programs\Palworld Editor"
$dadosUsuario = Join-Path $env:LOCALAPPDATA "PalworldEditor"

# 1) fecha o app se estiver aberto
Get-Process pythonw -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -and $_.Path -like "*Palworld Editor*" } |
    Stop-Process -Force

# 2) remove os atalhos
$menu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Palworld Editor.lnk"
$desk = Join-Path ([Environment]::GetFolderPath("Desktop")) "Palworld Editor.lnk"
Remove-Item $menu -Force
Remove-Item $desk -Force

# 3) remove o registro de "Adicionar/Remover programas"
Remove-Item "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\PalworldEditor" -Recurse -Force

# 4) pergunta se quer manter os backups
$manter = $true
try {
    Add-Type -AssemblyName System.Windows.Forms
    $r = [System.Windows.Forms.MessageBox]::Show(
        "Deseja MANTER seus backups de save?" + [Environment]::NewLine + [Environment]::NewLine +
        "Sim = mantem os backups em:" + [Environment]::NewLine + $dadosUsuario + [Environment]::NewLine +
        "Nao = apaga tudo, inclusive os backups.",
        "Desinstalar Palworld Editor",
        [System.Windows.Forms.MessageBoxButtons]::YesNo,
        [System.Windows.Forms.MessageBoxIcon]::Question)
    if ($r -eq [System.Windows.Forms.DialogResult]::No) { $manter = $false }
} catch {}
if (-not $manter) {
    Remove-Item -Recurse -Force $dadosUsuario
}

# 5) apaga a pasta do programa. Sai de dentro dela primeiro; o proprio script ja
#    esta carregado na memoria, entao pode se auto-apagar junto com a pasta.
Set-Location $env:TEMP
Remove-Item -Recurse -Force $destino

try {
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show(
        "Palworld Editor foi desinstalado.", "Pronto",
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Information) | Out-Null
} catch {}
