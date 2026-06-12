#!/bin/bash
# Entrypoint para el contenedor Ollama.
# Inicia el servidor Ollama, espera que esté listo y descarga el modelo.

set -e

MODEL="${OLLAMA_MODEL:-llama3.2:3b}"

echo "🚀 Iniciando Ollama server..."
ollama serve &

# Esperar a que Ollama esté listo (usando ollama list en vez de curl)
echo "⏳ Esperando que Ollama esté disponible..."
for i in $(seq 1 30); do
    if ollama list > /dev/null 2>&1; then
        echo "✅ Ollama está listo!"
        break
    fi
    sleep 2
done

# Descargar el modelo si no existe
echo "📥 Verificando modelo $MODEL..."
if ollama list 2>/dev/null | grep -q "$MODEL"; then
    echo "✅ Modelo $MODEL ya está descargado"
else
    echo "📥 Descargando modelo $MODEL (puede tomar varios minutos)..."
    ollama pull "$MODEL"
    echo "✅ Modelo $MODEL descargado"
fi

# Mantener el contenedor vivo
wait
