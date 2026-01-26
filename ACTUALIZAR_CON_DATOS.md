# 🔄 ACTUALIZACIÓN SEGURA - MANTÉN TUS DATOS

## ✅ GARANTÍA: NO PERDERÁS NADA

Este proceso mantiene **todos tus gastos registrados**.

---

## 🚀 INSTALACIÓN PARA USUARIOS EXISTENTES

### Paso 1: Respalda tu base de datos actual

```bash
cd /Developer/Cashflow-Cashflow-Optimizer
cp instance/cashflow.db instance/MI-BACKUP.db
```

**Importante:** Guarda este backup en lugar seguro (Dropbox, Google Drive, etc.)

---

### Paso 2: Extrae nueva versión en NUEVO directorio

```bash
cd /Developer
unzip -o ~/Downloads/cashflow-optimizer-v3-CON-MIGRACION.zip -d cashflow-optimizer-NEW
cd cashflow-optimizer-NEW/cashflow-optimizer
```

---

### Paso 3: Copia tu base de datos antigua

```bash
# Copia tu base de datos CON DATOS al nuevo proyecto
cp /Developer/Cashflow-Cashflow-Optimizer/instance/cashflow.db instance/cashflow.db
```

---

### Paso 4: Ejecuta migración

```bash
chmod +x setup_mac.sh run.sh
./setup_mac.sh
python3 migrate_database.py
```

Verás:
```
🔄 Cash Flow Optimizer - Database Migration
============================================================

🔄 Starting database migration...
   Database: instance/cashflow.db
✅ Backup created: instance/cashflow-backup-20260103-183045.db
📝 Adding card_id column to variable_expense_log...
✅ card_id column added

✅ Migration completed successfully!
   Your data is safe and the database is updated
   Backup available at: instance/cashflow-backup-20260103-183045.db

📊 Current data:
   Variable expenses: 5
   Fixed expenses paid: 2

✅ Migration successful!
   You can now run: ./run.sh
```

---

### Paso 5: Ejecuta la app

```bash
./run.sh
```

Abre: **http://localhost:8080**

✅ **Verás todos tus gastos anteriores + nuevas funcionalidades**

---

## 🔄 RESUMEN DEL PROCESO

```
Tu DB actual (con datos)
  en /Developer/Cashflow-Cashflow-Optimizer
         ↓
    Hacer backup
         ↓
Copiar a nueva versión
         ↓
  Ejecutar migración
         ↓
DB actualizada (con tus datos + nuevos campos)
```

---

## ✅ QUÉ HACE LA MIGRACIÓN

1. **Crea backup automático** (por si acaso)
2. **Agrega columna `card_id`** a gastos variables
3. **Verifica datos existentes** estén correctos
4. **Mantiene TODO** lo que ya registraste

---

## 📊 VERIFICACIÓN POST-MIGRACIÓN

Después de migrar, verifica:

```bash
# Ve tus gastos variables
python3 -c "
from app import app, db, VariableExpenseLog
with app.app_context():
    expenses = VariableExpenseLog.query.all()
    for e in expenses:
        print(f'{e.expense_date.date()} - {e.category} - \${e.amount}')
"

# Ve tus gastos fijos pagados
python3 -c "
from app import app, db, ExpensePayment
with app.app_context():
    payments = ExpensePayment.query.all()
    for p in payments:
        print(f'{p.payment_date.date()} - {p.expense.name} - \${p.amount}')
"
```

Si ves tus gastos → ✅ Migración exitosa

---

## ⚠️ SI ALGO SALE MAL

### Restaurar backup:
```bash
cd /Developer/cashflow-optimizer-NEW/cashflow-optimizer
cp instance/MI-BACKUP.db instance/cashflow.db
./run.sh
```

O usa el backup automático:
```bash
cp instance/cashflow-backup-*.db instance/cashflow.db
```

---

## 💡 ALTERNATIVA: Actualizar en el mismo directorio

Si prefieres actualizar en tu directorio actual:

```bash
# 1. Backup
cd /Developer/Cashflow-Cashflow-Optimizer
cp instance/cashflow.db ~/Desktop/BACKUP-cashflow.db

# 2. Extrae nueva versión encima
cd /Developer
unzip -o ~/Downloads/cashflow-optimizer-v3-CON-MIGRACION.zip
mv cashflow-optimizer/* Cashflow-Cashflow-Optimizer/
rm -rf cashflow-optimizer

# 3. Restaura tu DB
cd /Developer/Cashflow-Cashflow-Optimizer
cp ~/Desktop/BACKUP-cashflow.db instance/cashflow.db

# 4. Migra
./setup_mac.sh
python3 migrate_database.py
./run.sh
```

---

## 💡 ALTERNATIVA SIMPLE (Si prefieres empezar de cero)

Si no tienes muchos datos o prefieres empezar limpio:

```bash
cd /Developer
rm -rf Cashflow-Cashflow-Optimizer
unzip ~/Downloads/cashflow-optimizer-v3-CON-MIGRACION.zip
mv cashflow-optimizer Cashflow-Cashflow-Optimizer
cd Cashflow-Cashflow-Optimizer
./setup_mac.sh
./run.sh
```

Esto crea una DB nueva con tus configuraciones pero sin gastos registrados.

---

## 🎯 RECOMENDACIÓN

**Usa la migración** si ya tienes:
- Gastos variables registrados
- Gastos fijos marcados como pagados
- Balance actualizado manualmente

**Empieza de cero** si:
- Es tu primer día usando el sistema
- Solo probaste sin registrar datos reales
- Prefieres empezar limpio

---

## 📞 SOPORTE

Si tienes problemas:
1. Tu backup está en `instance/MI-BACKUP.db`
2. Migración crea backup automático también
3. Tu directorio viejo sigue en `/Developer/Cashflow-Cashflow-Optimizer`
4. Siempre puedes restaurar

---

**¡Tus datos están seguros!** 🎉
