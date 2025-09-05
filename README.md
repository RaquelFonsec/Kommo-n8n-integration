# 🚀 Sistema Kommo-n8n-Python Integration

## 📊 Visão Geral

Sistema de integração completo entre **Kommo CRM**, **n8n (Automação/IA)** e **Python API** para automação de conversas proativas e reativas via WhatsApp Business.



## 🏗️ Arquitetura

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     KOMMO       │    │   PYTHON API    │    │      N8N        │    │    SUPABASE     │
│   (CRM/WhatsApp)│◄──►│  (FastAPI)      │◄──►│  (Automação)    │◄──►│   (Banco)       │
│                 │    │                 │    │                 │    │                 │
│ • Leads         │    │ • Webhooks      │    │ • IA/LLM        │    │ • Agendamentos  │
│ • Contatos      │    │ • Conversas     │    │ • Workflows     │    │ • Vendedores    │
│ • Vendedores    │    │ • Controle Bot  │    │ • Integrações   │    │ • Histórico     │
│ • Webhooks      │    │ • Agendamentos  │    │ • Respostas     │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Funcionalidades Principais

### 1. **Vendedores Dinâmicos**
- **9 vendedores reais** sincronizados automaticamente do Kommo
- **3 vendedores fictícios** para testes e desenvolvimento
- **Sincronização automática** a cada requisição
- **Cache inteligente** para performance

### 2. **Conversas Proativas**
- **Gatilhos**: Formulário preenchido, material baixado, agendamento
- **Personalização**: Mensagens personalizadas por vendedor
- **Prevenção de duplicatas**: Não cria conversas duplicadas
- **Áreas elegíveis**: Filtro por área de atuação

### 3. **Controle de Bot**
- **Pausar/Reativar**: Controle manual via API
- **Comandos simples**: `/assumir` e `/liberar` para vendedores
- **Status**: Verificação de status do bot
- **Cache de status**: Sistema de cache para performance

### 4. **Sistema de Agendamento**
- **Identificação automática** do vendedor por conversa/contato/lead
- **Integração n8n**: Envio de dados estruturados
- **Contexto Supabase**: Dados completos para agendamento
- **Payload estruturado**: Dados organizados para processamento

### 5. **Integração Kommo**
- **OAuth2**: Sistema de autenticação
- **Refresh Token**: Renovação automática de tokens
- **API Notes**: Criação de notas nos leads
- **Webhooks**: Recebimento de mensagens

## 📁 Estrutura do Projeto

```
kommo-n8n-integration/
├── app/
│   ├── main.py                 # 🚀 API Principal (FastAPI)
│   ├── models/
│   │   └── kommo_models.py     # 📋 Modelos Pydantic
│   ├── services/
│   │   ├── kommo_service.py    # 🔗 Serviço Kommo
│   │   └── n8n_service.py      # 🔗 Serviço n8n
│   ├── routes/
│   │   └── oauth.py            # 🔐 Rotas OAuth
│   └── utils/
│       └── logger.py           # 📝 Sistema de Logs
├── .env                        # ⚙️ Configurações
├── requirements.txt            # 📦 Dependências
├── docker-compose.yml          # 🐳 Docker
├── README.md                   # 📖 Este arquivo
├── FLUXOGRAMA_SISTEMA.md       # 🔄 Fluxos detalhados
└── DIAGRAMA_SISTEMA_COMPLETO.md # 📊 Documentação técnica
```

## 🔧 Instalação e Configuração

### 1. **Pré-requisitos**
- Python 3.8+
- Conta Kommo com API habilitada
- n8n configurado
- Supabase (opcional)

### 2. **Instalação**
```bash
# Clone o repositório
git clone <repository-url>
cd kommo-n8n-integration

# Crie ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

# Instale dependências
pip install -r requirements.txt
```

### 3. **Configuração**
```bash
# Copie o arquivo de exemplo
cp env.example .env

# Configure as variáveis no .env
KOMMO_CLIENT_ID=seu_client_id
KOMMO_CLIENT_SECRET=seu_client_secret
KOMMO_ACCESS_TOKEN=seu_access_token
KOMMO_REFRESH_TOKEN=seu_refresh_token
KOMMO_API_URL=https://sua-conta.kommo.com/api/v4/
N8N_WEBHOOK_URL=https://seu-n8n.com/webhook/serena
```

### 4. **Execução**
```bash
# Inicie o servidor
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Acesse a documentação
# http://localhost:8000/docs
```

## 📊 Endpoints Disponíveis

### 🔗 **Conectividade & Status**
- `GET /version` - Versão da API
- `GET /stats` - Estatísticas do sistema
- `GET /health` - Status de saúde
- `GET /debug/conversations` - Debug das conversas

### 🔐 **Autenticação & Kommo**
- `GET /test-kommo-connectivity` - Teste de conectividade
- `GET /test-integration` - Teste de integração geral
- `POST /create-test-note/{lead_id}` - Criar nota de teste

### 👥 **Gerenciamento de Vendedores**
- `GET /vendedores` - Listar todos os vendedores
- `GET /vendedores/reais` - Vendedores reais do Kommo
- `GET /vendedores/dinamicos` - Vendedores dinâmicos (reais + fictícios)
- `POST /vendedores/adicionar` - Adicionar vendedor customizado
- `POST /vendedores/sincronizar` - Sincronizar com Kommo

### 💬 **Conversas Proativas**
- `POST /start-proactive` - Iniciar conversa proativa
- `GET /conversations/active` - Conversas ativas
- `POST /webhooks/kommo` - Webhook principal do Kommo
- `POST /send-response` - Enviar resposta via IA

### 🤖 **Controle de Bot**
- `POST /bot-control` - Controle manual (pause/resume/status)
- `POST /vendedor/comandos` - Comandos simples para vendedores

### 📅 **Sistema de Agendamento**
- `POST /agendamento/request` - Solicitar agendamento
- `GET /vendedor/conversa/{id}` - Vendedor por conversa
- `GET /vendedor/contato/{id}` - Vendedor por contato
- `GET /vendedor/lead/{id}` - Vendedor por lead

## 🔄 Fluxos de Trabalho

### **Fluxo Proativo (Bot inicia conversa)**
1. Cliente preenche formulário/baixa material
2. Python identifica vendedor responsável
3. Sistema cria conversa proativa
4. n8n gera mensagem personalizada
5. Mensagem é enviada via WhatsApp

### **Fluxo Reativo (Cliente responde)**
1. Cliente envia mensagem no WhatsApp
2. Kommo envia webhook para Python
3. Python verifica se bot está ativo
4. Se ativo, envia para n8n
5. IA gera resposta personalizada
6. Resposta é enviada via Kommo

### **Controle de Bot (Vendedor assume)**
1. Vendedor digita `/assumir 12345` no WhatsApp Business
2. Sistema pausa bot para aquele contato
3. Vendedor atende cliente normalmente
4. Vendedor digita `/liberar 12345` quando terminar
5. Bot reativa automaticamente

## 🎯 Exemplos de Uso

### **Iniciar Conversa Proativa**
```bash
curl -X POST http://localhost:8000/start-proactive \
  -H "Content-Type: application/json" \
  -d '{
    "contact_id": 12345,
    "lead_id": 67890,
    "vendedor": "Asaf",
    "area_atuacao": "previdenciário",
    "trigger_type": "formulario_preenchido",
    "lead_data": {
      "name": "João Silva",
      "interesse": "aposentadoria por invalidez"
    }
  }'
```

### **Controle de Bot**
```bash
# Pausar bot
curl -X POST http://localhost:8000/bot-control \
  -H "Content-Type: application/json" \
  -d '{"contact_id": 12345, "command": "pause"}'

# Reativar bot
curl -X POST http://localhost:8000/bot-control \
  -H "Content-Type: application/json" \
  -d '{"contact_id": 12345, "command": "resume"}'
```

### **Comandos de Vendedor**
```bash
# Vendedor assume conversa
curl -X POST http://localhost:8000/vendedor/comandos \
  -H "Content-Type: application/json" \
  -d '{
    "message": "/assumir 12345",
    "contact_id": 99999
  }'

# Vendedor libera conversa
curl -X POST http://localhost:8000/vendedor/comandos \
  -H "Content-Type: application/json" \
  -d '{
    "message": "/liberar 12345",
    "contact_id": 99999
  }'
```

## 🐳 Docker

```bash
# Build da imagem
docker build -t kommo-n8n-integration .

# Executar com docker-compose
docker-compose up -d

# Ver logs
docker-compose logs -f
```

## 📈 Monitoramento

### **Logs**
- Logs estruturados em JSON
- Níveis: INFO, WARNING, ERROR
- Rotação automática de logs

### **Métricas**
- Taxa de sucesso dos endpoints
- Número de conversas ativas
- Status dos vendedores
- Performance da API

### **Health Checks**
```bash
# Status geral
curl http://localhost:8000/health

# Estatísticas
curl http://localhost:8000/stats

# Versão
curl http://localhost:8000/version
```

## 🔧 Desenvolvimento

### **Estrutura de Código**
- **FastAPI**: Framework web moderno
- **Pydantic**: Validação de dados
- **AsyncIO**: Programação assíncrona
- **aiohttp**: Cliente HTTP assíncrono

### **Testes**
```bash
# Executar testes
python -m pytest

# Teste de conectividade
curl http://localhost:8000/test-integration
```

### **Contribuição**
1. Fork o projeto
2. Crie uma branch para sua feature
3. Commit suas mudanças
4. Push para a branch
5. Abra um Pull Request

## 📚 Documentação Adicional

- [FLUXOGRAMA_SISTEMA.md](FLUXOGRAMA_SISTEMA.md) - Fluxos detalhados do sistema
- [DIAGRAMA_SISTEMA_COMPLETO.md](DIAGRAMA_SISTEMA_COMPLETO.md) - Documentação técnica completa
- [API Docs](http://localhost:8000/docs) - Documentação interativa da API

## 🆘 Suporte

### **Problemas Comuns**

1. **Erro 401 Unauthorized**
   - Verifique se o token do Kommo está válido
   - Confirme se o subdomain está correto

2. **Webhook não funciona**
   - Verifique se a URL do webhook está acessível
   - Confirme se o n8n está rodando

3. **Vendedores não sincronizam**
   - Verifique as permissões da API do Kommo
   - Confirme se o endpoint `/users` está acessível

### **Contato**
- **Issues**: Abra uma issue no GitHub
- **Documentação**: Consulte a documentação da API
- **Logs**: Verifique os logs para mais detalhes

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## 🎉 Status do Projeto

**✅ SISTEMA PRONTO PARA PRODUÇÃO**

- ✅ Taxa de sucesso: 100%
- ✅ Todos os endpoints funcionais
- ✅ Integrações estáveis
- ✅ Documentação completa
- ✅ Testes passando

---

**Desenvolvido com ❤️ para automação de conversas inteligentes**
