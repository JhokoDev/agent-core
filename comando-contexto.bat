$ArquivoSaida = "projeto_completo.txt"

# 1. Escreve a estrutura de pastas e ficheiros
"=== ESTRUTURA DO PROJETO ===`n" | Out-File $ArquivoSaida -Encoding utf8
Get-ChildItem -Recurse | Where-Object { $_.FullName -notmatch '\\node_modules|\\__pycache__|\\\.git' } | ForEach-Object { $depth = ($_.FullName -split '\\').Count - (Get-Location).Path.Split('\\').Count; "  " * $depth +$(if ($_.PSIsContainer) { "+-- [" + $_.Name + "]" } else { "|   " + $_.Name }) } \vert{} Out-File$ArquivoSaida -Append -Encoding utf8

# 2. Escreve o código-fonte de cada ficheiro (apenas extensões de texto/código)
"`n`n=== CONTEÚDO DOS ARQUIVOS ===`n" | Out-File $ArquivoSaida -Append -Encoding utf8
Get-ChildItem -Recurse -File | Where-Object { $_.FullName -notmatch '\\node_modules|\\__pycache__|\\\.git' -and $_.Extension -match '\.(py|jsx|js|html|css|json|md|txt|bat)$' } | ForEach-Object { "`n`n--- ARQUIVO: $($_.FullName.Replace((Get-Location).Path + '\', '')) ---`n"; Get-Content $_.FullName -Raw -ErrorAction SilentlyContinue } \vert{} Out-File$ArquivoSaida -Append -Encoding utf8

Write-Host "Exportação concluída! Arquivo salvo na sua pasta atual como: $ArquivoSaida" -ForegroundColor Green