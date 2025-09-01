#!/bin/bash

# Script de Deploy para Digital Ocean
# Kommo-n8n Integration

set -e

echo "🚀 Iniciando deploy na Digital Ocean..."

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Função para log colorido
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

# Verificar se está rodando como root
if [[ $EUID -eq 0 ]]; then
   error "Este script não deve ser executado como root"
   exit 1
fi

# Atualizar sistema
log "📦 Atualizando sistema..."
sudo apt update && sudo apt upgrade -y

# Instalar dependências
log "🔧 Instalando dependências..."
sudo apt install -y python3 python3-pip python3-venv nginx certbot python3-certbot-nginx git curl

# Criar usuário para aplicação
log "👤 Configurando usuário da aplicação..."
if ! id "kommo-app" &>/dev/null; then
    sudo useradd -m -s /bin/bash kommo-app
    sudo usermod -aG sudo kommo-app
fi

# Criar diretório da aplicação
log "📁 Criando diretório da aplicação..."
sudo mkdir -p /var/www/api.previdas.com.br
sudo chown kommo-app:kommo-app /var/www/api.previdas.com.br

# Clonar repositório
log "📥 Clonando repositório..."
cd /var/www/api.previdas.com.br
if [ ! -d ".git" ]; then
    sudo -u kommo-app git clone https://github.com/RaquelFonsec/Kommo-n8n-integration.git .
else
    sudo -u kommo-app git pull origin main
fi

# Configurar ambiente virtual
log "🐍 Configurando ambiente virtual..."
sudo -u kommo-app python3 -m venv venv
sudo -u kommo-app venv/bin/pip install --upgrade pip
sudo -u kommo-app venv/bin/pip install -r requirements.txt

# Configurar arquivo .env
log "⚙️ Configurando variáveis de ambiente..."
if [ ! -f ".env" ]; then
    sudo -u kommo-app cp env.example .env
    warn "⚠️ Configure o arquivo .env com suas credenciais antes de continuar"
    echo "Arquivo .env criado em /var/www/api.previdas.com.br/.env"
    echo "Edite o arquivo com suas credenciais do Kommo e n8n"
    exit 1
fi

# Configurar Nginx
log "🌐 Configurando Nginx..."
sudo cp nginx.conf /etc/nginx/sites-available/api.previdas.com.br
sudo ln -sf /etc/nginx/sites-available/api.previdas.com.br /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Testar configuração do Nginx
sudo nginx -t

# Configurar SSL (se domínio estiver configurado)
log "🔒 Configurando SSL..."
if [ -n "$(dig +short api.previdas.com.br)" ]; then
    sudo certbot --nginx -d api.previdas.com.br --non-interactive --agree-tos --email admin@previdas.com.br
else
    warn "⚠️ Domínio api.previdas.com.br não resolvido. Configure o DNS primeiro."
fi

# Criar service do systemd
log "⚙️ Configurando service do systemd..."
sudo tee /etc/systemd/system/kommo-n8n-integration.service > /dev/null <<EOF
[Unit]
Description=Kommo-n8n Integration
After=network.target

[Service]
Type=simple
User=kommo-app
Group=kommo-app
WorkingDirectory=/var/www/api.previdas.com.br
Environment=PATH=/var/www/api.previdas.com.br/venv/bin
ExecStart=/var/www/api.previdas.com.br/venv/bin/python app/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Recarregar systemd e habilitar service
sudo systemctl daemon-reload
sudo systemctl enable kommo-n8n-integration

# Iniciar serviços
log "🚀 Iniciando serviços..."
sudo systemctl start nginx
sudo systemctl start kommo-n8n-integration

# Verificar status
log "📊 Verificando status dos serviços..."
sudo systemctl status nginx --no-pager
sudo systemctl status kommo-n8n-integration --no-pager

# Testar aplicação
log "🧪 Testando aplicação..."
sleep 5
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    log "✅ Aplicação funcionando corretamente!"
else
    error "❌ Aplicação não está respondendo"
    sudo journalctl -u kommo-n8n-integration -n 20
fi

log "🎉 Deploy concluído com sucesso!"
log "📋 Próximos passos:"
log "   1. Configure o webhook no Kommo: https://api.previdas.com.br/webhooks/kommo"
log "   2. Configure o n8n para enviar respostas para: https://api.previdas.com.br/send-response"
log "   3. Teste o fluxo completo"
log ""
log "📊 Logs da aplicação: sudo journalctl -u kommo-n8n-integration -f"
log "📊 Logs do Nginx: sudo tail -f /var/log/nginx/api.previdas.com.br.access.log"
