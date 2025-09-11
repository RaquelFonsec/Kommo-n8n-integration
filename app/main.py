import os
import logging
import uvicorn
import aiohttp
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Importar modelos Pydantic
from app.models.kommo_models import ProactiveStart, DistribuicaoPayload, BotCommand, N8nResponse, VendedorCustom, AgendamentoPayload
from app.services.kommo_service import KommoService

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==========================================
# CONFIGURAÇÃO FASTAPI
# ==========================================

app = FastAPI(
    title="Kommo-n8n Integration API",
    description="API para integração entre Kommo CRM, n8n e WhatsApp Business com sistema de agendamento",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# CACHE E CONFIGURAÇÕES GLOBAIS
# ==========================================

_proactive_conversations = {}
_vendedores_cache = {}
_last_vendedores_update = None

# ==========================================
# FUNÇÕES AUXILIARES
# ==========================================

async def send_to_n8n(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Envia dados para n8n via webhook - PRODUÇÃO
    Configurado para usar a URL de produção correta
    """
    try:
        # Usar URL do n8n configurada no .env
        n8n_webhook_url = os.getenv("N8N_WEBHOOK_URL", "https://n8n-n8n.eanhw2.easypanel.host/webhook/serena")
        
        # Manter URL do n8n que funciona (eanhw2.easypanel.host é o n8n real)
        # n8n.previdas.com.br é ESTE sistema Python, não o n8n!
        
        logger.info(f"Enviando para n8n: {n8n_webhook_url}")
        logger.info(f"Payload: {payload}")
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Previdas-Bot/1.0"
        }
        
        # API Key se disponível
        api_key = os.getenv("N8N_API_KEY")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(n8n_webhook_url, json=payload, headers=headers) as response:
                response_text = await response.text()
                logger.info(f"📡 n8n Response Status: {response.status}")
                
                if response.status in [200, 201]:
                    try:
                        result = await response.json() if response.content_type == "application/json" else {"message": response_text}
                        logger.info(f"Resposta do n8n: {result}")
                        return result
                    except:
                        logger.info(f"n8n resposta (texto): {response_text}")
                        return {"message": response_text, "status": "success"}
                else:
                    logger.error(f"Erro n8n {response.status}: {response_text}")
                    return {"error": f"n8n error {response.status}: {response_text}"}
                    
    except Exception as e:
        logger.error(f"Erro ao enviar para n8n: {e}")
        return {"error": str(e)}

async def get_vendedores_dinamicos():
    """Busca vendedores diretamente do Kommo"""
    global _vendedores_cache, _last_vendedores_update
    
    try:
        # Cache por 5 minutos
        if _last_vendedores_update and (datetime.now() - _last_vendedores_update).seconds < 300:
            return _vendedores_cache
        
        kommo_service = KommoService()
        api_url = os.getenv("KOMMO_API_URL")
        access_token = os.getenv("KOMMO_ACCESS_TOKEN")
        
        if not api_url or not access_token:
            logger.error("Configurações Kommo não encontradas")
            return {}
        
        headers = {"Authorization": f"Bearer {access_token}"}
        url = f"{api_url}/users"
        
        timeout = aiohttp.ClientTimeout(total=15, connect=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    users = data.get("_embedded", {}).get("users", [])
                    
                    vendedores = {}
                    for user in users:
                        if user.get("rights", {}).get("is_active", False):
                            nome = user.get("name", "").strip()
                            if nome:
                                vendedores[nome] = {
                                    "id": user.get("id"),
                                    "name": nome,
                                    "email": user.get("email", ""),
                                    "phone_api": f"{nome.lower().replace(' ', '_')}_whatsapp",
                                    "display_name": f"{nome} - Previdas",
                                    "area_atuacao": "nao_identificada"
                                }
                    
                    _vendedores_cache = vendedores
                    _last_vendedores_update = datetime.now()
                    
                    logger.info(f"Encontrados {len(vendedores)} vendedores reais no Kommo")
                    logger.info("Cache de vendedores atualizado com dados reais")
                    
                    return vendedores
                else:
                    logger.error(f"Erro ao buscar vendedores do Kommo: {response.status}")
                    return {}
                    
    except Exception as e:
        logger.error(f"Erro ao buscar vendedores: {e}")
        return {}

async def get_vendedor_whatsapp_config(vendedor_name: str) -> Dict[str, str]:
    """Retorna configuração do WhatsApp para um vendedor específico"""
    vendedores = await get_vendedores_dinamicos()
    
    if vendedor_name in vendedores:
        return vendedores[vendedor_name]
    
    # Fallback para vendedores não encontrados
    return {
        "name": vendedor_name,
        "display_name": f"{vendedor_name} - Previdas",
        "phone_api": f"{vendedor_name.lower().replace(' ', '_')}_whatsapp",
        "area_atuacao": "nao_identificada"
    }

async def start_proactive_conversation(proactive_data: ProactiveStart) -> Dict[str, Any]:
    """Inicia uma conversa proativa com um lead"""
    try:
        logger.info(f"Iniciando conversa proativa para contato {proactive_data.contact_id}")
        
        # Buscar configuração do vendedor
        vendedor_config = await get_vendedor_whatsapp_config(proactive_data.vendedor)
        
        # Preparar dados da conversa
        conversation_id = f"conv_{proactive_data.contact_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Salvar contexto da conversa
        _proactive_conversations[proactive_data.contact_id] = {
            "conversation_id": conversation_id,
            "vendedor": proactive_data.vendedor,
            "area_atuacao": proactive_data.area_atuacao,
            "trigger_type": proactive_data.trigger_type,
            "initiated_at": datetime.now().isoformat(),
            "initiated_by_bot": True,
            "first_response_received": False,
            "lead_data": proactive_data.lead_data or {}
        }
        
        # Preparar payload para n8n
        payload = {
            "action": "start_proactive",
            "conversation_id": conversation_id,
            "contact_id": proactive_data.contact_id,
            "lead_id": proactive_data.lead_id,
            "vendedor": vendedor_config,
            "area_atuacao": proactive_data.area_atuacao,
            "trigger_type": proactive_data.trigger_type,
            "lead_data": proactive_data.lead_data,
            "custom_message": getattr(proactive_data, 'custom_message', None),
            "timestamp": datetime.now().isoformat()
        }
        
        # Enviar para n8n
        result = await send_to_n8n(payload)
        
        if "error" not in result:
            logger.info(f"Conversa proativa iniciada com sucesso: {conversation_id}")
            return {
                "success": True,
                "conversation_id": conversation_id,
                "vendedor": proactive_data.vendedor,
                "n8n_response": result
            }
        else:
            logger.error(f"Erro ao iniciar conversa via n8n: {result}")
            return {"success": False, "error": result.get("error")}
            
    except Exception as e:
        logger.error(f"Erro ao iniciar conversa proativa: {e}")
        return {"success": False, "error": str(e)}

# ==========================================
# FUNÇÕES DE NOTA KOMMO - REMOVIDAS
# ==========================================
# Simplificação: N8N agora cuida de criar notas + enviar WhatsApp
# Sistema mais simples e confiável

# REMOVIDO: create_kommo_note_simple - N8N faz isso agora
async def create_kommo_note_simple_DEPRECATED(conversation_id: str, message: str) -> Dict[str, Any]:
    """
    Cria uma nota simples no Kommo usando API de Notes v4
    Configurado para trabalhar com as permissões corretas do token
    """
    try:
        logger.info(f"create_kommo_note_simple chamada para {conversation_id}")
        
        # Extrair lead_id do conversation_id
        parts = conversation_id.split("_")
        if len(parts) >= 3 and parts[-1].isdigit():
            lead_id = parts[-1]
        elif len(parts) >= 2 and parts[1].isdigit():
            lead_id = parts[1]  # Formato alternativo: conv_12345_...
        else:
            logger.error(f"Não foi possível extrair lead_id de: {conversation_id}")
            return {"success": False, "error": "conversation_id inválido"}
        
        logger.info(f"Criando nota no lead {lead_id}")
        
        # Configurações Kommo
        api_url = os.getenv("KOMMO_API_URL", "https://previdas.kommo.com/api/v4")
        access_token = os.getenv("KOMMO_ACCESS_TOKEN")
        
        if not access_token:
            return {"success": False, "error": "KOMMO_ACCESS_TOKEN não configurado"}
        
        # Payload correto para API de Notes do Kommo v4
        # Baseado na documentação oficial e na correção do n8n produção
        note_payload = {
            "note_type": "common",
            "params": {
                "text": f"🤖 RESPOSTA IA:\n\n{message}\n\n📝 Mensagem gerada pela IA para envio manual ao cliente."
            }
        }
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "User-Agent": "Previdas-Bot/1.0"
        }
        
        # URL correta para API v4 de Notes
        url = f"{api_url}/leads/{lead_id}/notes"
        logger.info(f"📡 API Notes URL: {url}")
        logger.info(f"📦 Payload Notes: {note_payload}")
        
        timeout = aiohttp.ClientTimeout(total=20, connect=8)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=note_payload, headers=headers) as response:
                response_text = await response.text()
                logger.info(f"📡 Resposta API Notes: Status {response.status}")
                logger.info(f"📡 Resposta API Notes: Body {response_text}")
                
                if response.status in [200, 201]:
                    try:
                        result = await response.json() if response.content_type == "application/json" else {"raw": response_text}
                        logger.info("✅ Nota criada com sucesso no Kommo via API Notes")
                        return {"success": True, "data": result, "method": "api_notes"}
                    except:
                        logger.info("✅ Nota criada (resposta não-JSON)")
                        return {"success": True, "data": {"response": response_text}, "method": "api_notes"}
                elif response.status == 400:
                    logger.warning(f"⚠️ Bad Request (400): {response_text}")
                    return {"success": False, "error": f"Bad Request: {response_text}"}
                elif response.status == 401:
                    logger.error(f"❌ Token inválido (401): {response_text}")
                    return {"success": False, "error": "Token de acesso inválido"}
                elif response.status == 403:
                    logger.error(f"❌ Sem permissão (403): {response_text}")
                    return {"success": False, "error": "Sem permissão para criar notas"}
                elif response.status == 404:
                    logger.error(f"❌ Lead não encontrado (404): {response_text}")
                    return {"success": False, "error": f"Lead {lead_id} não encontrado"}
                else:
                    logger.error(f"❌ Erro API Notes {response.status}: {response_text}")
                    return {"success": False, "error": f"API error {response.status}: {response_text}"}
                    
    except Exception as e:
        logger.error(f"❌ Erro ao criar nota via API Notes: {e}")
        return {"success": False, "error": str(e)}

# REMOVIDO: send_kommo_message_new - N8N faz isso direto agora
async def send_kommo_message_new_DEPRECATED(conversation_id: str, message: str) -> Dict[str, Any]:
    """
    DEPRECATED: Função removida - N8N agora faz nota + WhatsApp diretamente
    Mantida apenas para referência histórica
    """
    logger.info(f"🔄 FALLBACK: Enviando via n8n para {conversation_id}")
    
    try:
        # Extrair lead_id do conversation_id
        try:
            parts = conversation_id.split("_")
            if len(parts) >= 3 and parts[2].isdigit():
                lead_id = parts[2]
            else:
                logger.error(f"Conversation_id inválido: {conversation_id}")
                return {"success": False, "error": "conversation_id inválido"}
        except:
            logger.error(f"Não foi possível extrair lead_id de: {conversation_id}")
            return {"success": False, "error": "conversation_id inválido"}
        
        # Buscar dados do lead via KommoService
        kommo_service = KommoService()
        lead_data = await kommo_service.get_lead_by_contact(int(lead_id)) if lead_id.isdigit() else None
        if not lead_data:
            return {"success": False, "error": "Lead não encontrado"}
        
        # Extrair número do WhatsApp
        contact_data = lead_data.get("contacts", {}).get("data", [])
        if not contact_data:
            return {"success": False, "error": "Contato não encontrado"}
        
        contact = contact_data[0]
        custom_fields = contact.get("custom_fields_values", [])
        
        whatsapp_number = None
        for field in custom_fields:
            if field.get("field_code") == "PHONE":
                whatsapp_number = field.get("values", [{}])[0].get("value", "")
                break
        
        if not whatsapp_number:
            return {"success": False, "error": "Número do WhatsApp não encontrado"}
        
        # Limpar número
        clean_number = whatsapp_number.replace("+", "").replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        if clean_number.startswith("55"):
            clean_number = clean_number[2:]
        
        # Enviar via n8n (usando URL de produção)
        n8n_whatsapp_url = os.getenv("N8N_WHATSAPP_URL", "https://n8n.previdas.com.br/webhook/whatsapp")
        n8n_webhook_url = os.getenv("N8N_WEBHOOK_URL", "https://n8n.previdas.com.br/webhook/serena")
        
        # Usar webhook principal se whatsapp específico não estiver configurado
        if "n8n-n8n.eanhw2.easypanel.host" in n8n_whatsapp_url:
            n8n_whatsapp_url = "https://n8n.previdas.com.br/webhook/whatsapp"
            logger.info(f"🔄 Usando URL de produção: {n8n_whatsapp_url}")
        
        payload = {
            "to": f"55{clean_number}",
            "message": f"🤖 RESPOSTA SUGERIDA PELO BOT:\n\n{message}\n\n📝 ENVIE ESTA MENSAGEM MANUALMENTE PARA O CLIENTE",
            "conversation_id": conversation_id,
            "lead_id": lead_id,
            "contact_id": contact.get("id"),
            "source": "kommo_bot_response"
        }
        
        timeout = aiohttp.ClientTimeout(total=15, connect=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(n8n_whatsapp_url, json=payload) as response:
                if response.status in [200, 201]:
                    result = await response.json()
                    logger.info(f"✅ FALLBACK: Mensagem enviada via n8n para {clean_number}")
                    return {
                        "success": True,
                        "data": result,
                        "message": "Mensagem enviada via n8n (fallback)",
                        "conversation_id": conversation_id,
                        "lead_id": lead_id,
                        "method": "n8n_whatsapp_fallback"
                    }
                else:
                    error_text = await response.text()
                    logger.error(f"❌ FALLBACK: Erro n8n {response.status} - {error_text}")
                    return {"success": False, "error": f"n8n error {response.status}: {error_text}"}
                    
    except Exception as e:
        logger.error(f"❌ FALLBACK: Erro ao enviar via n8n: {e}")
        return {"success": False, "error": str(e)}

# ==========================================
# ENDPOINTS PRINCIPAIS
# ==========================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "3.0.0",
        "timestamp": datetime.now().isoformat(),
        "configuration": {
            "kommo_configured": bool(os.getenv("KOMMO_ACCESS_TOKEN")),
            "n8n_configured": bool(os.getenv("N8N_WEBHOOK_URL")),
            "vendedores_configurados": len(await get_vendedores_dinamicos()),
            "environment": "development"
        }
    }

@app.get("/vendedores")
async def get_vendedores():
    """Lista todos os vendedores disponíveis"""
    try:
        vendedores = await get_vendedores_dinamicos()
        return {
            "vendedores": vendedores,
            "total": len(vendedores),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/distribuicao/lead")
async def receber_distribuicao_lead(distribuicao: DistribuicaoPayload):
    """
    Recebe distribuição de lead do RD Station/Kommo e inicia conversa proativa
    """
    try:
        logger.info(f"📨 Distribuição recebida: Lead {distribuicao.lead_id} → Vendedor {distribuicao.vendedor_atribuido}")
        
        # Converter DistribuicaoPayload para ProactiveStart
        proactive_data = ProactiveStart(
            contact_id=distribuicao.contact_id,
            lead_id=distribuicao.lead_id,
            vendedor=distribuicao.vendedor_atribuido,
            area_atuacao=distribuicao.area_atuacao,
            trigger_type=distribuicao.trigger_type,
            lead_data=distribuicao.lead_data,
            custom_message=getattr(distribuicao, 'custom_message', None)
        )
        
        # Iniciar conversa proativa
        result = await start_proactive_conversation(proactive_data)
        
        if result.get("success"):
            return {
                "status": "success",
                "message": "Distribuição processada e conversa proativa iniciada",
                "lead_id": distribuicao.lead_id,
                "vendedor": distribuicao.vendedor_atribuido,
                "conversation_id": result.get("conversation_id"),
                "timestamp": datetime.now().isoformat()
            }
        else:
            logger.error(f"Erro ao iniciar conversa proativa: {result.get('error')}")
            return {
                "status": "error",
                "message": f"Erro ao iniciar conversa proativa: {result.get('error')}",
                "lead_id": distribuicao.lead_id,
                "vendedor": distribuicao.vendedor_atribuido
            }
            
    except Exception as e:
        logger.error(f"Erro ao processar distribuição: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/send-response")
async def receive_n8n_response(response_data: N8nResponse):
    """Recebe resposta do n8n e envia de volta para processar nota + WhatsApp"""
    try:
        logger.info(f"Resposta do n8n recebida: {response_data.conversation_id}")
        
        # Simplificado: Sempre envia para n8n processar (criar nota + enviar WhatsApp)
        # N8N tem permissões corretas e é especializado nisso
        
        # Extrair lead_id para envio
        parts = response_data.conversation_id.split("_")
        lead_id = None
        if len(parts) >= 3 and parts[-1].isdigit():
            lead_id = parts[-1]
        elif len(parts) >= 2 and parts[1].isdigit():
            lead_id = parts[1]
        
        # Preparar payload para n8n processar tudo
        payload = {
            "action": "create_note_and_send",
            "conversation_id": response_data.conversation_id,
            "response_text": response_data.response_text,
            "response_type": response_data.response_type,
            "confidence": getattr(response_data, 'confidence', 1.0),
            "lead_id": lead_id,
            "method": "n8n_direct",
            "timestamp": datetime.now().isoformat()
        }
        
        # Enviar para n8n que fará nota + WhatsApp
        result = await send_to_n8n(payload)
        
        if "error" not in result:
            logger.info("✅ Resposta enviada para n8n processar (nota + WhatsApp)")
            return {
                "success": True,
                "message": "Resposta processada pelo n8n (nota + WhatsApp)",
                "conversation_id": response_data.conversation_id,
                "method": "n8n_complete",
                "n8n_response": result
            }
        else:
            logger.error(f"Erro ao enviar para n8n: {result}")
            raise HTTPException(status_code=500, detail=f"Erro no n8n: {result.get('error')}")
            
    except Exception as e:
        logger.error(f"Erro ao processar resposta: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/webhooks/kommo")
async def kommo_webhook(webhook_data: Dict[str, Any]):
    """
    Webhook do Kommo para receber mensagens de chat
    """
    try:
        logger.info("Webhook do Kommo recebido")
        logger.info(f"Dados: {webhook_data}")
        
        # Verificar se é uma mensagem de chat
        if "chats" in webhook_data and "message" in webhook_data["chats"]:
            message_data = webhook_data["chats"]["message"]
            
            conversation_id = message_data.get("conversation_id")
            contact_id = message_data.get("contact_id")
            message_text = message_data.get("text", "")
            author_type = message_data.get("author", {}).get("type")
            
            logger.info(f"Mensagem de contato {contact_id}: '{message_text}'")
            logger.info(f"Autor: {author_type}")
            
            # Processar apenas mensagens de contatos (não de agentes)
            if author_type == "contact":
                # Buscar vendedores para contexto
                vendedores_dinamicos = await get_vendedores_dinamicos()
                
                # Buscar contexto da conversa
                conversation_context = _proactive_conversations.get(contact_id, {})
                vendedor = conversation_context.get("vendedor", "default")
                
                vendedor_config = vendedores_dinamicos.get(vendedor, {})
                
                # Preparar payload para n8n (MELHORADO COM SISTEMA DE AGENDAMENTO)
                payload = {
                    "conversation_id": conversation_id,
                    "contact_id": contact_id,
                    "message_text": message_text,
                    "timestamp": datetime.now().isoformat(),
                    "chat_type": "whatsapp",
                    "lead_id": conversation_context.get("lead_id"),
                    "contact_name": conversation_context.get("lead_data", {}).get("name", ""),
                    "proactive_context": {
                        "initiated_by_bot": conversation_context.get("initiated_by_bot", False),
                        "trigger_source": conversation_context.get("trigger_type"),
                        "first_response": conversation_context.get("first_response_received", False),
                        "initiated_at": conversation_context.get("initiated_at")
                    },
                    "vendor_context": {
                        "responsible_user": vendedor,
                        "phone_api": vendedor_config.get("phone_api"),
                        "display_name": vendedor_config.get("display_name"),
                        "area_atuacao": conversation_context.get("area_atuacao")
                    },
                    # DADOS PARA SUPABASE/AGENDAMENTO
                    "supabase_context": {
                        "vendedor_for_scheduling": vendedor,
                        "agenda_table": f"agenda_{vendedor.lower()}" if vendedor else None,
                        "client_id": contact_id,
                        "lead_id": conversation_context.get("lead_id"),
                        "conversation_active": True,
                        "scheduling_enabled": True
                    }
                }
                
                # Enviar para n8n (IA)
                result = await send_to_n8n(payload)
                
                if "error" not in result:
                    # Marcar primeira resposta recebida
                    if contact_id in _proactive_conversations:
                        _proactive_conversations[contact_id]["first_response_received"] = True
                    
                    logger.info(f"Mensagem processada e enviada para n8n: {conversation_id}")
                    return {"status": "processed", "conversation_id": conversation_id}
                else:
                    logger.error(f"Erro ao enviar para n8n: {result}")
                    return {"status": "error", "message": result.get("error")}
            else:
                return {"status": "ignored", "reason": "Message from agent or system"}
        else:
            return {"status": "ignored", "reason": "Not a chat message"}
            
    except Exception as e:
        logger.error(f"Erro ao processar webhook do Kommo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# AGENDAMENTO E SISTEMA SUPABASE
# ==========================================

@app.post("/agendamento/request")
async def request_agendamento(agendamento: AgendamentoPayload):
    """
    Endpoint para solicitar agendamento - integração com Supabase via n8n
    
    Este endpoint identifica o vendedor e envia dados completos para n8n/Supabase
    """
    try:
        vendedor_info = None
        
        # 1. Tentar identificar vendedor por conversation_id
        if agendamento.conversation_id:
            for contact_id, conversation in _proactive_conversations.items():
                if conversation.get("conversation_id") == agendamento.conversation_id:
                    vendedor_info = {
                        "name": conversation.get("vendedor"),
                        "source": "conversation_id",
                        "area_atuacao": conversation.get("area_atuacao"),
                        "lead_data": conversation.get("lead_data", {})
                    }
                    break
        
        # 2. Tentar identificar por contact_id
        if not vendedor_info and agendamento.contact_id in _proactive_conversations:
            conversation = _proactive_conversations[agendamento.contact_id]
            vendedor_info = {
                "name": conversation.get("vendedor"),
                "source": "contact_id",
                "area_atuacao": conversation.get("area_atuacao"),
                "lead_data": conversation.get("lead_data", {})
            }
        
        # 3. Usar vendedor solicitado como fallback
        if not vendedor_info and agendamento.vendedor_requested:
            vendedor_info = {
                "name": agendamento.vendedor_requested,
                "source": "manual_request",
                "area_atuacao": "nao_identificada",
                "lead_data": {}
            }
        
        # 4. Fallback final
        if not vendedor_info:
            vendedor_info = {
                "name": "João",  # Vendedor padrão
                "source": "default_fallback",
                "area_atuacao": "nao_identificada",
                "lead_data": {}
            }
        
        vendedor_name = vendedor_info["name"]
        vendedores_dinamicos = await get_vendedores_dinamicos()
        
        vendedor_config = await get_vendedor_whatsapp_config(vendedor_name)
        
        # Preparar payload completo para n8n/Supabase
        supabase_payload = {
            "action": "agendamento_request",
            "timestamp": datetime.now().isoformat(),
            "contact_id": agendamento.contact_id,
            "lead_id": agendamento.lead_id,
            "conversation_id": agendamento.conversation_id,
            
            # DADOS DO VENDEDOR PARA ACESSO À AGENDA
            "vendedor": {
                "name": vendedor_name,
                "display_name": vendedor_config.get("display_name"),
                "phone_api": vendedor_config.get("phone_api"),
                "area_atuacao": vendedor_info.get("area_atuacao"),
                "identification_source": vendedor_info.get("source")
            },
            
            # DADOS DO AGENDAMENTO
            "agenda_data": agendamento.agenda_data,
            
            # DADOS DO CLIENTE
            "client_data": {
                **vendedor_info.get("lead_data", {}),
                **(agendamento.client_data or {})
            },
            
            # METADADOS PARA SUPABASE
            "supabase_action": "insert_agendamento",
            "table_prefix": f"agenda_{vendedor_name.lower()}",
            "priority": "normal"
        }
        
        # Enviar para n8n (que processará e enviará para Supabase)
        result = await send_to_n8n(supabase_payload)
        
        return {
            "status": "success",
            "message": f"Agendamento solicitado para {vendedor_config.get('display_name')}",
            "vendedor": vendedor_name,
            "n8n_response": result,
            "supabase_ready": True,
            "agenda_access": f"agenda_{vendedor_name.lower()}"
        }
        
    except Exception as e:
        logger.error(f"Erro ao processar agendamento: {e}")
        return {
            "status": "error",
            "message": str(e),
            "available_endpoints": [
                "GET /vendedores",
                "GET /vendedor/by-contact/{contact_id}",
                "GET /vendedor/by-lead/{lead_id}"
            ]
        }

# ==========================================
# ENDPOINTS FALTANTES
# ==========================================

@app.get("/vendedores/config")
async def get_vendedores_config_endpoint():
    """Endpoint para obter configuração de vendedores"""
    try:
        config = await get_vendedores_config()
        return {
            "status": "success",
            "data": config,
            "total_vendedores": len(config.get("vendedores", {}))
        }
    except Exception as e:
        logger.error(f"Erro ao obter config vendedores: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

@app.post("/test-whatsapp")
async def test_whatsapp_integration(payload: Dict[str, Any]):
    """Endpoint para testar integração WhatsApp"""
    try:
        logger.info(f"Teste WhatsApp recebido: {payload}")
        
        # Simular envio de mensagem WhatsApp
        test_result = {
            "status": "success",
            "message": "Teste WhatsApp executado com sucesso",
            "payload_received": payload,
            "timestamp": datetime.now().isoformat(),
            "method": "whatsapp_business_api"
        }
        
        return test_result
        
    except Exception as e:
        logger.error(f"Erro no teste WhatsApp: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

@app.post("/proactive/start")
async def start_proactive_endpoint(proactive_data: ProactiveStart):
    """Endpoint para iniciar conversa proativa"""
    try:
        logger.info(f"Iniciando conversa proativa: {proactive_data}")
        
        # Usar a função existente
        result = await start_proactive_conversation(proactive_data)
        
        return {
            "status": "success",
            "message": "Conversa proativa iniciada",
            "data": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erro ao iniciar conversa proativa: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

@app.post("/bot/control")
async def bot_control(command_data: BotCommand):
    """Controle do bot - pausar/reativar por contato"""
    try:
        contact_id = command_data.contact_id
        command = command_data.command.lower()
        
        if command == "pause":
            # Cache para marcar bot como pausado
            _bot_status_cache[contact_id] = {
                "status": "paused",
                "timestamp": datetime.now().isoformat(),
                "paused_by": "manual_control"
            }
            
            logger.info(f"Bot pausado para contato {contact_id}")
            return {
                "status": "success",
                "message": f"Bot pausado para contato {contact_id}",
                "contact_id": contact_id,
                "action": "paused"
            }
            
        elif command == "resume":
            # Remove do cache para reativar
            if contact_id in _bot_status_cache:
                del _bot_status_cache[contact_id]
            
            logger.info(f"Bot reativado para contato {contact_id}")
            return {
                "status": "success",
                "message": f"Bot reativado para contato {contact_id}",
                "contact_id": contact_id,
                "action": "resumed"
            }
            
        elif command == "status":
            # Verificar status atual
            status = _bot_status_cache.get(contact_id, {"status": "active"})
            return {
                "status": "success",
                "contact_id": contact_id,
                "bot_status": status.get("status", "active"),
                "timestamp": status.get("timestamp"),
                "paused_by": status.get("paused_by")
            }
            
        else:
            raise HTTPException(status_code=400, detail="Comando inválido. Use: pause, resume ou status")
            
    except Exception as e:
        logger.error(f"Erro no controle do bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/bot/status")
async def get_bot_status():
    """Ver status geral de todos os bots"""
    try:
        total_paused = len(_bot_status_cache)
        total_active = len(_proactive_conversations) - total_paused
        
        return {
            "status": "success",
            "summary": {
                "total_conversations": len(_proactive_conversations),
                "active_bots": max(0, total_active),
                "paused_bots": total_paused
            },
            "paused_contacts": list(_bot_status_cache.keys()),
            "active_conversations": list(_proactive_conversations.keys()),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter status dos bots: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/bot/pause/{contact_id}")
async def pause_bot_quick(contact_id: int):
    """Pausar bot rapidamente via URL"""
    try:
        _bot_status_cache[contact_id] = {
            "status": "paused",
            "timestamp": datetime.now().isoformat(),
            "paused_by": "quick_pause"
        }
        
        return {
            "status": "success",
            "message": f"Bot pausado para contato {contact_id}",
            "contact_id": contact_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/bot/resume/{contact_id}")
async def resume_bot_quick(contact_id: int):
    """Reativar bot rapidamente via URL"""
    try:
        if contact_id in _bot_status_cache:
            del _bot_status_cache[contact_id]
        
        return {
            "status": "success",
            "message": f"Bot reativado para contato {contact_id}",
            "contact_id": contact_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/config/check")
async def config_check():
    """Verificação de configuração completa"""
    return {
        "kommo_api_url": "Configurado" if os.getenv("KOMMO_API_URL") else "Não configurado",
        "kommo_access_token": "Configurado" if os.getenv("KOMMO_ACCESS_TOKEN") else "Não configurado",
        "n8n_webhook_url": "Configurado" if os.getenv("N8N_WEBHOOK_URL") else "Não configurado",
        "n8n_api_key": "Configurado" if os.getenv("N8N_API_KEY") else "Não configurado",
        "vendedores_cache": len(_vendedores_cache),
        "conversations_active": len(_proactive_conversations),
        "timestamp": datetime.now().isoformat()
    }

# ==========================================
# FUNÇÕES AUXILIARES ADICIONAIS
# ==========================================

async def get_vendedores_config():
    """Retorna configuração completa dos vendedores"""
    vendedores_dinamicos = await get_vendedores_dinamicos()
    
    return {
        "vendedores": vendedores_dinamicos,
        "total": len(vendedores_dinamicos),
        "source": "kommo_api",
        "cache_updated": _last_vendedores_update.isoformat() if _last_vendedores_update else None,
        "available_areas": [
            "previdenciario",
            "trabalhista", 
            "civil",
            "criminal",
            "tributario"
        ]
    }

# ==========================================
# PONTO DE ENTRADA
# ==========================================

if __name__ == "__main__":
    logger.info("Iniciando Kommo-n8n Integration API v3.0")
    logger.info("Funcionalidades ativas:")
    logger.info("- Distribuição automática de leads")
    logger.info("- Mensagens proativas via WhatsApp Business")
    logger.info("- Sistema de agendamento integrado")
    logger.info("- Controle de bot em tempo real")
    logger.info("- Integração completa Kommo + n8n + Supabase")
    
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)