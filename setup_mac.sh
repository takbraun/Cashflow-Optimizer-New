#!/bin/bash

# Cash Flow Optimizer - Auto Setup Script para Mac
# Este script configura todo automáticamente usando virtual environment

echo "🚀 Cash Flow Optimizer - Instalación Automática"
echo "================================================"
echo ""

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Verificar que estamos en el directorio correcto
if [ ! -f "requirements.txt" ]; then
    echo "❌ Error: Ejecuta este script desde el directorio cashflow-optimizer"
    echo "   cd cashflow-optimizer"
    echo "   ./setup_mac.sh"
    exit 1
fi

echo -e "${BLUE}📦 Paso 1/4:${NC} Creando virtual environment..."
python3 -m venv venv

echo -e "${BLUE}📦 Paso 2/4:${NC} Activando virtual environment..."
source venv/bin/activate

echo -e "${BLUE}📦 Paso 3/4:${NC} Instalando dependencias..."
pip install -r requirements.txt

echo -e "${BLUE}📦 Paso 4/4:${NC} Verificando instalación..."
python3 --version
echo ""

echo -e "${GREEN}✅ Instalación completada!${NC}"
echo ""
echo "================================================"
echo -e "${YELLOW}🎯 Para ejecutar la app:${NC}"
echo ""
echo "   python app.py"
echo ""
echo -e "   Luego abre: ${GREEN}http://localhost:8080${NC}"
echo ""
echo "================================================"
echo -e "${YELLOW}💡 Comandos útiles:${NC}"
echo ""
echo "   Ver análisis:     python3 analyze_cashflow.py"
echo "   Probar sistema:   python3 test_recommendation.py"
echo "   Detener server:   Ctrl + C"
echo ""
echo "================================================"
echo ""
echo -e "${GREEN}🚀 ¿Listo para empezar? Ejecuta:${NC}"
echo ""
echo "   ./run.sh"
echo ""
echo "   (O manualmente: source venv/bin/activate && python3 app.py)"
echo ""
