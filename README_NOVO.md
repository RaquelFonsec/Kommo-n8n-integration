# 🚀 Sistema Kommo-n8n-Python Integration (SIMPLIFICADO)

## 📊 Visão Geral

Sistema de integração **simplificado** entre **Kommo CRM**, **n8n (IA/Automação)** e **Python API** para automação completa de conversas via WhatsApp Business com distribuição inteligente por área de atuação.

## 🎯 MUDANÇAS PRINCIPAIS (SISTEMA SIMPLIFICADO)

### ✅ **ANTES (Complexo):**
- Python tentava criar notas diretamente
- Múltiplos pontos de falha
- Código duplicado e complexo

### ✅ **AGORA (Simplificado):**
- **N8N cuida de tudo**: IA + WhatsApp + Notas Kommo
- **Python só coordena** fluxos e distribuição
- **Sistema mais robusto** e confiável

---

## 🏗️ Arquitetura Simplificada

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     KOMMO       │    │   PYTHON API    │    │      N8N        │    │    SUPABASE     │
│   (CRM/Webhook) │◄──►│  (Coordenador)  │◄──►│ (IA/Automação)  │◄──►│   (Agendas)     │
│                 │    │                 │    │                 │    │                 │
│ • Leads/Contatos│    │ • Recebe hooks  │    │ • OpenAI/Claude │    │ • agenda_vendedor│
│ • Envia webhooks│    │ • Distribui     │    │ • WhatsApp API  │    │ • Agendamentos  │
│ • Recebe notas  │    │ • Coordena      │    │ • Kommo API     │    │ • Histórico     │
│ • Interface CRM │    │ • Gerencia bot  │    │ • Workflow único│    │ • Notificações  │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## 🚀 Funcionalidades Principais

### 1. **Distribuição Automática por Área**
- **Previdenciário** → João
- **Trabalhista** → Ana
- **Consumidor** → Carlos
- **Outras áreas** → Distribuição dinâmica

### 2. **Fluxos Automatizados**

#### 📝 **FLUXO 1: Formulário → WhatsApp Proativo**
```
Formulário Site → RD Station → Kommo → Python → N8N → WhatsApp + Nota
```

#### 💬 **FLUXO 2: Cliente Responde → IA Automática**
```
Cliente WhatsApp → Kommo → Python → N8N → IA + WhatsApp + Nota
```

#### 📅 **FLUXO 3: Agendamento Inteligente**
```
"Quero agendar" → Python → N8N → Supabase + WhatsApp + Nota
```

#### 🤖 **FLUXO 4: Controle Manual (Opcional)**
```
#pausar/#voltar → Python → Kommo → Conversa Manual
```

### 3. **Sistema de Agendamento Supabase**
- **Tabelas por vendedor**: `agenda_joao`, `agenda_ana`, `agenda_carlos`
- **Extração automática** de data/hora via IA
- **Confirmações via WhatsApp**
- **Lembretes automáticos**

### 4. **Vendedores Dinâmicos**
- **Sincronização automática** do Kommo
- **Cache inteligente** para performance
- **Vendedores reais + fictícios para teste**

---

## 🔧 Endpoints da API

### 📥 **Webhooks (Entrada)**
```
POST /webhooks/kommo          # Recebe eventos do Kommo
POST /distribuicao/lead       # Distribui leads por área
POST /send-response           # Processa respostas da IA
POST /agendamento/request     # Gerencia agendamentos
```

### 🔍 **Informações (Consulta)**
```
GET  /vendedores             # Lista vendedores dinâmicos
GET  /vendedores/config      # Configuração de vendedores
GET  /health                 # Status do sistema
```

### 🎮 **Controle (Administração)**
```
POST /bot/control            # Pausar/reativar bot
POST /proactive/start        # Iniciar conversa proativa
POST /test-whatsapp          # Teste de conectividade
```

---

## 🔑 Variáveis de Ambiente

### **KOMMO (CRM)**
```env
KOMMO_ACCESS_TOKEN=eyJ0eXAiOiJKV1Q...
KOMMO_API_URL=https://previdas.kommo.com/api/v4
KOMMO_ACCOUNT_ID=34592139
KOMMO_REFRESH_TOKEN=def50200a6b887...
```

### **N8N (Automação)**
```env
N8N_WEBHOOK_URL=https://n8n-n8n.eanhw2.easypanel.host/webhook/serena
N8N_API_KEY=seu_n8n_api_key
```

### **SUPABASE (Agendamentos)**
```env
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=seu_supabase_key
```

### **LOGGING**
```env
LOG_LEVEL=INFO
PYTHON_ENV=production
```

---

## 🚀 Deploy e Execução

### **Docker (Recomendado)**
```bash
# Produção
docker-compose -f docker-compose.prod.yml up -d

# Desenvolvimento
docker-compose up -d
```

### **Local (Desenvolvimento)**
```bash
# Instalar dependências
pip install -r requirements.txt

# Executar
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🧪 Testes

### **Teste Completo do Sistema**
```bash
# Distribuição de lead
curl -X POST http://localhost:8000/distribuicao/lead \
  -H "Content-Type: application/json" \
  -d '{
    "lead_id": 999,
    "contact_id": 888,
    "area_atuacao": "previdenciario",
    "vendedor_atribuido": "João",
    "lead_data": {"name": "Teste Sistema"}
  }'

# Webhook Kommo
curl -X POST http://localhost:8000/webhooks/kommo \
  -H "Content-Type: application/json" \
  -d '{
    "chats": {
      "message": {
        "conversation_id": "conv_888_999",
        "text": "Teste mensagem",
        "contact_id": 888
      }
    }
  }'

# Agendamento
curl -X POST http://localhost:8000/agendamento/request \
  -H "Content-Type: application/json" \
  -d '{
    "contact_id": 888,
    "agenda_data": {
      "data_preferida": "2025-09-15",
      "horario_preferido": "14:00"
    }
  }'
```

### **Teste com Dados Reais**
```bash
# Lead real: 12141408 (Dandara: +55 53 9173-8823)
curl -X POST http://localhost:8000/webhooks/kommo \
  -d '{"chats":{"message":{"conversation_id":"conv_12141408","contact_id":12141408,"text":"Teste sistema real"}}}'
```

---

## 📋 Configuração N8N

### **Webhook URL Necessária:**
```
https://n8n.previdas.com.br/webhook/kommo
```

### **Workflow N8N (1 único):**
1. **Webhook Node** - Recebe dados do Python
2. **Switch Node** - Direciona por `action`
3. **4 Fluxos**:
   - `process_chat_message` → IA + WhatsApp + Nota
   - `create_note_and_send` → Nota + WhatsApp direto
   - `agendamento_request` → Supabase + confirmação
   - `proactive_message` → IA + WhatsApp proativo

### **APIs Integradas no N8N:**
- ✅ **OpenAI/Claude** (IA)
- ✅ **WhatsApp Business** (Mensagens)
- ✅ **Kommo API** (Notas/Atividades)
- ✅ **Supabase** (Agendamentos)

---

## 📊 Monitoramento

### **Health Check**
```bash
curl https://n8n.previdas.com.br/health
```

### **Logs em Tempo Real**
```bash
docker-compose logs -f app
```

### **Métricas**
- **Leads processados**: Via logs
- **Conversas ativas**: Cache interno
- **Agendamentos**: Supabase queries
- **Performance**: Response time

---

## 🔄 Fluxo de Desenvolvimento

### **1. Desenvolvimento Local**
```bash
git clone https://github.com/RaquelFonsec/Kommo-n8n-integration.git
cd kommo-n8n-integration
cp .env.example .env
# Configurar variáveis
docker-compose up -d
```

### **2. Testes**
```bash
# Executar testes do plano
./test_deploy_completo.sh
```

### **3. Deploy**
```bash
git add .
git commit -m "feat: nova funcionalidade"
git push origin main
# Deploy via Docker/SSH
```

---

## 🎯 Casos de Uso

### **ESCRITÓRIO DE ADVOCACIA:**

#### **Cenário 1: Novo Lead**
1. Cliente preenche formulário sobre **previdenciário**
2. Sistema **distribui automaticamente** para João
3. João recebe **mensagem personalizada** via WhatsApp
4. **Conversa iniciada** automaticamente
5. **Tudo documentado** no Kommo

#### **Cenário 2: Cliente Responde**
1. Cliente: *"Quero saber sobre aposentadoria especial"*
2. **IA processa** e gera resposta técnica
3. **Resposta enviada** via WhatsApp
4. **Nota criada** no Kommo para João
5. **Histórico completo** mantido

#### **Cenário 3: Agendamento**
1. Cliente: *"Quero agendar para quinta 15h"*
2. **IA extrai** data e horário
3. **Salva na agenda** do João (Supabase)
4. **Confirmação** via WhatsApp
5. **Lembrete** automático

---

## 🏆 Vantagens do Sistema Simplificado

### ✅ **PARA O ESCRITÓRIO:**
- **Distribuição automática** por especialidade
- **Atendimento 24h** via IA
- **Agendamentos organizados**
- **Histórico completo** no CRM

### ✅ **PARA OS ADVOGADOS:**
- **Leads qualificados** chegam prontos
- **Conversas já iniciadas**
- **Agenda organizada** automaticamente
- **Foco no atendimento**, não na triagem

### ✅ **PARA OS CLIENTES:**
- **Respostas imediatas** e inteligentes
- **Direcionamento correto** por área
- **Agendamentos simples**
- **Atendimento profissional**

### ✅ **TÉCNICAS:**
- **Sistema robusto** com fallbacks
- **Código limpo** e manutenível
- **Performance otimizada**
- **Monitoramento completo**

---

## 📞 Suporte

### **Documentação Técnica:**
- `FLUXOGRAMA_SISTEMA_NOVO.md` - Fluxos detalhados
- `PLANO_TESTES_DEPLOY.md` - Testes pós-deploy
- `N8N_WORKFLOW_COMPLETO.md` - Configuração N8N

### **Logs e Debug:**
```bash
# Ver logs da aplicação
docker-compose logs app

# Status detalhado
curl /health/detailed

# Teste de conectividade
curl /test/all-integrations
```

---

## 🚀 Roadmap

### **✅ CONCLUÍDO:**
- Sistema Python completo
- Integração Kommo/Supabase
- Distribuição por área
- Agendamentos automáticos
- Sistema simplificado (N8N cuida de tudo)

### **🔧 EM ANDAMENTO:**
- Workflow N8N (aguardando implementação)
- Deploy produção

### **📋 PRÓXIMOS PASSOS:**
- Métricas avançadas
- Dashboard administrativo
- Integração RD Station direta
- WhatsApp Web oficial

---

**🎯 SISTEMA 100% AUTOMATIZADO PARA ESCRITÓRIOS DE ADVOCACIA**

**Transforme leads em clientes automaticamente com IA, distribuição inteligente e agendamentos automáticos! 🚀**
