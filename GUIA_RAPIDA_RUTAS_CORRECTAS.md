# ⚡ GUÍA RÁPIDA - Rutas Correctas

## 🎯 TU INSTALACIÓN ACTUAL

```
/Developer/Cashflow-Cashflow-Optimizer/
```

---

## 🚀 ACTUALIZACIÓN PASO A PASO

### 1. Backup (30 segundos)
```bash
cd /Developer/Cashflow-Cashflow-Optimizer
cp instance/cashflow.db ~/Desktop/BACKUP-cashflow-3enero.db
```

### 2. Extrae nueva versión (1 minuto)
```bash
cd /Developer
unzip -o ~/Downloads/cashflow-optimizer-v3-CON-MIGRACION.zip
```

### 3. Copia tu DB con datos (10 segundos)
```bash
cd /Developer/cashflow-optimizer
cp ~/Desktop/BACKUP-cashflow-3enero.db instance/cashflow.db
```

### 4. Instala y migra (2 minutos)
```bash
chmod +x setup_mac.sh run.sh
./setup_mac.sh
python3 migrate_database.py
```

### 5. Ejecuta (5 segundos)
```bash
./run.sh
```

Abre: **http://localhost:8080**

---

## ✅ VERIFICACIÓN

Verás:
```
✅ Backup created: instance/cashflow-backup-20260103-xxx.db
✅ card_id column added

📊 Current data:
   Variable expenses: [tu número]
   Fixed expenses paid: [tu número]

✅ Migration successful!
```

Si ves esto → **Todo correcto** ✅

---

## 🔄 OPCIONAL: Renombrar directorio nuevo

Si quieres mantener el nombre original:

```bash
cd /Developer
mv Cashflow-Cashflow-Optimizer Cashflow-Cashflow-Optimizer-OLD
mv cashflow-optimizer Cashflow-Cashflow-Optimizer
cd Cashflow-Cashflow-Optimizer
./run.sh
```

---

## 🛡️ MÚLTIPLES BACKUPS

Tienes 3 backups de seguridad:
1. `~/Desktop/BACKUP-cashflow-3enero.db` (manual)
2. `instance/cashflow-backup-FECHA.db` (automático)
3. `/Developer/Cashflow-Cashflow-Optimizer-OLD/` (directorio completo)

**Imposible perder datos** ✅

---

## ⚡ RESUMEN ULTRA-RÁPIDO

```bash
cd /Developer/Cashflow-Cashflow-Optimizer && \
cp instance/cashflow.db ~/Desktop/BACKUP.db && \
cd /Developer && \
unzip -o ~/Downloads/cashflow-optimizer-v3-CON-MIGRACION.zip && \
cd cashflow-optimizer && \
cp ~/Desktop/BACKUP.db instance/cashflow.db && \
./setup_mac.sh && \
python3 migrate_database.py && \
./run.sh
```

Copia todo eso, pega en Terminal, presiona Enter.

---

**Total: ~3 minutos** ⏱️
