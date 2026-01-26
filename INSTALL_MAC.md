# 🚀 INSTALACIÓN EN MACBOOK AIR - GUÍA RÁPIDA

## ⚡ Setup AUTOMÁTICO (2 pasos, 2 minutos)

### Método 1: Setup Automático (RECOMENDADO) 🎯

```bash
cd ~/Downloads
unzip cashflow-optimizer-v2.zip
cd cashflow-optimizer
./setup_mac.sh
```

Eso es todo! El script hace todo automáticamente:
- ✅ Crea virtual environment
- ✅ Instala todas las dependencias
- ✅ Configura todo

Luego ejecuta:
```bash
./run.sh
```

Abre: **http://localhost:8080**

---

### Método 2: Manual (si prefieres hacerlo paso a paso)

```bash
# 1. Extrae
cd ~/Downloads
unzip cashflow-optimizer-v2.zip
cd cashflow-optimizer

# 2. Crea virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Instala dependencias
pip install -r requirements.txt

# 4. Ejecuta
python app.py
```

Abre: **http://localhost:8080**

---

## ✅ TODO YA CONFIGURADO

La app corre en **puerto 8080** (no interfiere con AirPlay).

La base de datos ya tiene tus datos:
- ✅ Checking: $5,552
- ✅ Savings: $7,000 / $15,000
- ✅ 3 tarjetas (BofA, Amex, Citi)
- ✅ Gastos fijos y variables
- ✅ Meta de ahorro: $500/catorcena

**NO necesitas hacer `python3 init_db.py`** - ya está inicializado.

---

## 🎯 Uso

1. Abre **http://localhost:8080**
2. Ingresa monto de compra (ej: $500)
3. Click "🔍 Recomendar Tarjeta"
4. Sistema te dice qué tarjeta usar y por qué

---

## 🔄 Cómo ejecutar después de la instalación

### Opción A - Usar script automático:
```bash
cd ~/Downloads/cashflow-optimizer
./run.sh
```

### Opción B - Manual:
```bash
cd ~/Downloads/cashflow-optimizer
source venv/bin/activate
python app.py
```

---

## 🐛 Troubleshooting Mac

### "Permission denied" al ejecutar ./setup_mac.sh
```bash
chmod +x setup_mac.sh run.sh
./setup_mac.sh
```

### "python: command not found"
→ Usa `python3` en lugar de `python`

### "Port 8080 already in use"
→ Raro, pero si pasa, edita `app.py` última línea y cambia 8080 por 9000

### Quieres reiniciar DB desde cero
```bash
source venv/bin/activate
rm instance/cashflow.db
python init_db.py
```

---

## 📁 Archivos incluidos

```
cashflow-optimizer/
├── setup_mac.sh               # 🎯 Script de instalación automática
├── run.sh                     # 🎯 Script para ejecutar la app
├── app.py                     # Backend Flask (puerto 8080)
├── recommendation_engine.py   # Motor inteligente
├── cash_flow_calculator.py    # Proyecciones
├── init_db.py                 # Setup datos
├── analyze_cashflow.py        # Análisis detallado
├── requirements.txt           # Dependencias
├── INSTALL_MAC.md            # Esta guía
├── README.md                 # Documentación
├── templates/
│   └── index.html           # Dashboard
└── instance/
    └── cashflow.db          # Base de datos (ya configurada)
```

---

## 🎮 Comandos útiles

### Ver análisis detallado de tu cash flow
```bash
source venv/bin/activate
python analyze_cashflow.py
```

### Probar motor de recomendación
```bash
source venv/bin/activate
python test_recommendation.py
```

### Detener el servidor
```
Ctrl + C
```

---

## 📊 Próximos pasos después de instalar

1. **Ejecuta**: `./run.sh`
2. **Abre**: http://localhost:8080
3. **Prueba** el recomendador con $500
4. **Revisa** `analyze_cashflow.py` para ver tu proyección de enero

---

## 🔄 Si quieres actualizar tus datos

1. Edita `init_db.py`
2. Cambia los números (balance, gastos, etc.)
3. Ejecuta:
```bash
source venv/bin/activate
rm instance/cashflow.db
python init_db.py
```

---

## 💡 Tips para Mac

- ✅ **Usa los scripts**: `./setup_mac.sh` y `./run.sh`
- ✅ **Virtual environment**: Todo aislado, no afecta tu sistema
- ✅ **Puerto 8080**: No interfiere con AirPlay
- ✅ **Python 3.8+**: Tu Mac ya lo tiene instalado
- ✅ **No necesitas sudo**: Todo se instala en el directorio local

---

## ⚡ Resumen súper rápido

```bash
cd ~/Downloads
unzip cashflow-optimizer-v2.zip
cd cashflow-optimizer
./setup_mac.sh
./run.sh
```

Abre: **http://localhost:8080**

---

**¡Listo! Disfruta tu sistema de cash flow.** 🎉

*Para soporte, revisa README.md*
