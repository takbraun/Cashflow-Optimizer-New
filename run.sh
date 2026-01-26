#!/bin/bash

# Script para ejecutar la app (activa venv automáticamente)

if [ ! -d "venv" ]; then
    echo "❌ Virtual environment no encontrado."
    echo "   Ejecuta primero: ./setup_mac.sh"
    exit 1
fi

echo "🚀 Iniciando Cash Flow Optimizer..."
source venv/bin/activate
python3 app.py
