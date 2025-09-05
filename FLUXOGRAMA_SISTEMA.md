# 🔄 FLUXOGRAMA DO SISTEMA KOMMO-N8N-PYTHON

## 📱 FLUXO PROATIVO (Bot inicia conversa)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              FLUXO PROATIVO                                    │
│                         (Bot inicia conversa)                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   GATILHO   │───►│   PYTHON    │───►│     N8N     │───►│  WHATSAPP   │
│             │    │             │    │             │    │             │
│ • Formulário│    │ • Identifica│    │ • Gera      │    │ • Envia     │
│   preenchido│    │   vendedor  │    │   mensagem  │    │   mensagem  │
│ • Material  │    │ • Cria      │    │ • IA        │    │   proativa  │
│   baixado   │    │   conversa  │    │   personaliza│   │             │
│ • Agendamento│   │ • Valida    │    │ • Contexto  │    │             │
│   solicitado│    │   área      │    │   completo  │    │             │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

## 💬 FLUXO REATIVO (Cliente responde)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              FLUXO REATIVO                                     │
│                         (Cliente responde)                                    │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   CLIENTE   │───►│   KOMMO     │───►│   PYTHON    │───►│     N8N     │
│             │    │             │    │             │    │             │
│ • Envia     │    │ • Recebe    │    │ • Processa  │    │ • IA        │
│   mensagem  │    │   webhook   │    │   webhook   │    │   responde  │
│ • WhatsApp  │    │ • Envia     │    │ • Verifica  │    │ • Personaliza│
│   Business  │    │   para API  │    │   bot ativo │    │   resposta  │
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

## 🤖 CONTROLE DE BOT (Vendedor assume)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            CONTROLE DE BOT                                     │
│                         (Vendedor assume)                                     │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  VENDEDOR   │───►│   PYTHON    │───►│     BOT     │───►│   CLIENTE   │
│             │    │             │    │             │    │             │
│ • Digita    │    │ • Processa  │    │ • Pausa     │    │ • Vendedor  │
│   comando   │    │   comando   │    │   automaticamente│ │   assume   │
│ • /assumir  │    │ • Atualiza  │    │ • Para      │    │ • Atendimento│
│ • /liberar  │    │   status    │    │   respostas │    │   humano    │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

## 📅 SISTEMA DE AGENDAMENTO

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          SISTEMA DE AGENDAMENTO                                │
│                         (Integração Supabase)                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   CLIENTE   │───►│   PYTHON    │───►│     N8N     │───►│  SUPABASE   │
│             │    │             │    │             │    │             │
│ • Solicita  │    │ • Identifica│    │ • Processa  │    │ • Armazena  │
│   agendamento│   │   vendedor  │    │   dados     │    │   agenda    │
│ • Escolhe   │    │ • Valida    │    │ • Organiza  │    │ • Histórico │
│   horário   │    │   disponibilidade│ │   informações│   │ • Vendedor  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

## 🎯 CENÁRIOS DE USO

### **Cenário 1: Cliente preenche formulário**
```
1. Cliente preenche formulário no site
2. Kommo cria lead e contato
3. Python recebe webhook ou chamada manual
4. Sistema identifica vendedor responsável
5. Cria conversa proativa no cache
6. Envia dados para n8n com contexto completo
7. n8n gera mensagem personalizada
8. Mensagem é enviada via WhatsApp
9. Sistema cria nota no lead do Kommo
```

### **Cenário 2: Cliente responde mensagem**
```
1. Cliente envia mensagem no WhatsApp
2. Kommo recebe mensagem e envia webhook
3. Python processa webhook e verifica status do bot
4. Se bot ativo, envia para n8n
5. n8n gera resposta personalizada
6. Resposta é enviada via Kommo
7. Sistema registra interação no lead
```

### **Cenário 3: Vendedor assume conversa**
```
1. Vendedor digita "/assumir 12345" no WhatsApp Business
2. Kommo envia webhook (não é do contato)
3. Python detecta comando e pausa bot
4. Bot fica pausado para aquele contato
5. Vendedor pode atender cliente normalmente
6. Vendedor digita "/liberar 12345"
7. Bot reativa automaticamente
```

### **Cenário 4: Cliente solicita agendamento**
```
1. Cliente solicita agendamento durante conversa
2. Python identifica vendedor responsável
3. Sistema envia dados estruturados para n8n
4. n8n processa e envia para Supabase
5. Dados são armazenados na tabela específica do vendedor
6. Sistema confirma agendamento para o cliente
```

## 🔧 COMPONENTES TÉCNICOS

### **Python API (FastAPI)**
- **Porta**: 8000
- **Endpoints**: 26 endpoints ativos
- **Funcionalidades**: Webhooks, controle de bot, vendedores, agendamento

### **Kommo API**
- **URL**: `https://previdas.kommo.com/api/v4/`
- **Autenticação**: OAuth2 + Access Token
- **Endpoints**: `/users`, `/leads`, `/contacts`, `/leads/{id}/notes`

### **n8n (Automação)**
- **Função**: IA/LLM + Workflows
- **Integração**: Webhooks bidirecionais
- **Funcionalidades**: Respostas personalizadas, agendamentos, Supabase

### **Supabase (Banco)**
- **Função**: Armazenamento de agendamentos
- **Integração**: Via n8n
- **Tabelas**: `agenda_[vendedor]`, `vendedores`, `histórico`

## 📊 MÉTRICAS E MONITORAMENTO

### **Taxa de Sucesso**
- ✅ **100%** dos endpoints funcionais
- ✅ **9 vendedores reais** sincronizados
- ✅ **3 vendedores fictícios** para testes
- ✅ **26 endpoints** ativos

### **Performance**
- **Cache inteligente** para vendedores
- **Processamento assíncrono** de webhooks
- **Logs estruturados** para monitoramento
- **Health checks** automáticos

### **Confiabilidade**
- **Tratamento de erros** robusto
- **Fallbacks** para APIs externas
- **Validação de dados** com Pydantic
- **Retry logic** para falhas temporárias

---

**Este fluxograma representa o funcionamento completo do sistema de integração Kommo-n8n-Python, mostrando todos os fluxos de dados e interações entre os componentes.**

