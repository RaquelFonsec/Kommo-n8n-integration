# 🔄 Kommo-n8n Integration



## 📋 Sobre o Projeto

Sistema de integração entre **Kommo CRM** e **n8n** para automação de atendimento via WhatsApp com agente inteligente. A aplicação atua como ponte entre o Kommo (que recebe mensagens do WhatsApp) e o n8n (que processa com IA), permitindo um fluxo automatizado de atendimento.

## 🎯 Funcionalidades

### 🤖 **Agente Inteligente Automatizado**
- **Primeira linha de atendimento**: Responde dúvidas simples e coleta informações
- **Pré-qualificação de leads**: Identifica leads com perfil adequado
- **Triagem automática**: Filtra leads relevantes vs. não relevantes
- **Escalonamento controlado**: Permite intervenção humana quando necessário

### 🔄 **Fluxo Completo**
1. **Cliente manda WhatsApp** → Kommo recebe
2. **Kommo dispara webhook** → Python processa
3. **Python envia para n8n** → IA processa e responde
4. **n8n retorna resposta** → Python envia para Kommo
5. **Kommo envia para WhatsApp** → Cliente recebe resposta

###  **Controle do Bot**
- **Pausar/Reativar**: Controle manual do bot por contato
- **Comandos especiais**: `#pausar`, `#voltar`, `#status`
- **Status em tempo real**: Verificação do estado do bot
- **Handoff suave**: Transição para vendedor humano

- Como o Vendedor Usa os Comandos no WhatsApp
Cenário Típico de Atendimento
1. Cliente inicia conversa:
👤 Cliente: "Olá, quero saber sobre o produto X"
🤖 Bot: "Olá! Sou o assistente virtual. Posso te ajudar com o produto X..."
👤 Cliente: "Preciso de mais detalhes"
🤖 Bot: "Claro! O produto X tem as seguintes características..."
👤 Cliente: "Quero falar com um vendedor"
�� Bot: "Vou transferir você para um vendedor especializado..."

Vendedor assume a conversa:
�� Vendedor: "#pausar"
�� Sistema: "🤖 Bot pausado. Vendedor assumindo conversa."

👤 Cliente: "Olá, ainda está aí?"
💼 Vendedor: "Olá! Sou o João, vendedor especializado. Como posso te ajudar?"
👤 Cliente: "Quero comprar o produto X"
💼 Vendedor: "Perfeito! Vou te passar todas as informações..."


Vendedor termina e reativa o bot:

💼 Vendedor: "Perfeito! Vou te enviar a proposta por email."
�� Cliente: "Obrigado!"
�� Vendedor: "#voltar"
🤖 Sistema: "�� Bot reativado. Assumindo atendimento automático."

👤 Cliente: "Tenho mais uma dúvida"
🤖 Bot: "Olá! Como posso te ajudar?"


Comandos Disponíveis
Comando	O que faz	Quando usar
#pausar	Pausa o bot	Quando quer assumir a conversa
#voltar	Reativa o bot	Quando termina o atendimento
#status	Mostra status	Para ver se o bot está ativo
#help	Mostra ajuda	Para ver todos os comandos

## 🏗️ Arquitetura

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   WhatsApp  │───▶│    Kommo    │───▶│    Python   │
│             │    │    CRM      │    │   Server    │
└─────────────┘    └─────────────┘    └─────────────┘
       ▲                   ▲                   │
       │                   │                   ▼
       │                   │            ┌─────────────┐
       │                   │            │     n8n     │
       │                   │            │   (IA)      │
       │                   │            └─────────────┘
       └───────────────────┴───────────────────┘
```

## 🌐 URLs de Produção

### **Servidor Principal:**
- **Base URL:** `https://dashboard.previdas.com.br/api/kommo-n8n`

### **Endpoints Principais:**
- **Webhook Kommo:** `https://dashboard.previdas.com.br/api/kommo-n8n/webhooks/kommo`
- **Resposta n8n:** `https://dashboard.previdas.com.br/api/kommo-n8n/send-response`
- **Controle Bot:** `https://dashboard.previdas.com.br/api/kommo-n8n/bot/command`
- **Status Bot:** `https://dashboard.previdas.com.br/api/kommo-n8n/bot/status/{contact_id}`
- **OAuth:** `https://dashboard.previdas.com.br/api/kommo-n8n/oauth/callback`

### **Configurações Externas:**
- **Kommo Webhook:** Configure para disparar em "Lead adicionado"
- **n8n Saída:** Configure para enviar respostas para o endpoint de resposta

## 📁 Estrutura do Projeto

```
kommo-n8n-integration/
├── app/                    # Código principal
│   ├── main.py            # Aplicação FastAPI
│   ├── models/            # Modelos Pydantic
│   ├── routes/            # Endpoints da API
│   ├── services/          # Serviços (Kommo, n8n)
│   └── utils/             # Utilitários
├── logs/                  # Logs da aplicação
├── .env                   # Configurações (não versionado)
├── env.example           # Exemplo de configuração
├── requirements.txt      # Dependências Python
└── README.md            # Este arquivo
```

## 🚀 Instalação e Configuração

### 1. **Pré-requisitos**
```bash
# Python 3.8+
python3 --version

# Git
git --version
```

### 2. **Clone e Setup**
```bash
# Clonar repositório
git clone https://github.com/RaquelFonsec/Kommo-n8n-integration.git
cd kommo-n8n-integration

# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

### 3. **Configuração do Ambiente**
```bash
# Copiar arquivo de exemplo
cp env.example .env

# Editar configurações
nano .env
```

### 4. **Variáveis de Ambiente**
```bash
# ===== CONFIGURAÇÕES KOMMO =====
KOMMO_CLIENT_ID=seu_client_id
KOMMO_CLIENT_SECRET=seu_client_secret
KOMMO_ACCESS_TOKEN=seu_access_token
KOMMO_BASE_URL=https://seu-dominio.kommo.com
KOMMO_ACCOUNT_ID=seu_account_id

# ===== CONFIGURAÇÕES N8N =====
N8N_WEBHOOK_URL=https://n8n-seu-dominio.com/webhook/seu-webhook
N8N_API_KEY=sua_api_key_n8n

# ===== CONFIGURAÇÕES APP =====
PORT=8000
HOST=0.0.0.0
DEBUG=true
ENVIRONMENT=development
```

##  Execução

### **Desenvolvimento**
```bash
# Ativar ambiente virtual
source venv/bin/activate

# Executar aplicação
python app/main.py
```

### **Produção**
```bash
# Usando uvicorn diretamente
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Usando systemd (recomendado)
sudo systemctl start kommo-n8n-integration
sudo systemctl enable kommo-n8n-integration
```

## 🌐 Endpoints da API

### ** Status e Saúde**
- `GET /` - Status da aplicação
- `GET /health` - Verificação de saúde
- `GET /config` - Configurações carregadas

### ** Webhooks**
- `POST /webhooks/kommo` - Recebe webhooks do Kommo
- `POST /send-response` - Recebe respostas do n8n

### ** Controle do Bot**
- `GET /bot/status/{contact_id}` - Status do bot para contato
- `POST /bot/pause/{contact_id}` - Pausar bot para contato
- `POST /bot/resume/{contact_id}` - Reativar bot para contato
- `POST /bot/command` - Comandos do bot via API

### ** OAuth**
- `GET /oauth/callback` - Callback OAuth do Kommo
- `GET /oauth/status` - Status da autenticação

##  Configuração Externa

### **Kommo CRM**
1. **Webhook**: Configure para `https://seu-dominio.com/webhooks/kommo`
2. **Eventos**: Adição de mensagem
3. **Autenticação**: OAuth2 configurado

### **n8n**
1. **Webhook de entrada**: `https://n8n-seu-dominio.com/webhook/seu-webhook`
2. **HTTP Request de saída**: `https://seu-dominio.com/send-response`
3. **Payload esperado**:
```json
{
  "conversation_id": "conv_123456",
  "contact_id": 789,
  "message_text": "Olá, preciso de uma perícia médica",
  "timestamp": "2024-08-27T14:30:00",
  "chat_type": "whatsapp"
}
```

##  Monitoramento

### **Logs**
- **Localização**: `logs/` diretório
- **Formato**: JSON estruturado
- **Rotação**: Automática diária

### **Métricas**
- **Webhooks recebidos**: Contador de mensagens
- **Respostas enviadas**: Contador de respostas
- **Erros**: Logs detalhados com emojis

### **Alertas**
- **n8n offline**: Notificação quando n8n não responde
- **Kommo erro**: Notificação de erros de API
- **Bot pausado**: Status de contatos com bot pausado

##  Desenvolvimento

### **Estrutura de Código**
```python
# Serviços principais
app/services/
├── kommo_service.py      # Integração com Kommo
├── n8n_service.py        # Integração com n8n
└── webhook_processor.py  # Processamento de webhooks

# Modelos de dados
app/models/
└── kommo_models.py       # Pydantic models

# Rotas da API
app/routes/
├── oauth.py             # Endpoints OAuth
└── webhooks.py          # Endpoints webhook
```

### **Padrões de Código**
- **Async/Await**: Todas as operações I/O são assíncronas
- **Logging estruturado**: Logs com emojis para fácil identificação
- **Tratamento de erros**: Try/catch em todas as operações críticas
- **Validação**: Pydantic para validação de dados

##  Segurança

### **Autenticação**
- **Kommo**: OAuth2 com refresh token
- **n8n**: API Key Bearer token
- **HTTPS**: Obrigatório em produção

### **Validação**
- **Input sanitization**: Todos os inputs são validados
- **Rate limiting**: Proteção contra spam
- **CORS**: Configurado para origens específicas

##  Deploy em Produção

### **1. Servidor**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip nginx

# Configurar nginx
sudo nano /etc/nginx/sites-available/kommo-n8n
```

### **2. Nginx Config**
```nginx
server {
    listen 80;
    server_name api.seudominio.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### **3. SSL/HTTPS**
```bash
# Certbot
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d api.seudominio.com
```

### **4. Systemd Service**
```ini
[Unit]
Description=Kommo-n8n Integration
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/kommo-n8n-integration
Environment=PATH=/path/to/kommo-n8n-integration/venv/bin
ExecStart=/path/to/kommo-n8n-integration/venv/bin/python app/main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

##  Troubleshooting

### **Problemas Comuns**

#### **n8n não responde**
```bash
# Verificar conectividade
curl -X GET https://n8n-seu-dominio.com

# Verificar logs
tail -f logs/app-$(date +%Y%m%d).log
```

#### **Kommo webhook não chega**
```bash
# Verificar endpoint
curl -X POST https://seu-dominio.com/webhooks/kommo \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'

# Verificar configuração no Kommo
```

#### **Erro de autenticação**
```bash
# Verificar tokens
curl -s "http://localhost:8000/config" | python -m json.tool

# Renovar token OAuth se necessário
```

### **Logs Úteis**
```bash
# Logs em tempo real
tail -f logs/app-$(date +%Y%m%d).log | grep -E "(ERROR|WARNING)"

# Logs de webhook
grep "webhook" logs/app-$(date +%Y%m%d).log

# Logs de n8n
grep "n8n" logs/app-$(date +%Y%m%d).log
```


### **Contatos**
- **Desenvolvedor**: Raquel Fonseca
- **Email**: [raquel.promptia@gmail.com.com]



## 📄 Licença

Este projeto é proprietário da **Previdas**. Todos os direitos reservados.
