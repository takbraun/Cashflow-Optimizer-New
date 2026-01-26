#!/bin/bash
# Cash Flow Optimizer - Production Installation Script
# For Pop OS / Ubuntu Linux

set -e  # Exit on error

echo "=========================================="
echo "Cash Flow Optimizer - Production Setup"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get current user
CURRENT_USER=$(whoami)

echo -e "${YELLOW}Current user: $CURRENT_USER${NC}"
echo ""

# Ask for confirmation
read -p "Install to /var/www/cashflow-optimizer? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Installation cancelled."
    exit 1
fi

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo -e "${RED}ERROR: Do not run this script as root/sudo${NC}"
    echo "Run as regular user. The script will ask for sudo when needed."
    exit 1
fi

echo ""
echo "Step 1: Installing system dependencies..."
sudo apt update
sudo apt install -y python3 python3-pip python3-venv nginx

echo ""
echo "Step 2: Creating application directory..."
sudo mkdir -p /var/www/cashflow-optimizer
sudo chown $CURRENT_USER:www-data /var/www/cashflow-optimizer

echo ""
echo "Step 3: Copying application files..."
# Assuming script is run from the app directory
if [ -f "app.py" ]; then
    cp -r * /var/www/cashflow-optimizer/
    echo -e "${GREEN}✓ Files copied${NC}"
else
    echo -e "${RED}ERROR: app.py not found. Run this script from the app directory.${NC}"
    exit 1
fi

cd /var/www/cashflow-optimizer

echo ""
echo "Step 4: Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo ""
echo "Step 5: Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

echo ""
echo "Step 6: Initializing database..."
if [ ! -f "instance/cashflow.db" ]; then
    python3 init_db.py
    echo -e "${GREEN}✓ Database initialized${NC}"
else
    echo -e "${YELLOW}⚠ Database already exists, skipping initialization${NC}"
fi

echo ""
echo "Step 7: Running migrations..."
python3 migrate_liquidity_status.py 2>/dev/null || echo "Migration already applied"
python3 migrate_dual_balance.py 2>/dev/null || echo "Migration already applied"

echo ""
echo "Step 8: Creating log directory..."
mkdir -p logs
chmod 755 logs

echo ""
echo "Step 9: Setting permissions..."
sudo chown -R $CURRENT_USER:www-data /var/www/cashflow-optimizer
sudo chmod -R 755 /var/www/cashflow-optimizer
sudo chmod 660 instance/cashflow.db

echo ""
echo "Step 10: Creating systemd service..."
sudo tee /etc/systemd/system/cashflow-optimizer.service > /dev/null <<EOF
[Unit]
Description=Cash Flow Optimizer - Gunicorn WSGI Server
After=network.target

[Service]
User=$CURRENT_USER
Group=www-data
WorkingDirectory=/var/www/cashflow-optimizer
Environment="PATH=/var/www/cashflow-optimizer/venv/bin"

ExecStart=/var/www/cashflow-optimizer/venv/bin/gunicorn \\
    --config /var/www/cashflow-optimizer/gunicorn_config.py \\
    app:app

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✓ Systemd service created${NC}"

echo ""
echo "Step 11: Starting service..."
sudo systemctl daemon-reload
sudo systemctl enable cashflow-optimizer
sudo systemctl start cashflow-optimizer

# Wait a bit for service to start
sleep 2

if sudo systemctl is-active --quiet cashflow-optimizer; then
    echo -e "${GREEN}✓ Service started successfully${NC}"
else
    echo -e "${RED}✗ Service failed to start${NC}"
    echo "Check logs with: sudo journalctl -u cashflow-optimizer -n 50"
    exit 1
fi

echo ""
echo "Step 12: Configuring Nginx..."

# Get IP address
IP_ADDRESS=$(hostname -I | awk '{print $1}')

sudo tee /etc/nginx/sites-available/cashflow-optimizer > /dev/null <<EOF
server {
    listen 80;
    server_name $IP_ADDRESS localhost;

    access_log /var/log/nginx/cashflow-access.log;
    error_log /var/log/nginx/cashflow-error.log;

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /static {
        alias /var/www/cashflow-optimizer/static;
        expires 30d;
    }
}
EOF

# Enable site
sudo ln -sf /etc/nginx/sites-available/cashflow-optimizer /etc/nginx/sites-enabled/

# Test Nginx configuration
if sudo nginx -t; then
    echo -e "${GREEN}✓ Nginx configuration OK${NC}"
    sudo systemctl restart nginx
else
    echo -e "${RED}✗ Nginx configuration error${NC}"
    exit 1
fi

echo ""
echo "Step 13: Configuring firewall..."
if sudo ufw status | grep -q "Status: active"; then
    sudo ufw allow 'Nginx Full'
    echo -e "${GREEN}✓ Firewall configured${NC}"
else
    echo -e "${YELLOW}⚠ Firewall not active, skipping${NC}"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}Installation Complete!${NC}"
echo "=========================================="
echo ""
echo "Your application is now running at:"
echo -e "${GREEN}http://$IP_ADDRESS${NC}"
echo ""
echo "Useful commands:"
echo "  Status:  sudo systemctl status cashflow-optimizer"
echo "  Restart: sudo systemctl restart cashflow-optimizer"
echo "  Logs:    sudo journalctl -u cashflow-optimizer -f"
echo ""
echo "Next steps:"
echo "  1. Access the app in your browser"
echo "  2. Configure your cards and income"
echo "  3. (Optional) Set up SSL with: sudo certbot --nginx"
echo ""
