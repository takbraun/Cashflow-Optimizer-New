# ⚡ SCRIPT CORREGIDO - CON NOMBRE CORRECTO DEL ZIP

## 🎯 EL ARCHIVO SE DESCARGÓ COMO: `File.zip`

---

## ⚡ COMANDO TODO-EN-UNO (CORREGIDO)

```bash
cd /Users/takbraun/Developer/Cashflow-Optimizer && \
cp instance/cashflow.db ~/Desktop/BACKUP-3enero.db && \
echo "✅ Backup creado en Desktop" && \
cd ~/Downloads && \
unzip -o File.zip && \
mv ~/Downloads/cashflow-optimizer ~/Developer/Cashflow-Optimizer-NEW && \
cd ~/Developer/Cashflow-Optimizer-NEW && \
cp ~/Desktop/BACKUP-3enero.db instance/cashflow.db && \
echo "✅ Base de datos copiada" && \
chmod +x setup_mac.sh run.sh && \
./setup_mac.sh && \
python3 migrate_database.py && \
./run.sh
```

---

## 📝 PASO A PASO (CORREGIDO)

### 1. Backup
```bash
cd /Users/takbraun/Developer/Cashflow-Optimizer
cp instance/cashflow.db ~/Desktop/BACKUP-3enero.db
ls -la ~/Desktop/BACKUP-3enero.db
```

### 2. Extrae (con nombre correcto)
```bash
cd ~/Downloads
unzip -o File.zip
```

### 3. Mueve a Developer
```bash
mv ~/Downloads/cashflow-optimizer ~/Developer/Cashflow-Optimizer-NEW
cd ~/Developer/Cashflow-Optimizer-NEW
```

### 4. Copia tu DB con datos
```bash
cp ~/Desktop/BACKUP-3enero.db instance/cashflow.db
ls -la instance/cashflow.db
```

### 5. Instala y migra
```bash
chmod +x setup_mac.sh run.sh
./setup_mac.sh
python3 migrate_database.py
```

### 6. Ejecuta
```bash
./run.sh
```

Abre: **http://localhost:8080**

---

## ✅ VERIFICACIÓN

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

📊 Current data:
   Variable expenses: 5  ← TUS DATOS
   Fixed expenses paid: 2 ← TUS DATOS

✅ Migration successful!
   You can now run: ./run.sh

🚀 Iniciando Cash Flow Optimizer...
 * Running on http://0.0.0.0:8080
```

---

## 🛡️ BACKUPS MÚLTIPLES

1. **Manual:** `~/Desktop/BACKUP-3enero.db`
2. **Automático:** `~/Developer/Cashflow-Optimizer-NEW/instance/cashflow-backup-FECHA.db`
3. **Directorio viejo:** `~/Developer/Cashflow-Optimizer/` (intacto)

---

## ⏱️ TIEMPO TOTAL: ~3 minutos

¡Listo! 🎉
