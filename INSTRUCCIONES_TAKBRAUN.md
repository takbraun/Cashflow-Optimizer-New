# ⚡ ACTUALIZACIÓN - RUTAS CORRECTAS PARA TU MAC

## 🎯 TU INSTALACIÓN ACTUAL

```
/Users/takbraun/Developer/Cashflow-Optimizer
```

---

## 🚀 ACTUALIZACIÓN PASO A PASO

### 1. Backup (30 segundos) ✅
```bash
cd /Users/takbraun/Developer/Cashflow-Optimizer
cp instance/cashflow.db ~/Desktop/BACKUP-3enero.db
ls -la ~/Desktop/BACKUP-3enero.db
```

Debes ver algo como: `-rw-r--r--  1 takbraun  staff  20480 Jan  3 ... BACKUP-3enero.db` ✅

---

### 2. Extrae nueva versión (1 minuto)
```bash
cd ~/Downloads
unzip -o cashflow-optimizer-v3-FINAL.zip
```

---

### 3. Mueve a Developer (10 segundos)
```bash
mv ~/Downloads/cashflow-optimizer ~/Developer/Cashflow-Optimizer-NEW
cd ~/Developer/Cashflow-Optimizer-NEW
```

---

### 4. Copia tu DB con datos (10 segundos) ✅
```bash
cp ~/Desktop/BACKUP-3enero.db instance/cashflow.db
ls -la instance/cashflow.db
```

Debes ver: `-rw-r--r--  ... cashflow.db` ✅

---

### 5. Instala dependencias (2 minutos)
```bash
chmod +x setup_mac.sh run.sh
./setup_mac.sh
```

---

### 6. Migra la base de datos (30 segundos) ⭐
```bash
python3 migrate_database.py
```

Verás:
```
✅ Backup created: instance/cashflow-backup-20260103-183045.db
✅ card_id column added

📊 Current data:
   Variable expenses: 5  ← TUS GASTOS
   Fixed expenses paid: 2 ← TUS PAGOS

✅ Migration successful!
```

---

### 7. Ejecuta la app (5 segundos)
```bash
./run.sh
```

Abre: **http://localhost:8080**

✅ **Verás tus datos + nuevas funciones** ✅

---

## ⚡ COMANDO TODO-EN-UNO (Alternativa rápida)

**Copia y pega todo esto:**

```bash
cd /Users/takbraun/Developer/Cashflow-Optimizer && \
cp instance/cashflow.db ~/Desktop/BACKUP-3enero.db && \
echo "✅ Backup creado" && \
cd ~/Downloads && \
unzip -o cashflow-optimizer-v3-FINAL.zip && \
mv ~/Downloads/cashflow-optimizer ~/Developer/Cashflow-Optimizer-NEW && \
cd ~/Developer/Cashflow-Optimizer-NEW && \
cp ~/Desktop/BACKUP-3enero.db instance/cashflow.db && \
chmod +x setup_mac.sh run.sh && \
./setup_mac.sh && \
python3 migrate_database.py && \
./run.sh
```

---

## 🔄 OPCIONAL: Renombrar directorios

Después de verificar que todo funciona:

```bash
cd ~/Developer
mv Cashflow-Optimizer Cashflow-Optimizer-OLD
mv Cashflow-Optimizer-NEW Cashflow-Optimizer
cd Cashflow-Optimizer
./run.sh
```

---

## 🛡️ TIENES 3 BACKUPS

1. **Manual:** `~/Desktop/BACKUP-3enero.db`
2. **Automático:** `~/Developer/Cashflow-Optimizer-NEW/instance/cashflow-backup-FECHA.db`
3. **Directorio completo:** `~/Developer/Cashflow-Optimizer/` (versión vieja intacta)

**Imposible perder datos** ✅

---

## 🎯 VERIFICAR SI TIENES DATOS ANTES

Si quieres verificar cuántos datos tienes antes de migrar:

```bash
cd /Users/takbraun/Developer/Cashflow-Optimizer
python3 << 'EOF'
import sqlite3
conn = sqlite3.connect('instance/cashflow.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM variable_expense_log')
var = cursor.fetchone()[0]
cursor.execute('SELECT COUNT(*) FROM expense_payment')
fixed = cursor.fetchone()[0]
print(f'\n📊 Tus datos actuales:')
print(f'   Gastos variables: {var}')
print(f'   Gastos fijos pagados: {fixed}\n')
if var > 0 or fixed > 0:
    print('✅ Tienes datos - USA LA MIGRACIÓN')
else:
    print('⚠️  No tienes datos - Puedes empezar de cero si quieres')
conn.close()
EOF
```

---

## 📊 DESPUÉS DE LA MIGRACIÓN

Verifica que tus datos estén ahí:

```bash
cd ~/Developer/Cashflow-Optimizer-NEW
python3 << 'EOF'
from app import app, db, VariableExpenseLog, ExpensePayment
with app.app_context():
    var_expenses = VariableExpenseLog.query.all()
    fixed_payments = ExpensePayment.query.all()
    
    print('\n📊 Gastos Variables:')
    for e in var_expenses[:5]:
        print(f'   {e.expense_date.date()} - {e.category} - ${e.amount}')
    
    print('\n✅ Gastos Fijos Pagados:')
    for p in fixed_payments[:5]:
        print(f'   {p.payment_date.date()} - {p.expense.name} - ${p.amount}')
    print()
EOF
```

---

## ⏱️ TIEMPO TOTAL: ~3-4 minutos

- Backup: 30 seg
- Extracción: 1 min
- Setup: 2 min
- Migración: 30 seg
- Verificación: 30 seg

**¡Listo!** 🎉
