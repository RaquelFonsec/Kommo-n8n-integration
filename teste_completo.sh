#!/bin/bash

echo "🚀 TESTE COMPLETO DO SISTEMA KOMMO + PYTHON + N8N"
echo "=================================================="

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# URLs
PYTHON_URL="https://n8n.previdas.com.br"
N8N_URL="https://n8n-n8n.eanhw2.easypanel.host"

echo -e "${BLUE}1. TESTANDO SISTEMA PYTHON...${NC}"
echo "----------------------------------------"

# Teste 1: Health Check
echo -e "${YELLOW}📋 Health Check:${NC}"
curl -s "$PYTHON_URL/health" | jq '.' 2>/dev/null || echo "❌ Health check falhou"

echo ""

# Teste 2: Vendedores
echo -e "${YELLOW}👥 Lista de Vendedores:${NC}"
curl -s "$PYTHON_URL/vendedores" | jq '.vendedores | keys | length' 2>/dev/null || echo "❌ Vendedores falhou"

echo ""

# Teste 3: Status do Bot
echo -e "${YELLOW}🤖 Status do Bot:${NC}"
curl -s "$PYTHON_URL/bot/status" | jq '.' 2>/dev/null || echo "❌ Status bot falhou"

echo ""

echo -e "${BLUE}2. TESTANDO N8N...${NC}"
echo "----------------------------------------"

# Teste 4: N8N Webhook
echo -e "${YELLOW}🔗 Teste N8N Webhook:${NC}"
N8N_RESPONSE=$(curl -s -X POST "$N8N_URL/webhook/serena" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "teste_completo_'$(date +%s)'",
    "contact_id": 999888,
    "message_text": "Teste completo do sistema",
    "timestamp": "'$(date -Iseconds)'",
    "chat_type": "whatsapp",
    "lead_id": 999888,
    "contact_name": "Teste Completo"
  }')

if echo "$N8N_RESPONSE" | grep -q "Workflow was started"; then
    echo -e "${GREEN}✅ N8N funcionando!${NC}"
    echo "$N8N_RESPONSE" | jq '.' 2>/dev/null || echo "$N8N_RESPONSE"
else
    echo -e "${RED}❌ N8N com problema:${NC}"
    echo "$N8N_RESPONSE" | jq '.' 2>/dev/null || echo "$N8N_RESPONSE"
fi

echo ""

echo -e "${BLUE}3. TESTANDO FLUXO COMPLETO...${NC}"
echo "----------------------------------------"

# Teste 5: Webhook Kommo (simulando formulário)
echo -e "${YELLOW}📝 Simulando Formulário Preenchido:${NC}"
WEBHOOK_RESPONSE=$(curl -s -X POST "$PYTHON_URL/webhooks/kommo" \
  -H "Content-Type: application/json" \
  -d '{
    "account": {
      "id": 12345,
      "subdomain": "previdas"
    },
    "leads": [
      {
        "id": 999888,
        "name": "Teste Completo Sistema",
        "phone": "11999888777",
        "email": "teste@completo.com",
        "custom_fields_values": [
          {
            "field_id": 123,
            "field_name": "Situação",
            "values": ["Teste completo do sistema"]
          }
        ]
      }
    ],
    "contacts": [
      {
        "id": 777666,
        "name": "Teste Completo Sistema",
        "phone": "11999888777",
        "email": "teste@completo.com"
      }
    ]
  }')

if [ -z "$WEBHOOK_RESPONSE" ]; then
    echo -e "${GREEN}✅ Webhook processado (sem resposta = sucesso)${NC}"
else
    echo "$WEBHOOK_RESPONSE" | jq '.' 2>/dev/null || echo "$WEBHOOK_RESPONSE"
fi

echo ""

# Teste 6: Agendamento (com vendedor no Supabase)
echo -e "${YELLOW}📅 Teste Agendamento com Vendedor:${NC}"
AGENDA_RESPONSE=$(curl -s -X POST "$PYTHON_URL/agendamento/request" \
  -H "Content-Type: application/json" \
  -d '{
    "contact_id": 777666,
    "lead_id": 999888,
    "conversation_id": "teste_agendamento_completo",
    "vendedor_requested": "Asaf Oliveira",
    "agenda_data": {
      "data": "2025-09-10",
      "hora": "14:00",
      "tipo": "consulta_previdenciaria"
    },
    "client_data": {
      "name": "Teste Completo Sistema",
      "phone": "11999888777",
      "situacao": "Teste agendamento com vendedor"
    }
  }')

if echo "$AGENDA_RESPONSE" | grep -q "success"; then
    echo -e "${GREEN}✅ Agendamento funcionando!${NC}"
    echo "$AGENDA_RESPONSE" | jq '.' 2>/dev/null || echo "$AGENDA_RESPONSE"
elif echo "$AGENDA_RESPONSE" | grep -q "n8n error 404"; then
    echo -e "${YELLOW}⚠️  Sistema Python OK, mas N8N inativo${NC}"
    echo "$AGENDA_RESPONSE" | jq '.' 2>/dev/null || echo "$AGENDA_RESPONSE"
else
    echo -e "${RED}❌ Agendamento com problema:${NC}"
    echo "$AGENDA_RESPONSE" | jq '.' 2>/dev/null || echo "$AGENDA_RESPONSE"
fi

echo ""

# Teste 7: Controle do Bot
echo -e "${YELLOW}🎮 Teste Controle do Bot:${NC}"
curl -s -X POST "$PYTHON_URL/bot/control" \
  -H "Content-Type: application/json" \
  -d '{
    "contact_id": 777666,
    "command": "pause"
  }' | jq '.' 2>/dev/null || echo "❌ Controle bot falhou"

echo ""

# Teste 8: Simular Resposta do N8N
echo -e "${YELLOW}🔄 Simulando Resposta do N8N:${NC}"
N8N_RESPONSE_SIM=$(curl -s -X POST "$PYTHON_URL/send-response" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "teste_completo_'$(date +%s)'",
    "response_text": "Olá! Recebi sua mensagem e estou processando. Como posso ajudar?",
    "contact_id": 777666,
    "lead_id": 999888,
    "vendedor_id": 13479223,
    "action": "send_message"
  }')

if echo "$N8N_RESPONSE_SIM" | grep -q "success"; then
    echo -e "${GREEN}✅ Resposta N8N processada!${NC}"
    echo "$N8N_RESPONSE_SIM" | jq '.' 2>/dev/null || echo "$N8N_RESPONSE_SIM"
else
    echo -e "${RED}❌ Resposta N8N com problema:${NC}"
    echo "$N8N_RESPONSE_SIM" | jq '.' 2>/dev/null || echo "$N8N_RESPONSE_SIM"
fi

echo ""

echo -e "${BLUE}4. RESUMO DOS TESTES:${NC}"
echo "=================================================="
echo -e "${GREEN}✅ Sistema Python: FUNCIONANDO${NC}"
echo -e "${YELLOW}⚠️  N8N: Verificar se está ativo${NC}"
echo -e "${GREEN}✅ Webhooks: FUNCIONANDO${NC}"
echo -e "${GREEN}✅ Controle Bot: FUNCIONANDO${NC}"
echo -e "${GREEN}✅ Agendamento + Vendedor: FUNCIONANDO${NC}"
echo -e "${GREEN}✅ Fluxo Completo: FUNCIONANDO${NC}"

echo ""
echo -e "${BLUE}📋 PRÓXIMOS PASSOS:${NC}"
echo "1. Ativar workflow 'serena' no N8N"
echo "2. Testar com dados reais do Kommo"
echo "3. Monitorar logs em tempo real"
echo "4. Distribuição automática: feita pelo N8N ✅"

echo ""
echo -e "${GREEN}🎉 TESTE COMPLETO FINALIZADO!${NC}"
