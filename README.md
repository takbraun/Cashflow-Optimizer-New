# 💳 Cash Flow Optimizer + Savings Tracker

Sistema inteligente de gestión de tarjetas de crédito con recomendador basado en cash flow y metas de ahorro.

## 🎯 Características

### ✅ Implementado (MVP v1.0)
- **Recomendador Inteligente**: Sistema de scoring que analiza 5 factores para recomendar la mejor tarjeta
- **Proyección de Cash Flow**: Calcula balance futuro considerando ingresos, gastos y pagos de tarjetas
- **Tracking de Savings Goal**: Monitoreo de progreso hacia meta de $15,000
- **Dashboard Visual**: Interfaz limpia con Tailwind CSS
- **3 Tarjetas Configuradas**: BofA, Amex, Citi con fechas de corte reales

### 🎯 Factores de Scoring

El motor de recomendación evalúa cada tarjeta con estos pesos:

1. **Timing (35%)**: Cuándo pagarás la compra vs cuándo recibes catorcenas
2. **Liquidez (25%)**: Si tendrás suficiente balance el día de pago
3. **Impacto en Ahorro (15%)**: Si la compra afecta tu meta de ahorro
4. **Utilization (15%)**: Porcentaje de límite de crédito usado
5. **Distribución (10%)**: Balance de transacciones entre tarjetas

## 📁 Estructura del Proyecto

```
cashflow-optimizer/
├── app.py                      # Flask app principal con modelos y rutas
├── recommendation_engine.py    # Motor de recomendación inteligente
├── cash_flow_calculator.py     # Calculador de proyecciones y ahorro
├── init_db.py                  # Script de inicialización con tus datos
├── requirements.txt            # Dependencias Python
├── templates/
│   └── index.html             # Dashboard principal
└── cashflow.db                # SQLite database (se crea automáticamente)
```

## 🚀 Instalación y Setup

### 1. Instalar dependencias

```bash
cd /home/claude/cashflow-optimizer
pip install -r requirements.txt --break-system-packages
```

### 2. Inicializar base de datos

```bash
python init_db.py
```

Esto crea la base de datos con:
- ✅ Tus 3 tarjetas (BofA, Amex, Citi)
- ✅ Balance actual de checking ($5,552)
- ✅ Fondo de emergencia ($7,000 / $15,000)
- ✅ Ingresos quincenales ($3,300 días 9 y 23)
- ✅ Gastos fijos (PLACEHOLDER - necesita tu lista real)
- ✅ Meta de ahorro ($500/catorcena)
- ✅ Bono de marzo ($5,000)

### 3. Actualizar gastos fijos

**IMPORTANTE**: El script usa gastos placeholder. Necesitas actualizarlos con tu lista real.

Edita `init_db.py` y reemplaza la sección de `FixedExpense` con tus gastos reales.

### 4. Ejecutar la app

```bash
python app.py
```

Abre en navegador: `http://localhost:8080`

## 💡 Cómo Usar

### Recomendador de Tarjetas

1. Ingresa monto de compra
2. (Opcional) Selecciona fecha
3. Click en "Recomendar Tarjeta"
4. El sistema muestra:
   - 🥇 Mejor opción con score y razones
   - 🥈 🥉 Alternativas con comparación
   - Breakdown visual de cada factor
   - Fecha de pago y balance proyectado

### Ejemplo de Recomendación

```
🥇 BofA - Score: 92/100
   └─ Pagarás: 16 Feb (42 días)
   └─ Balance ese día: $6,200 ✅
   └─ Utilization después: 2.5% ✅
   └─ RAZÓN: Timing excelente | Tendrás $6,200 disponible | Tarjeta casi vacía
```

## 🗄️ Modelos de Datos

### Card
```python
- name: str
- closing_day: int (1-31)
- payment_days_after: int
- credit_limit: float
- current_balance: float
- color: str (hex)
```

### Account (Checking)
```python
- balance: float
- last_updated: datetime
```

### SavingsAccount
```python
- balance: float
- target: float
- last_updated: datetime
```

### IncomeSchedule
```python
- amount: float
- first_paycheck_day: int
- second_paycheck_day: int
```

### FixedExpense
```python
- name: str
- amount: float
- due_day: int
- category: str
- active: bool
```

### SavingsGoal
```python
- amount_per_paycheck: float
- min_balance_comfort: float
- variable_expenses_monthly: float
```

### BonusEvent
```python
- amount: float
- expected_date: datetime
- description: str
- received: bool
```

## 🔌 API Endpoints

### GET /api/dashboard
Retorna estado completo del dashboard
```json
{
  "checking_balance": 5552.00,
  "savings": {
    "balance": 7000,
    "target": 15000,
    "progress_pct": 46.7
  },
  "cards": [...],
  "income": {...},
  "savings_goal": {...}
}
```

### POST /api/recommend
Obtiene recomendación de tarjeta
```json
// Request
{
  "amount": 500.00,
  "date": "2026-01-05"  // opcional
}

// Response
{
  "recommendations": [
    {
      "card_id": 1,
      "card_name": "BofA",
      "score": 92.0,
      "breakdown": {
        "timing": 35.0,
        "liquidity": 25.0,
        "savings_impact": 15.0,
        "utilization": 15.0,
        "distribution": 2.0
      },
      "payment_date": "2026-02-16",
      "projected_balance": 6200.00,
      "reasoning": "Timing excelente | Tendrás $6,200 disponible",
      "rank": 1
    },
    ...
  ]
}
```

### GET /api/savings/calculate-available
Calcula cuánto se puede transferir a ahorros ahora
```json
{
  "current_balance": 5552.00,
  "min_balance_required": 2000.00,
  "upcoming_expenses": 2800.00,
  "available_for_savings": 752.00,
  "recommended_transfer": 500.00,
  "would_meet_goal": true
}
```

### POST /api/savings/transfer
Transfiere dinero a ahorros
```json
// Request
{
  "amount": 500.00
}

// Response
{
  "success": true,
  "new_checking_balance": 5052.00,
  "new_savings_balance": 7500.00
}
```

## ⚠️ TODO - Pendientes

### Crítico (Necesario para funcionar correctamente)
1. ⏰ **Actualizar gastos fijos** con tu lista real del screenshot
2. 🔢 **Confirmar variable_expenses_monthly** (actualmente $800 placeholder)
3. 📅 **Fecha exacta del bono de marzo** (actualmente 15-Mar placeholder)

### Features Fase 2 (Próximas mejoras)
- [ ] Registro manual de transacciones
- [ ] Calendario visual de pagos
- [ ] Alertas automáticas cuando balance < mínimo
- [ ] Proyección de savings timeline (cuándo llegas a $15k)
- [ ] Export de datos a CSV
- [ ] Análisis por catorcena
- [ ] Gráficas de utilization histórica

### Features Fase 3 (Deploy + Mobile)
- [ ] Deploy en Railway/Render
- [ ] PWA para instalar en móvil
- [ ] Notificaciones push
- [ ] Dark mode
- [ ] Integración con APIs bancarias (futuro)

## 🐛 Troubleshooting

### Error: "System not configured"
→ Ejecuta `python init_db.py` primero

### Recomendaciones no aparecen
→ Verifica que hayas inicializado la DB y que haya tarjetas activas

### Balance proyectado incorrecto
→ Actualiza tus gastos fijos reales en `init_db.py` y reinicializa

## 📊 Estrategia de Ahorro (Configuración Actual)

- **Meta por catorcena**: $500
- **Balance mínimo confort**: $2,000
- **Gastos variables mensuales**: $800 (placeholder)
- **Progreso actual**: $7,000 / $15,000 (46.7%)
- **Bono marzo**: +$5,000
- **ETA para $15k**: ~Jun 2026 (con bono)

## 🔐 Seguridad

**IMPORTANTE**: Esta app es para uso local/personal. NO está lista para producción.

Antes de deploy público necesitas:
- [ ] Autenticación de usuarios
- [ ] HTTPS/SSL
- [ ] Encriptación de datos sensibles
- [ ] Rate limiting
- [ ] CSRF protection
- [ ] Input sanitization

## 📞 Contacto & Soporte

Desarrollado para Polo's personal use.
Preguntas o bugs → Contactar directamente

---

**Version**: 1.0.0 (MVP)  
**Last Updated**: 2026-01-03  
**Status**: ✅ Functional con placeholders | ⏰ Necesita gastos fijos reales
