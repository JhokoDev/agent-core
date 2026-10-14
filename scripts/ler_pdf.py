import sys
import PyPDF2
import os

if len(sys.argv) < 2:
    print("Erro: Nenhum arquivo fornecido.")
    sys.exit(1)

arquivo = sys.argv[1]
caminho = os.path.join("uploads", arquivo)

if not os.path.exists(caminho):
    print(f"Erro: Arquivo {arquivo} não encontrado na pasta uploads.")
    sys.exit(1)

try:
    texto = ""
    with open(caminho, "rb") as f:
        leitor = PyPDF2.PdfReader(f)
        for pagina in leitor.pages:
            texto += pagina.extract_text() + "\n"
    
    # Imprime apenas os primeiros 6000 caracteres para não estourar a memória do Qwen local
    print(texto[:6000]) 
except Exception as e:
    print(f"Erro fatal ao ler PDF: {e}")