#!/bin/bash

echo "🚀 Acordando o Servidor do Agente (Modo 100% Local)..."

# 1. Liga o Ollama em segundo plano (O Cérebro Principal)
echo "🧠 Ligando a Inteligência Artificial (Ollama)..."
ollama serve > /dev/null 2>&1 &

# Pausa de 3 segundos para dar tempo da IA carregar na memória
sleep 3

# 2. Torna a porta 8000 pública para o seu aplicativo Android conseguir conectar
echo "🌐 Configurando a porta 8000 como Pública..."
gh codespace ports visibility 8000:public -c $CODESPACE_NAME

# 3. Inicia o servidor Python carregando as senhas do .env
echo "⚡ Ligando a API FastAPI..."
uvicorn "app.main:create_app" --factory --host 0.0.0.0 --port 8000 --env-file .env
