# Cash Flow Optimizer - Guía de Instalación en Producción (Pop OS / Ubuntu)

## 📋 REQUISITOS PREVIOS

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar dependencias
sudo apt install -y python3 python3-pip python3-venv nginx
```

---

## 📁 PASO 1: PREPARAR DIRECTORIO DE PRODUCCIÓN

```bash
# Crear directorio de la aplicación
sudo mkdir -p /var/www/cashflow-optimizer
sudo chown $USER:$USER /var/www/cashflow-optimizer

# Copiar archivos
cd /var/www/cashflow-optimizer
# Aquí subes tu ZIP y lo extraes, o usas git clone
```

---

## 🐍 PASO 2: CONFIGURAR ENTORNO VIRTUAL Y DEPENDENCIAS

```bash
cd /var/www/cashflow-optimizer

# Crear entorno virtual
python3 -m venv venv

# Activar entorno virtual
source venv/bin/activate

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt

# Instalar Gunicorn (servidor WSGI para producción)
pip install gunicorn

# Verificar instalación
python3 -c "import flask; print('Flask OK')"
```

---

## 🗄️ PASO 3: CONFIGURAR BASE DE DATOS

```bash
# Inicializar base de datos
python3 init_db.py

# Ejecutar migraciones
python3 migrate_liquidity_status.py
python3 migrate_dual_balance.py

# Verificar que la DB existe
ls -lh instance/cashflow.db
```

---

## ⚙️ PASO 4: CREAR ARCHIVO DE CONFIGURACIÓN GUNICORN

```bash
# Crear archivo de configuración
nano /var/www/cashflow-optimizer/gunicorn_config.py
```

**Contenido de gunicorn_config.py:**
```python
import multiprocessing

# Dirección y puerto
bind = "127.0.0.1:8080"

# Número de workers (2-4 x NUM_CORES)
workers = multiprocessing.cpu_count() * 2 + 1

# Tipo de workers
worker_class = "sync"

# Timeout
timeout = 120

# Logging
accesslog = "/var/www/cashflow-optimizer/logs/access.log"
errorlog = "/var/www/cashflow-optimizer/logs/error.log"
loglevel = "info"

# Proceso
daemon = False
pidfile = "/var/www/cashflow-optimizer/gunicorn.pid"
```

```bash
# Crear directorio de logs
mkdir -p /var/www/cashflow-optimizer/logs
```

---

## 🔧 PASO 5: CREAR SERVICIO SYSTEMD

```bash
sudo nano /etc/systemd/system/cashflow-optimizer.service
```

**Contenido del archivo:**
```ini
[Unit]
Description=Cash Flow Optimizer - Gunicorn WSGI Server
After=network.target

[Service]
User=YOUR_USERNAME
Group=www-data
WorkingDirectory=/var/www/cashflow-optimizer
Environment="PATH=/var/www/cashflow-optimizer/venv/bin"

ExecStart=/var/www/cashflow-optimizer/venv/bin/gunicorn \
    --config /var/www/cashflow-optimizer/gunicorn_config.py \
    app:app

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**⚠️ IMPORTANTE: Reemplaza `YOUR_USERNAME` con tu usuario actual:**
```bash
# Para ver tu usuario:
whoami

# Edita el archivo y reemplaza YOUR_USERNAME con el resultado
sudo nano /etc/systemd/system/cashflow-optimizer.service
```

---

## 🚀 PASO 6: INICIAR SERVICIO

```bash
# Recargar systemd
sudo systemctl daemon-reload

# Habilitar servicio (inicia automáticamente al bootear)
sudo systemctl enable cashflow-optimizer

# Iniciar servicio
sudo systemctl start cashflow-optimizer

# Verificar estado
sudo systemctl status cashflow-optimizer

# Ver logs si hay problemas
sudo journalctl -u cashflow-optimizer -f
```

---

## 🌐 PASO 7: CONFIGURAR NGINX

```bash
sudo nano /etc/nginx/sites-available/cashflow-optimizer
```

**Contenido del archivo:**
```nginx
server {
    listen 80;
    server_name tu-dominio.com;  # O tu IP: 192.168.1.100

    # Logs
    access_log /var/log/nginx/cashflow-access.log;
    error_log /var/log/nginx/cashflow-error.log;

    # Aumentar tamaño máximo de subida (para archivos grandes)
    client_max_body_size 10M;

    location / {
        # Proxy a Gunicorn
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Static files (opcional, si usas archivos estáticos)
    location /static {
        alias /var/www/cashflow-optimizer/static;
        expires 30d;
    }
}
```

**Activar sitio:**
```bash
# Crear symlink
sudo ln -s /etc/nginx/sites-available/cashflow-optimizer /etc/nginx/sites-enabled/

# Verificar configuración
sudo nginx -t

# Si todo está OK, reiniciar Nginx
sudo systemctl restart nginx

# Verificar estado
sudo systemctl status nginx
```

---

## 🔒 PASO 8: CONFIGURAR SSL/HTTPS (OPCIONAL PERO RECOMENDADO)

### **Opción A: Con Dominio (Let's Encrypt - GRATIS)**

```bash
# Instalar Certbot
sudo apt install certbot python3-certbot-nginx -y

# Obtener certificado (reemplaza tu-dominio.com)
sudo certbot --nginx -d tu-dominio.com

# Certbot configurará automáticamente HTTPS
# El certificado se renovará automáticamente
```

### **Opción B: Sin Dominio (Auto-firmado para red local)**

```bash
# Crear certificado auto-firmado
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/cashflow.key \
    -out /etc/ssl/certs/cashflow.crt

# Actualizar configuración de Nginx
sudo nano /etc/nginx/sites-available/cashflow-optimizer
```

**Agregar al archivo:**
```nginx
server {
    listen 443 ssl;
    server_name tu-ip-o-hostname;

    ssl_certificate /etc/ssl/certs/cashflow.crt;
    ssl_certificate_key /etc/ssl/private/cashflow.key;

    # ... resto de la configuración igual
}

# Redirigir HTTP a HTTPS
server {
    listen 80;
    server_name tu-ip-o-hostname;
    return 301 https://$server_name$request_uri;
}
```

---

## 🔥 PASO 9: CONFIGURAR FIREWALL

```bash
# Permitir HTTP y HTTPS
sudo ufw allow 'Nginx Full'

# O si solo quieres HTTP:
sudo ufw allow 'Nginx HTTP'

# Verificar firewall
sudo ufw status
```

---

## ✅ PASO 10: VERIFICAR QUE TODO FUNCIONA

### **Verificar servicios:**
```bash
# Gunicorn
sudo systemctl status cashflow-optimizer

# Nginx
sudo systemctl status nginx

# Ver logs en tiempo real
sudo journalctl -u cashflow-optimizer -f
```

### **Probar desde navegador:**
```
http://tu-ip-o-dominio
# O si configuraste HTTPS:
https://tu-ip-o-dominio
```

---

## 🔧 COMANDOS ÚTILES DE ADMINISTRACIÓN

### **Reiniciar aplicación:**
```bash
sudo systemctl restart cashflow-optimizer
```

### **Ver logs:**
```bash
# Logs de la aplicación
sudo journalctl -u cashflow-optimizer --since today

# Logs de Gunicorn
tail -f /var/www/cashflow-optimizer/logs/error.log

# Logs de Nginx
tail -f /var/log/nginx/cashflow-error.log
```

### **Detener aplicación:**
```bash
sudo systemctl stop cashflow-optimizer
```

### **Actualizar aplicación:**
```bash
# 1. Detener servicio
sudo systemctl stop cashflow-optimizer

# 2. Activar entorno virtual
cd /var/www/cashflow-optimizer
source venv/bin/activate

# 3. Actualizar código (git pull o copiar archivos nuevos)
# ...

# 4. Instalar nuevas dependencias si hay
pip install -r requirements.txt

# 5. Ejecutar migraciones si hay
python3 migrate_xxx.py

# 6. Reiniciar servicio
sudo systemctl start cashflow-optimizer
```

---

## 🛡️ SEGURIDAD ADICIONAL

### **1. Restringir permisos:**
```bash
# Permisos de directorio
sudo chown -R $USER:www-data /var/www/cashflow-optimizer
sudo chmod -R 755 /var/www/cashflow-optimizer

# Base de datos solo lectura/escritura para owner
chmod 600 /var/www/cashflow-optimizer/instance/cashflow.db
```

### **2. Configurar rate limiting en Nginx:**
```nginx
# Agregar al inicio del archivo de Nginx:
limit_req_zone $binary_remote_addr zone=cashflow_limit:10m rate=10r/s;

# Dentro del bloque location /:
limit_req zone=cashflow_limit burst=20;
```

### **3. Backups automáticos:**
```bash
# Crear script de backup
nano /var/www/cashflow-optimizer/backup.sh
```

**Contenido:**
```bash
#!/bin/bash
BACKUP_DIR="/var/backups/cashflow"
mkdir -p $BACKUP_DIR
DATE=$(date +%Y%m%d_%H%M%S)

# Backup de base de datos
cp /var/www/cashflow-optimizer/instance/cashflow.db \
   $BACKUP_DIR/cashflow_$DATE.db

# Mantener solo últimos 30 días
find $BACKUP_DIR -name "cashflow_*.db" -mtime +30 -delete

echo "Backup completed: cashflow_$DATE.db"
```

```bash
# Dar permisos de ejecución
chmod +x /var/www/cashflow-optimizer/backup.sh

# Agregar a cron (ejecutar diario a las 2 AM)
crontab -e

# Agregar línea:
0 2 * * * /var/www/cashflow-optimizer/backup.sh >> /var/log/cashflow-backup.log 2>&1
```

---

## 🚨 TROUBLESHOOTING

### **Error: "Connection refused"**
```bash
# Verificar que Gunicorn está corriendo
sudo systemctl status cashflow-optimizer

# Verificar puerto
sudo netstat -tlnp | grep 8080
```

### **Error: "502 Bad Gateway"**
```bash
# Verificar logs de Nginx
tail -f /var/log/nginx/cashflow-error.log

# Verificar logs de Gunicorn
tail -f /var/www/cashflow-optimizer/logs/error.log
```

### **Error de permisos en base de datos**
```bash
# Verificar permisos
ls -l /var/www/cashflow-optimizer/instance/cashflow.db

# Corregir si es necesario
sudo chown $USER:www-data /var/www/cashflow-optimizer/instance/cashflow.db
chmod 660 /var/www/cashflow-optimizer/instance/cashflow.db
```

---

## 📊 MONITOREO

### **Ver uso de recursos:**
```bash
# CPU y memoria de Gunicorn
ps aux | grep gunicorn

# Espacio en disco
df -h

# Tamaño de base de datos
du -h /var/www/cashflow-optimizer/instance/cashflow.db
```

---

¡Listo! Tu aplicación ahora está corriendo en producción de manera profesional y segura. 🎉
