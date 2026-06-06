#!/bin/bash
# setup_hetzner.sh — Prontuario Medico no Hetzner (Ubuntu 24.04)
# Rodar como root: bash setup_hetzner.sh
#
# Servicos criados:
#   prontuario-sync.service   — baixa banco do Drive a cada 5 min
#   prontuario-medico.service — app web para o medico (porta 8553)
#
# Acesso medico: http://167.233.18.218

set -e

IP="167.233.18.218"
APP_DIR="/opt/prontuario"
APP_USER="prontuario"
REPO="https://github.com/sanicolauvix/prontuarioMedico.git"
PORTA_MEDICO="8553"

echo ""
echo "========================================"
echo "  PRONTUARIO MEDICO — Setup Hetzner"
echo "========================================"
echo ""

# ----------------------------------------
# 1. Atualizar sistema
# ----------------------------------------
echo "[1/8] Atualizando sistema..."
apt-get update -q
apt-get upgrade -y -q
apt-get install -y -q \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-pip \
    git \
    nginx \
    ufw \
    curl \
    build-essential \
    libssl-dev \
    libffi-dev \
    libpoppler-cpp-dev \
    poppler-utils \
    libgl1 \
    libglib2.0-0
echo "[1/8] OK"

# ----------------------------------------
# 2. Criar usuario dedicado
# ----------------------------------------
echo "[2/8] Criando usuario '$APP_USER'..."
if ! id "$APP_USER" &>/dev/null; then
    useradd -m -s /bin/bash "$APP_USER"
fi
echo "[2/8] OK"

# ----------------------------------------
# 3. Clonar repositorio
# ----------------------------------------
echo "[3/8] Clonando repositorio..."
if [ -d "$APP_DIR/.git" ]; then
    echo "  Repositorio ja existe — fazendo git pull..."
    cd "$APP_DIR" && git pull origin master
else
    git clone "$REPO" "$APP_DIR"
fi
chown -R "$APP_USER":"$APP_USER" "$APP_DIR"
echo "[3/8] OK"

# ----------------------------------------
# 4. Virtualenv + dependencias
# ----------------------------------------
echo "[4/8] Criando virtualenv e instalando dependencias..."
cd "$APP_DIR"
sudo -u "$APP_USER" python3.11 -m venv .venv
sudo -u "$APP_USER" .venv/bin/pip install --upgrade pip -q
sudo -u "$APP_USER" .venv/bin/pip install \
    flet==0.28.2 \
    google-auth \
    google-auth-httplib2 \
    google-auth-oauthlib \
    google-api-python-client \
    requests \
    anthropic \
    httpx \
    repath \
    pdfplumber \
    pypdfium2 \
    pypdf \
    opencv-python-headless \
    -q
echo "[4/8] OK"

# ----------------------------------------
# 5. Criar pastas necessarias
# ----------------------------------------
echo "[5/8] Criando pastas..."
sudo -u "$APP_USER" mkdir -p "$APP_DIR/dados"
sudo -u "$APP_USER" mkdir -p "$APP_DIR/logs"
sudo -u "$APP_USER" mkdir -p "$APP_DIR/temp"
sudo -u "$APP_USER" mkdir -p "$APP_DIR/assets/fotos_receitas"
sudo -u "$APP_USER" mkdir -p "$APP_DIR/assets/notas_fiscais"
sudo -u "$APP_USER" mkdir -p "$APP_DIR/assets/compras"
sudo -u "$APP_USER" mkdir -p "$APP_DIR/assets/cache_fotos"
echo "[5/8] OK"

# ----------------------------------------
# 6. Servico: sync do Drive
# ----------------------------------------
echo "[6/8] Configurando servico de sync Drive..."
cat > /etc/systemd/system/prontuario-sync.service << EOF
[Unit]
Description=Prontuario — Sync banco do Google Drive
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$APP_USER
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/.venv/bin/python drive_sync_server.py
Restart=always
RestartSec=30
StandardOutput=append:$APP_DIR/logs/drive_sync.log
StandardError=append:$APP_DIR/logs/drive_sync_error.log
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# ----------------------------------------
# 7. Servico: app web do medico
# ----------------------------------------
echo "[7/8] Configurando servico do app medico..."
cat > /etc/systemd/system/prontuario-medico.service << EOF
[Unit]
Description=Prontuario Medico — Visao Web do Medico
After=network.target prontuario-sync.service

[Service]
Type=simple
User=$APP_USER
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/.venv/bin/python main_medico.py
Restart=always
RestartSec=5
StandardOutput=append:$APP_DIR/logs/medico.log
StandardError=append:$APP_DIR/logs/medico_error.log
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable prontuario-sync
systemctl enable prontuario-medico
echo "[6/8] e [7/8] OK"

# ----------------------------------------
# 8. Nginx
# ----------------------------------------
echo "[8/8] Configurando nginx..."
cat > /etc/nginx/sites-available/prontuario-medico << EOF
server {
    listen 80;
    server_name $IP;

    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:$PORTA_MEDICO;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_read_timeout 86400;
    }
}
EOF

ln -sf /etc/nginx/sites-available/prontuario-medico /etc/nginx/sites-enabled/prontuario-medico
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable nginx
echo "[8/8] OK"

# ----------------------------------------
# Firewall
# ----------------------------------------
echo "Configurando firewall..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow http
ufw --force enable
echo "Firewall OK"

# ----------------------------------------
# Resumo
# ----------------------------------------
echo ""
echo "========================================"
echo "  Setup concluido!"
echo "========================================"
echo ""
echo "  PROXIMO PASSO OBRIGATORIO (manual):"
echo ""
echo "  1. Copiar credenciais Google para o servidor:"
echo "     scp mycreds.json root@$IP:$APP_DIR/mycreds.json"
echo "     chown $APP_USER:$APP_USER $APP_DIR/mycreds.json"
echo "     chmod 600 $APP_DIR/mycreds.json"
echo ""
echo "  2. Iniciar os servicos:"
echo "     systemctl start prontuario-sync"
echo "     systemctl start prontuario-medico"
echo "     systemctl start nginx"
echo ""
echo "  3. Verificar status:"
echo "     systemctl status prontuario-sync"
echo "     systemctl status prontuario-medico"
echo ""
echo "  4. Acompanhar logs:"
echo "     tail -f $APP_DIR/logs/drive_sync.log"
echo "     tail -f $APP_DIR/logs/medico.log"
echo ""
echo "  Acesso medico: http://$IP"
echo ""
