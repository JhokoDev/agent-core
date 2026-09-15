# Somente diagnóstico. Não instala software nem cria serviço/Bridge.
$ErrorActionPreference = "Stop"
Write-Output "Preflight do Windows — Fase 0"
Write-Output ([System.Environment]::OSVersion.VersionString)
foreach ($Tool in @("py", "git", "tailscale", "kicad-cli")) {
    $Found = Get-Command $Tool -ErrorAction SilentlyContinue
    if ($Found) { Write-Output "$Tool : encontrado" }
    else { Write-Output "$Tool : não encontrado no PATH" }
}
Write-Output "O KiCad pode estar instalado fora do PATH. Bridge e rede serão implementados na Fase 5."
