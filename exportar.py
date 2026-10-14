from pathlib import Path

ignore = {".git", "node_modules", "__pycache__"}
exts = {".py", ".jsx", ".js", ".html", ".css", ".json", ".md", ".txt", ".bat"}
out = Path("projeto_completo.txt")

with out.open("w", encoding="utf-8") as f:
    f.write("=== ESTRUTURA DO PROJETO ===\n")
    
    # 1. Mapeia a estrutura
    for p in sorted(Path('.').rglob('*')):
        if any(i in p.parts for i in ignore): continue
        depth = len(p.relative_to('.').parts) - 1
        indent = "  " * depth
        if p.is_dir():
            f.write(f"{indent}+-- [{p.name}]\n")
        else:
            f.write(f"{indent}|   {p.name}\n")

    f.write("\n\n=== CONTEÚDO DOS ARQUIVOS ===\n")
    
    # 2. Extrai os textos
    for p in Path('.').rglob('*'):
        if p.is_file() and p.suffix in exts and not any(i in p.parts for i in ignore):
            f.write(f"\n\n--- ARQUIVO: {p.relative_to('.')} ---\n")
            try:
                f.write(p.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                f.write("[Erro de leitura]\n")

print(f"Sucesso! Arquivo salvo em: {out.absolute()}")