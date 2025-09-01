#!/bin/bash

# Script de Deploy Docker para Digital Ocean
# Kommo-n8n Integration

set -e

echo "🐳 Iniciando deploy Docker na Digital Ocean..."

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Verificar se Docker está instalado
check_docker() {
    if ! command -v docker &> /dev/null; then
        error "Docker não está instalado"
        log "Instalando Docker..."
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        sudo usermod -aG docker $USER
        rm get-docker.sh
        warn "⚠️ Faça logout e login novamente para aplicar as permissões do Docker"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose não está instalado"
        log "Instalando Docker Compose..."
        sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
    fi
}

# Atualizar sistema
update_system() {
    log "📦 Atualizando sistema..."
    sudo apt update && sudo apt upgrade -y
}

# Instalar dependências
install_dependencies() {
    log "🔧 Instalando dependências..."
    sudo apt install -y curl git certbot python3-certbot-nginx
}

# Configurar domínio
setup_domain() {
    log "🌐 Configurando domínio..."
    
    if [ -z "$DOMAIN" ]; then
        read -p "Digite o domínio (ex: api.previdas.com.br): " DOMAIN
    fi
    
    # Verificar se domínio resolve
    if ! dig +short $DOMAIN | grep -q .; then
        warn "⚠️ Domínio $DOMAIN não resolve. Configure o DNS primeiro."
        warn "   Aponte para o IP: $(curl -s ifconfig.me)"
    fi
}

# Configurar SSL
setup_ssl() {
    log "🔒 Configurando SSL..."
    
    if [ -n "$DOMAIN" ]; then
        # Criar diretório para certificados
        sudo mkdir -p /etc/letsencrypt/live/$DOMAIN
        
        # Tentar obter certificado
        if sudo certbot certonly --standalone -d $DOMAIN --non-interactive --agree-tos --email admin@previdas.com.br; then
            log "✅ Certificado SSL obtido com sucesso!"
            
            # Copiar certificados para volume Docker
            sudo mkdir -p ssl
            sudo cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem ssl/
            sudo cp /etc/letsencrypt/live/$DOMAIN/privkey.pem ssl/
            sudo chown -R $USER:$USER ssl/
        else
            warn "⚠️ Não foi possível obter certificado SSL. Continuando sem HTTPS..."
        fi
    fi
}

# Configurar arquivo .env
setup_env() {
    log "⚙️ Configurando variáveis de ambiente..."
    
    if [ ! -f ".env" ]; then
        cp env.example .env
        warn "⚠️ Configure o arquivo .env com suas credenciais antes de continuar"
        echo ""
        echo "📝 Variáveis necessárias no .env:"
        echo "   KOMMO_CLIENT_ID=sua_client_id"
        echo "   KOMMO_CLIENT_SECRET=sua_client_secret"
        echo "   KOMMO_REDIRECT_URI=https://$DOMAIN/auth/callback"
        echo "   KOMMO_REFRESH_TOKEN=seu_refresh_token"
        echo "   N8N_WEBHOOK_URL=https://n8n-n8n.eanhw2.easypanel.host/webhook/serena"
        echo "   N8N_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        echo ""
        echo "Arquivo .env criado. Edite com suas credenciais e execute novamente."
        exit 1
    fi
}

# Construir e executar containers
deploy_containers() {
    log "🐳 Construindo e executando containers..."
    
    # Parar containers existentes
    docker-compose -f docker-compose.prod.yml down 2>/dev/null || true
    
    # Construir imagem
    log "🔨 Construindo imagem Docker..."
    docker-compose -f docker-compose.prod.yml build --no-cache
    
    # Executar containers
    log "🚀 Iniciando containers..."
    docker-compose -f docker-compose.prod.yml up -d
    
    # Aguardar inicialização
    log "⏳ Aguardando inicialização..."
    sleep 30
}

# Verificar status
check_status() {
    log "📊 Verificando status dos containers..."
    
    # Status dos containers
    docker-compose -f docker-compose.prod.yml ps
    
    # Testar aplicação
    log "🧪 Testando aplicação..."
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log "✅ Aplicação funcionando corretamente!"
    else
        error "❌ Aplicação não está respondendo"
        docker-compose -f docker-compose.prod.yml logs app
    fi
    
    # Testar Nginx
    if curl -f http://localhost > /dev/null 2>&1; then
        log "✅ Nginx funcionando corretamente!"
    else
        error "❌ Nginx não está respondendo"
        docker-compose -f docker-compose.prod.yml logs nginx
    fi
}

# Configurar firewall
setup_firewall() {
    log "🔥 Configurando firewall..."
    sudo ufw allow 22/tcp
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    sudo ufw --force enable
}

# Configurar renovação automática SSL
setup_ssl_renewal() {
    log "🔄 Configurando renovação automática SSL..."
    
    # Criar script de renovação
    sudo tee /usr/local/bin/renew-ssl.sh > /dev/null <<EOF
#!/bin/bash
certbot renew --quiet
docker-compose -f /root/kommo-n8n-integration/docker-compose.prod.yml restart nginx
EOF
    
    sudo chmod +x /usr/local/bin/renew-ssl.sh
    
    # Adicionar ao crontab
    (crontab -l 2>/dev/null; echo "0 12 * * * /usr/local/bin/renew-ssl.sh") | crontab -
}

# Main execution
main() {
    log "🚀 Iniciando deploy Docker..."
    
    # Verificar se está rodando como root
    if [[ $EUID -eq 0 ]]; then
        error "Este script não deve ser executado como root"
        exit 1
    fi
    
    # Executar etapas
    check_docker
    update_system
    install_dependencies
    setup_domain
    setup_env
    setup_ssl
    deploy_containers
    check_status
    setup_firewall
    setup_ssl_renewal
    
    log "🎉 Deploy Docker concluído com sucesso!"
    log ""
    log "📋 URLs da aplicação:"
    log "   🌐 HTTP: http://$DOMAIN"
    log "   🔒 HTTPS: https://$DOMAIN"
    log "   📚 Docs: https://$DOMAIN/docs"
    log "   🏥 Health: https://$DOMAIN/health"
    log ""
    log "📋 Webhooks para configurar:"
    log "   📥 Kommo → https://$DOMAIN/webhooks/kommo"
    log "   📤 n8n → https://$DOMAIN/send-response"
    log ""
    log "📊 Comandos úteis:"
    log "   📋 Status: docker-compose -f docker-compose.prod.yml ps"
    log "   📊 Logs: docker-compose -f docker-compose.prod.yml logs -f"
    log "   🔄 Restart: docker-compose -f docker-compose.prod.yml restart"
    log "   🛑 Stop: docker-compose -f docker-compose.prod.yml down"
}

# Executar main
main "$@"
