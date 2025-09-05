# 🚀 SISTEMA KOMMO-N8N-PYTHON - DIAGRAMA COMPLETO

## 📊 VISÃO GERAL DO SISTEMA

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           SISTEMA KOMMO-N8N-PYTHON                             │
│                                                     │
└─────────────────────────────────────────────────────────────────────────────────┘

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

## 🔄 FLUXOS PRINCIPAIS

### 1. 📱 FLUXO PROATIVO (Bot inicia conversa)

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   GATILHO   │───►│   PYTHON    │───►│     N8N     │───►│  WHATSAPP   │
│             │    │             │    │             │    │             │
│ • Formulário│    │ • Identifica│    │ • Gera      │    │ • Envia     │
│ • Download  │    │   vendedor  │    │   mensagem  │    │   mensagem  │
│ • Agendamento│   │ • Cria      │    │ • IA        │    │   proativa  │
│             │    │   conversa  │    │   personaliza│   │             │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### 2. 💬 FLUXO REATIVO (Cliente responde)

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   CLIENTE   │───►│   KOMMO     │───►│   PYTHON    │───►│     N8N     │
│             │    │             │    │             │    │             │
│ • Envia     │    │ • Recebe    │    │ • Processa  │    │ • IA        │
│   mensagem  │    │   webhook   │    │   webhook   │    │   responde  │
│ • WhatsApp  │    │ • Envia     │    │ • Verifica  │    │ • Personaliza│
│             │    │   para API  │    │   bot ativo │    │   resposta  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                                              │
                                                              ▼
                                                   ┌─────────────┐
                                                   │   KOMMO     │
                                                   │             │
                                                   │ • Cria nota │
                                                   │ • Atualiza  │
                                                   │   lead      │
                                                   └─────────────┘
```

### 3. 🤖 CONTROLE DE BOT (Vendedor assume)

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  VENDEDOR   │───►│   PYTHON    │───►│     BOT     │
│             │    │             │    │             │
│ • Digita    │    │ • Processa  │    │ • Pausa     │
│   comando   │    │   comando   │    │   automaticamente│
│ • /assumir  │    │ • Atualiza  │    │ • Vendedor  │
│ • /liberar  │    │   status    │    │   assume    │
└─────────────┘    └─────────────┘    └─────────────┘
```

## 🏗️ ARQUITETURA TÉCNICA

### 📁 ESTRUTURA DE ARQUIVOS

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
└── docker-compose.yml          # 🐳 Docker
```

### 🔧 COMPONENTES PRINCIPAIS

#### 1. **FastAPI (Python)**
- **Porta**: 8000
- **Endpoints**: 26 endpoints ativos
- **Funcionalidades**:
  - Webhooks do Kommo
  - Controle de bot
  - Gerenciamento de vendedores
  - Sistema de agendamento
  - Conversas proativas

#### 2. **Kommo API**
- **URL**: `https://previdas.kommo.com/api/v4/`
- **Autenticação**: OAuth2 + Access Token
- **Endpoints usados**:
  - `/users` - Vendedores reais
  - `/leads` - Dados dos leads
  - `/contacts` - Dados dos contatos
  - `/leads/{id}/notes` - Criar notas

#### 3. **n8n (Automação)**
- **Função**: IA/LLM + Workflows
- **Integração**: Webhooks bidirecionais
- **Funcionalidades**:
  - Geração de respostas personalizadas
  - Processamento de agendamentos
  - Integração com Supabase

#### 4. **Supabase (Banco de Dados)**
- **Função**: Armazenamento de agendamentos
- **Integração**: Via n8n
- **Tabelas**:
  - `agenda` - Agendamentos
  - `vendedores` - Vendedores

## 📊 ENDPOINTS ATIVOS (26 total)

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
- `POST /sincronizar/vendedores` - Alias para sincronização

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

### 🧪 **Testes & Debug**
- `GET /webhooks/test` - Teste de webhook
- `GET /test-kommo-lead/{id}` - Teste de lead específico
- `DELETE /reset/conversations` - Reset das conversas

## 🎯 FUNCIONALIDADES PRINCIPAIS

### 1. **Vendedores Dinâmicos**
- ✅ **Vendedores Reais**: Busca automática do Kommo (9 vendedores encontrados)
- ✅ **Vendedores Fictícios**: 3 vendedores de exemplo
- ✅ **Sincronização**: Atualização automática dos vendedores reais
- ✅ **Cache**: Sistema de cache para performance

### 2. **Conversas Proativas**
- ✅ **Gatilhos**: Formulário, download, agendamento
- ✅ **Personalização**: Mensagens personalizadas por vendedor
- ✅ **Prevenção de Duplicatas**: Não cria conversas duplicadas
- ✅ **Áreas Elegíveis**: Filtro por área de atuação

### 3. **Controle de Bot**
- ✅ **Pausar/Reativar**: Controle manual via API
- ✅ **Comandos Simples**: `/assumir` e `/liberar` para vendedores
- ✅ **Status**: Verificação de status do bot
- ✅ **Cache de Status**: Sistema de cache para performance

### 4. **Sistema de Agendamento**
- ✅ **Identificação de Vendedor**: Automática por conversa/contato/lead
- ✅ **Integração n8n**: Envio de dados estruturados
- ✅ **Contexto Supabase**: Dados completos para agendamento
- ✅ **Payload Estruturado**: Dados organizados para processamento

### 5. **Integração Kommo**
- ✅ **OAuth2**: Sistema de autenticação
- ✅ **Refresh Token**: Renovação automática de tokens
- ✅ **API Notes**: Criação de notas nos leads
- ✅ **Webhooks**: Recebimento de mensagens





