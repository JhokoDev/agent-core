import whisper
import os

# Carrega o modelo "base" (equilíbrio perfeito entre velocidade e precisão)
print(" Carregando motor de áudio Whisper (isso pode demorar na primeira vez)...")
modelo_whisper = whisper.load_model("base")
print(" Motor de áudio carregado!")

def transcrever_audio(caminho_arquivo: str) -> str:
    """ Lê um arquivo físico de áudio e devolve o texto em português. """
    try:
        # Força o idioma para português para acelerar a inferência
        resultado = modelo_whisper.transcribe(caminho_arquivo, language="pt")
        return resultado.get("text", "").strip()
    except Exception as e:
        return f"[Erro na transcrição de áudio: {e}]"
    finally:
        # Garante que o arquivo temporário será deletado do PC para não lotar o disco
        if os.path.exists(caminho_arquivo):
            os.remove(caminho_arquivo)