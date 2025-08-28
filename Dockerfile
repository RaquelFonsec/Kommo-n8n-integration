# Dockerfile para Kommo-n8n Integration
FROM python:3.11-slim

# Definir variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Instalar dependências do sistema
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        nginx \
        certbot \
        python3-certbot-nginx \
    && rm -rf /var/lib/apt/lists/*

# Criar usuário não-root
RUN useradd --create-home --shell /bin/bash app

# Definir diretório de trabalho
WORKDIR /app

# Copiar requirements primeiro (para cache do Docker)
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY . .

# Criar diretórios necessários
RUN mkdir -p logs && chown -R app:app /app

# Configurar Nginx
COPY nginx.conf /etc/nginx/sites-available/default
RUN ln -sf /etc/nginx/sites-available/default /etc/nginx/sites-enabled/

# Expor portas
EXPOSE 80 443 8000

# Script de inicialização
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Mudar para usuário não-root
USER app

# Comando padrão
ENTRYPOINT ["docker-entrypoint.sh"]
