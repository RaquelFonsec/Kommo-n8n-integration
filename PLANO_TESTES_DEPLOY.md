# PLANO DE TESTES PÓS-DEPLOY

## FASE 1: TESTES BÁSICOS DE CONECTIVIDADE

### 1.1 TESTAR ENDPOINTS PYTHON
```bash
# Sistema no ar
curl https://n8n.previdas.com.br/health

# Vendedores configurados
curl https://n8n.previdas.com.br/vendedores

# Webhook Kommo funcionando
curl -X POST https://n8n.previdas.com.br/webhooks/kommo \
  -H "Content-Type: application/json" \
  -d '{"test": "connectivity"}'
```

### 1.2 TESTAR N8N WEBHOOK
```bash
# N8N respondendo
curl https://n8n.previdas.com.br/webhook/kommo \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"action": "test", "message": "conectividade"}'
```

### 1.3 TESTAR INTEGRAÇÃO PYTHON → N8N
```bash
# Python enviando para N8N
curl -X POST https://n8n.previdas.com.br/send-response \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "conv_test_123",
    "response_text": "Teste de integração pós-deploy"
  }'
```

---

## FASE 2: TESTES FUNCIONAIS

### 2.1 TESTE DISTRIBUIÇÃO DE LEAD
```bash
# Simular chegada de lead do formulário
curl -X POST https://n8n.previdas.com.br/distribuicao/lead \
  -H "Content-Type: application/json" \
  -d '{
    "lead_id": 999888,
    "contact_id": 777666,
    "area_atuacao": "previdenciario",
    "vendedor_atribuido": "João", 
    "lead_data": {
      "name": "Teste Deploy",
      "phone": "11999888777",
      "situacao": "teste pós-deploy"
    },
    "fonte_original": "teste_deploy",
    "trigger_type": "teste_formulario"
  }'
```

**RESULTADO ESPERADO:**
- Status 200
- Conversa proativa iniciada
- N8N processa e envia WhatsApp
- Nota criada no Kommo

### 2.2 TESTE WEBHOOK KOMMO
```bash
# Simular mensagem vinda do Kommo
curl -X POST https://n8n.previdas.com.br/webhooks/kommo \
  -H "Content-Type: application/json" \
  -d '{
    "chats": {
      "message": {
        "conversation_id": "conv_777666_999888",
        "contact_id": 777666,
        "text": "Teste de mensagem pós-deploy",
        "timestamp": '$(date +%s)',
        "author": {"type": "contact"}
      }
    }
  }'
```

**RESULTADO ESPERADO:**
- Webhook processado
- Mensagem enviada para N8N
- IA responde
- Resposta enviada via WhatsApp
- Nota criada no Kommo

### 2.3 TESTE AGENDAMENTO
```bash
# Simular solicitação de agendamento
curl -X POST https://n8n.previdas.com.br/agendamento/request \
  -H "Content-Type: application/json" \
  -d '{
    "contact_id": 777666,
    "conversation_id": "conv_777666_999888",
    "vendedor_requested": "João",
    "agenda_data": {
      "data_preferida": "2025-09-15",
      "horario_preferido": "14:00"
    },
    "client_data": {
      "nome": "Teste Deploy"
    }
  }'
```

**RESULTADO ESPERADO:**
- Agendamento salvo no Supabase
- WhatsApp de confirmação enviado
- Nota de agendamento no Kommo

---

## FASE 3: TESTES COM DADOS REAIS

### 3.1 TESTE COM LEAD REAL DO KOMMO
```bash
# Usar lead existente: 12141408
curl -X POST https://n8n.previdas.com.br/webhooks/kommo \
  -H "Content-Type: application/json" \
  -d '{
    "chats": {
      "message": {
        "conversation_id": "conv_real_12141408",
        "contact_id": 12141408,
        "text": "Teste com lead real - deploy funcionando",
        "timestamp": '$(date +%s)',
        "author": {"type": "contact"}
      }
    }
  }'
```

### 3.2 TESTE COM NÚMERO REAL (+55 53 9173-8823)
```bash
# Teste com Dandara
curl -X POST https://n8n.previdas.com.br/distribuicao/lead \
  -H "Content-Type: application/json" \
  -d '{
    "lead_id": 12141408,
    "contact_id": 12141408,
    "area_atuacao": "previdenciario",
    "vendedor_atribuido": "João",
    "lead_data": {
      "name": "Dandara",
      "phone": "5553917388223"
    },
    "fonte_original": "teste_real_deploy"
  }'
```

**VERIFICAR:**
- Dandara recebe WhatsApp real
- Nota aparece no Kommo lead 12141408
- Sistema funciona fim-a-fim

---

## FASE 4: TESTES DE MONITORAMENTO

### 4.1 VERIFICAR LOGS
```bash
# Logs do sistema Python
curl https://n8n.previdas.com.br/logs/recent

# Status de saúde
curl https://n8n.previdas.com.br/health/detailed
```

### 4.2 VERIFICAR INTEGRAÇÕES
```bash
# Kommo API funcionando
curl https://n8n.previdas.com.br/test/kommo-connection

# Supabase funcionando  
curl https://n8n.previdas.com.br/test/supabase-connection

# N8N funcionando
curl https://n8n.previdas.com.br/test/n8n-connection
```

---

## FASE 5: TESTE DE CARGA

### 5.1 MÚLTIPLAS REQUISIÇÕES
```bash
# 10 requisições simultâneas
for i in {1..10}; do
  curl -X POST https://n8n.previdas.com.br/webhooks/kommo \
    -H "Content-Type: application/json" \
    -d "{\"test\": \"carga_$i\"}" &
done
wait
```

### 5.2 TESTE DE FAILOVER
```bash
# Testar com dados inválidos
curl -X POST https://n8n.previdas.com.br/distribuicao/lead \
  -H "Content-Type: application/json" \
  -d '{"dados": "inválidos"}'

# Verificar se sistema se recupera
curl https://n8n.previdas.com.br/health
```

---

## CHECKLIST FINAL DE DEPLOY

### ✅ PRÉ-DEPLOY
- [ ] Código commitado e atualizado
- [ ] N8N workflow criado e testado
- [ ] Tokens e variáveis configurados
- [ ] Backup do sistema atual

### ✅ DURANTE DEPLOY
- [ ] Aplicação subiu sem erros
- [ ] Todas as variáveis carregadas
- [ ] Endpoints respondendo
- [ ] N8N conectado

### ✅ PÓS-DEPLOY
- [ ] Fase 1: Conectividade ✅
- [ ] Fase 2: Funcional ✅
- [ ] Fase 3: Dados reais ✅  
- [ ] Fase 4: Monitoramento ✅
- [ ] Fase 5: Carga ✅

### ✅ VALIDAÇÃO FINAL
- [ ] Lead real processado com sucesso
- [ ] WhatsApp real enviado e recebido
- [ ] Nota criada no Kommo corretamente
- [ ] Agendamento salvo no Supabase
- [ ] Sistema 100% operacional

---

## COMANDOS RÁPIDOS DE TESTE

### TESTE COMPLETO EM 1 COMANDO
```bash
# Executa todos os testes principais
./test_deploy_completo.sh
```

### MONITORAMENTO CONTÍNUO
```bash
# Monitora sistema em tempo real
watch -n 30 'curl -s https://n8n.previdas.com.br/health | jq'
```

### ROLLBACK SE NECESSÁRIO
```bash
# Volta para versão anterior
git checkout HEAD~1
docker-compose up -d
```

**RESULTADO ESPERADO: SISTEMA 100% FUNCIONAL EM PRODUÇÃO! 🚀**

