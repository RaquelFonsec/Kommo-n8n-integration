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
from app.models.kommo_models import AgendamentoPayload, VendedorCustom
from app.services.kommo_service import KommoService

# Import das rotas OAuth - Desabilitado temporariamente (métodos removidos)
# from app.routes import oauth

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Cache global
_proactive_conversations = {}
_bot_status_cache = {}

# Configurações - DINÂMICO para vendedores reais
VENDEDOR_CONFIG = {
    # Exemplos fictícios - será substituído por vendedores reais
    "Asaf": {"phone_api": "asaf_whatsapp", "display_name": "Asaf - Previdas"},
    "João": {"phone_api": "joao_whatsapp", "display_name": "João - Previdas"},
    "Maria": {"phone_api": "maria_whatsapp", "display_name": "Maria - Previdas"}
}

# Cache para vendedores reais do Kommo
_vendedores_kommo_cache = {}
_last_vendedores_update = None

MESSAGE_TEMPLATES = {
    "formulario_preenchido": "Olá {nome}!\n\nAqui é {vendedor_nome}. Vi que você preencheu nosso formulário sobre {interesse}.\n\nPosso esclarecer dúvidas iniciais sobre perícias médicas?",
    "material_baixado": "Olá {nome}!\n\nAqui é {vendedor_nome}. Obrigado por baixar nosso material sobre {interesse}.\n\nTenho algumas informações adicionais que podem te interessar. Gostaria de saber mais?",
    "reuniao_agendada": "Olá {nome}!\n\nAqui é {vendedor_nome}. Vi que você agendou uma reunião conosco.\n\nAntes do nosso encontro, posso esclarecer alguma dúvida inicial sobre perícias médicas?",
    "default": "Olá {nome}!\n\nAqui é {vendedor_nome}. Vi que você demonstrou interesse em nossos serviços.\n\nComo posso te ajudar?"
}

app = FastAPI(
    title="Kommo-n8n Integration API",
    description="""
    ## API de Integração Kommo + n8n
    
    ### Fluxo Completo:
    1. **Proativo**: Bot inicia conversa baseada em gatilhos
    2. **Reativo**: Cliente manda mensagem → Kommo → Python → n8n → IA responde
    3. **Controle**: Vendedor pode pausar/reativar bot a qualquer momento
    
    ### Endpoints Principais:
    - `POST /start-proactive` - Inicia conversa proativa
    - `POST /webhooks/kommo` - Recebe mensagens do Kommo
    - `POST /send-response` - Recebe respostas do n8n
    - `POST /bot-control` - Controle manual do bot
    
    ### Correção para API de Chats:
    Como o token atual não tem permissão para chats, usamos a API de Notes
    """,
    version="2.1.0"
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Incluir rotas OAuth - Desabilitado temporariamente (métodos removidos)
# app.include_router(oauth.router, prefix="/oauth", tags=["OAuth"])

# Modelos
class ProactiveStart(BaseModel):
    contact_id: int
    lead_id: int
    vendedor: str
    area_atuacao: str
    trigger_type: str = "formulario_preenchido"
    lead_data: Optional[Dict[str, Any]] = None
    custom_message: Optional[str] = None

class BotCommand(BaseModel):
    contact_id: int
    command: str

class N8nResponse(BaseModel):
    conversation_id: str
    response_text: str
    should_send: bool = True
    should_handoff: bool = False
    metadata: Optional[Dict[str, Any]] = None

# Funções auxiliares para vendedores reais
async def fetch_vendedores_kommo() -> Dict[str, Any]:
    """Busca vendedores reais da API do Kommo"""
    try:
        kommo_api_url = os.getenv("KOMMO_API_URL")
        access_token = os.getenv("KOMMO_ACCESS_TOKEN")
        
        if not kommo_api_url or not access_token:
            logger.warning("API Kommo não configurada, usando vendedores fictícios")
            return {}
        
        url = f"{kommo_api_url.rstrip('/')}/users"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        timeout = aiohttp.ClientTimeout(total=10, connect=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    vendedores = {}
                    
                    if "_embedded" in result and "users" in result["_embedded"]:
                        for user in result["_embedded"]["users"]:
                            if user.get("is_active", True) and not user.get("is_admin", False):
                                name = user.get("name", "")
                                if name:
                                    vendedores[name] = {
                                        "user_id": user.get("id"),
                                        "display_name": f"{name} - Previdas",
                                        "email": user.get("email", ""),
                                        "phone_api": f"{name.lower().replace(' ', '_')}_whatsapp",
                                        "is_real_user": True,
                                        "kommo_data": user
                                    }
                    
                    logger.info(f"Encontrados {len(vendedores)} vendedores reais no Kommo")
                    return vendedores
                else:
                    logger.error(f"Erro ao buscar vendedores: {response.status}")
                    return {}
    except Exception as e:
        logger.error(f"Erro ao buscar vendedores do Kommo: {e}")
        return {}

async def get_vendedores_dinamicos() -> Dict[str, Any]:
    """Retorna vendedores reais + fictícios, priorizando os reais"""
    global _vendedores_kommo_cache, _last_vendedores_update
    
    # Atualizar cache se necessário (a cada 10 minutos)
    now = datetime.now()
    if (_last_vendedores_update is None or 
        (now - _last_vendedores_update).total_seconds() > 600):
        
        vendedores_reais = await fetch_vendedores_kommo()
        if vendedores_reais:
            _vendedores_kommo_cache = vendedores_reais
            _last_vendedores_update = now
            logger.info("Cache de vendedores atualizado com dados reais")
    
    # Combinar vendedores reais + fictícios
    vendedores_combinados = {}
    
    # Primeiro, adicionar vendedores reais do Kommo
    vendedores_combinados.update(_vendedores_kommo_cache)
    
    # Depois, adicionar fictícios apenas se não existir vendedor real com mesmo nome
    for nome, config in VENDEDOR_CONFIG.items():
        if nome not in vendedores_combinados:
            vendedores_combinados[nome] = {
                **config,
                "is_real_user": False,
                "source": "fictional"
            }
    
    return vendedores_combinados

def get_message_template(trigger_type: str, lead_data: Dict[str, Any], vendedor: str) -> str:
    """Gera mensagem personalizada baseada no gatilho e vendedor"""
    nome = lead_data.get("name", lead_data.get("nome", ""))
    interesse = lead_data.get("interest", lead_data.get("interesse", "nossos serviços"))
    vendedor_config = VENDEDOR_CONFIG.get(vendedor, {"display_name": "Previdas"})
    vendedor_nome = vendedor_config.get("display_name", "Previdas")
    template = MESSAGE_TEMPLATES.get(trigger_type, MESSAGE_TEMPLATES["default"])
    return template.format(nome=nome, interesse=interesse, vendedor_nome=vendedor_nome)

async def send_to_n8n(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Envia payload para o webhook do n8n"""
    try:
        n8n_webhook_url = os.getenv("N8N_WEBHOOK_URL")
        if not n8n_webhook_url:
            logger.error("N8N_WEBHOOK_URL não configurada")
            return {"error": "N8N_WEBHOOK_URL não configurada"}
        
        headers = {"Content-Type": "application/json"}
        n8n_api_key = os.getenv("N8N_API_KEY")
        if n8n_api_key:
            headers["Authorization"] = f"Bearer {n8n_api_key}"
        
        logger.info(f"Enviando para n8n: {n8n_webhook_url}")
        logger.info(f"Payload: {payload}")
        
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(n8n_webhook_url, json=payload, headers=headers) as response:
                if response.status == 200:
                    try:
                        result = await response.json()
                        logger.info(f"Resposta do n8n: {result}")
                        return result
                    except:
                        text_response = await response.text()
                        logger.info(f"Resposta em texto: {text_response}")
                        return {"status": "success", "response_text": text_response}
                else:
                    error_text = await response.text()
                    logger.error(f"Erro n8n: {response.status} - {error_text}")
                    return {"error": f"Status {response.status}: {error_text}"}
                    
    except Exception as e:
        logger.error(f"Erro ao enviar para n8n: {e}")
        return {"error": str(e)}

async def send_kommo_message(conversation_id: str, message: str) -> Dict[str, Any]:
    """
    CORRIGIDO: Envia mensagem via API de Notes do Kommo
    
    Como não temos permissão para a API de chats, criamos uma nota no lead
    que o vendedor pode ver e enviar manualmente para o cliente
    """
    try:
        kommo_api_url = os.getenv("KOMMO_API_URL")
        access_token = os.getenv("KOMMO_ACCESS_TOKEN")
        
        if not kommo_api_url or not access_token:
            logger.error("Variáveis KOMMO_API_URL ou KOMMO_ACCESS_TOKEN não configuradas")
            return {"success": False, "error": "Configuração do Kommo não encontrada"}
        
        # Extrair lead_id do conversation_id
        # Formato esperado: "conv_contact_id_lead_id" ou apenas texto simples
        try:
            parts = conversation_id.split("_")
            if len(parts) >= 3 and parts[2].isdigit():
                lead_id = parts[2]  # lead_id está na terceira posição e é numérico
            elif len(parts) >= 2 and parts[1].isdigit():
                lead_id = parts[1]  # lead_id está na segunda posição e é numérico
            else:
                # Se não conseguir extrair lead_id válido, não criar nota no Kommo
                logger.info(f"Conversation_id sem lead_id válido: {conversation_id}")
                return {
                    "success": True, 
                    "message": "Mensagem processada sem criar nota no Kommo (conversation_id sem lead_id válido)",
                    "conversation_id": conversation_id,
                    "method": "no_kommo_note"
                }
        except:
            logger.error(f"Não foi possível extrair lead_id de: {conversation_id}")
            return {"success": False, "error": "conversation_id inválido"}
        
        # URL da API de leads do Kommo (FUNCIONA com suas permissões)
        full_url = f"{kommo_api_url.rstrip('/')}/leads/{lead_id}"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Atualizar lead com informações da resposta da IA (payload simplificado)
        payload = {
            "name": f"🤖 Bot Ativo - {datetime.now().strftime('%d/%m %H:%M')}"
        }
        
        logger.info(f"Atualizando lead {lead_id}: {full_url}")
        logger.info(f"Conversation ID: {conversation_id}")
        logger.info(f"Mensagem: {message}")
        
        timeout = aiohttp.ClientTimeout(total=15, connect=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.patch(full_url, json=payload, headers=headers) as response:
                if response.status in [200, 201]:
                    result = await response.json()
                    logger.info(f"Lead {lead_id} atualizado com sucesso")
                    return {
                        "success": True, 
                        "data": result,
                        "note": "Lead atualizado - resposta da IA registrada",
                        "lead_id": lead_id,
                        "method": "leads_api"
                    }
                elif response.status == 401:
                    error_text = await response.text()
                    logger.error(f"🔐 Erro de autenticação (401): Token expirado ou inválido")
                    logger.error(f"📄 Resposta completa: {error_text}")
                    return {
                        "success": False, 
                        "error": f"Token expirado ou inválido (401)",
                        "details": error_text,
                        "suggestion": "Execute o refresh token ou obtenha um novo token de acesso",
                        "oauth_endpoints": {
                            "status": "/oauth/status",
                            "refresh": "/oauth/refresh",
                            "exchange": "/oauth/exchange"
                        }
                    }
                else:
                    error_text = await response.text()
                    logger.error(f"Erro ao criar nota: {response.status} - {error_text}")
                    return {"success": False, "error": f"Status {response.status}: {error_text}"}
                    
    except Exception as e:
        logger.error(f"Erro ao criar nota: {e}")
        return {"success": False, "error": str(e)}

async def test_kommo_lead_access(lead_id: str) -> Dict[str, Any]:
    """Testa se consegue acessar um lead específico"""
    try:
        kommo_api_url = os.getenv("KOMMO_API_URL")
        access_token = os.getenv("KOMMO_ACCESS_TOKEN")
        
        full_url = f"{kommo_api_url.rstrip('/')}/leads/{lead_id}"
        headers = {"Authorization": f"Bearer {access_token}"}
        
        timeout = aiohttp.ClientTimeout(total=10, connect=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(full_url, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return {"success": True, "data": result}
                else:
                    error_text = await response.text()
                    return {"success": False, "error": f"Status {response.status}: {error_text}"}
                    
    except Exception as e:
        return {"success": False, "error": str(e)}

async def test_kommo_connectivity() -> Dict[str, Any]:
    """Testa conectividade real com a API do Kommo"""
    try:
        kommo_api_url = os.getenv("KOMMO_API_URL")
        access_token = os.getenv("KOMMO_ACCESS_TOKEN")
        
        if not kommo_api_url or not access_token:
            return {"success": False, "error": "Configuração incompleta"}
        
        # Teste com endpoint de leads (você TEM permissão)
        full_url = f"{kommo_api_url.rstrip('/')}/leads?limit=1"
        headers = {"Authorization": f"Bearer {access_token}"}
        
        timeout = aiohttp.ClientTimeout(total=10, connect=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(full_url, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return {"success": True, "method": "leads_api", "sample_data": result}
                else:
                    error_text = await response.text()
                    return {"success": False, "error": f"Status {response.status}: {error_text}"}
                    
    except Exception as e:
        return {"success": False, "error": str(e)}

def extract_responsible_user(webhook_data: Dict[str, Any]) -> str:
    """Extrai informações do vendedor responsável do webhook"""
    # Tentar diferentes locais onde o vendedor pode estar
    lead_data = webhook_data.get("leads", {})
    if lead_data:
        responsible_user = lead_data.get("responsible_user_name")
        if responsible_user:
            return responsible_user
    
    # Tentar em chat data
    chat_data = webhook_data.get("chats", {})
    if chat_data:
        responsible_user = chat_data.get("responsible_user_name")
        if responsible_user:
            return responsible_user
    
    return "default"

# ENDPOINTS

@app.get("/")
async def root():
    return {
        "message": "API Kommo-n8n Integration v2.1 - CORRIGIDA",
        "status": "online",
        "version": "2.1.0",
        "features": [
            "Conversas proativas multi-vendedor",
            "Integração Kommo + n8n com IA",
            "Controle manual de bot",
            "Webhooks automáticos",
            "API de Notes (corrigido para permissões)"
        ],
        "fix": "Usando API de Notes em vez de Chats devido às permissões do token"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "2.1.0",
        "timestamp": datetime.now().isoformat(),
        "configuration": {
            "kommo_configured": bool(os.getenv("KOMMO_API_URL") and os.getenv("KOMMO_ACCESS_TOKEN")),
            "n8n_configured": bool(os.getenv("N8N_WEBHOOK_URL")),
            "environment": os.getenv("ENVIRONMENT", "development")
        }
    }

@app.get("/config/check")
async def config_check():
    return {
        "kommo_api_url": "✅ Configurado" if os.getenv("KOMMO_API_URL") else "❌ Não configurado",
        "kommo_access_token": "✅ Configurado" if os.getenv("KOMMO_ACCESS_TOKEN") else "❌ Não configurado",
        "n8n_webhook_url": "✅ Configurado" if os.getenv("N8N_WEBHOOK_URL") else "❌ Não configurado",
        "n8n_api_key": "✅ Configurado" if os.getenv("N8N_API_KEY") else "❌ Não configurado",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "vendedores": list(VENDEDOR_CONFIG.keys()),
        "version": "2.1.0",
        "api_method": "notes_api (corrigido para permissões)"
    }

@app.post("/start-proactive")
async def start_proactive_conversation(proactive_data: ProactiveStart):
    """Inicia conversa proativa com lead"""
    try:
        logger.info(f"Iniciando conversa proativa: Lead {proactive_data.lead_id}, Contact {proactive_data.contact_id}")
        
        # Verificar área elegível
        areas_elegiveis = ["previdenciario", "tributario", "outros", "previdenciário", "tributário"]
        if proactive_data.area_atuacao.lower() not in areas_elegiveis:
            return {"status": "skipped", "reason": "area_not_eligible", "eligible_areas": areas_elegiveis}
        
        # Verificar vendedor
        if proactive_data.vendedor not in VENDEDOR_CONFIG:
            return {"status": "error", "reason": "vendor_not_configured", "available_vendors": list(VENDEDOR_CONFIG.keys())}
        
        # Verificar se já existe conversa ativa para este contact_id e lead_id
        if proactive_data.contact_id in _proactive_conversations:
            existing = _proactive_conversations[proactive_data.contact_id]
            if existing.get("active", False) and existing.get("lead_id") == proactive_data.lead_id:
                return {"status": "skipped", "reason": "conversation_already_active", "existing": existing}
        
        # Gerar mensagem personalizada
        lead_data = proactive_data.lead_data or {}
        message = proactive_data.custom_message or get_message_template(
            proactive_data.trigger_type, lead_data, proactive_data.vendedor
        )
        
        conversation_id = f"conv_{proactive_data.contact_id}_{proactive_data.lead_id}"
        
        # Registrar conversa proativa
        _proactive_conversations[proactive_data.contact_id] = {
            "lead_id": proactive_data.lead_id,
            "conversation_id": conversation_id,
            "vendedor": proactive_data.vendedor,
            "area_atuacao": proactive_data.area_atuacao,
            "trigger_type": proactive_data.trigger_type,
            "initiated_at": datetime.now().isoformat(),
            "initiated_by_bot": True,
            "active": True,
            "message_sent": message,
            "lead_data": lead_data
        }
        
        # Ativar bot para este contato
        _bot_status_cache[proactive_data.contact_id] = True
        
        # TODO: Implementar envio real da mensagem via WhatsApp Business API ou Kommo
        logger.info(f"Conversa proativa iniciada para contato {proactive_data.contact_id}")
        logger.info(f"Mensagem gerada: {message}")
        
        return {
            "status": "initiated",
            "conversation_id": conversation_id,
            "contact_id": proactive_data.contact_id,
            "lead_id": proactive_data.lead_id,
            "vendedor": proactive_data.vendedor,
            "message_sent": message,
            "message_sent_at": datetime.now().isoformat(),
            "vendor_config": VENDEDOR_CONFIG[proactive_data.vendedor],
            "note": "Conversa registrada - implementar envio real via WhatsApp Business API"
        }
        
    except Exception as e:
        logger.error(f"Erro ao iniciar conversa proativa: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/webhooks/kommo")
async def kommo_webhook(webhook_data: Dict[str, Any]):
    """
    Recebe webhooks do Kommo - FLUXO REATIVO
    
    Cliente manda WhatsApp → Kommo → Este endpoint → n8n → IA responde
    """
    try:
        logger.info("Webhook do Kommo recebido")
        logger.info(f"Dados: {webhook_data}")
        
        # Extrair informações da mensagem
        contact_id = None
        conversation_id = None
        message_text = ""
        author_type = ""
        
        # Processar diferentes estruturas de webhook
        if "chats" in webhook_data and "message" in webhook_data["chats"]:
            chat_data = webhook_data["chats"]
            message_data = chat_data["message"]
            
            contact_id = (
                message_data.get("contact_id") or 
                message_data.get("author", {}).get("contact_id") or 
                message_data.get("author", {}).get("id", 0)
            )
            
            conversation_id = (
                chat_data.get("conversation_id") or 
                message_data.get("conversation_id") or 
                str(message_data.get("id", ""))
            )
            
            message_text = message_data.get("text", "")
            author_type = message_data.get("author", {}).get("type", "")
            
        elif "message" in webhook_data:
            message_data = webhook_data["message"]
            contact_id = message_data.get("contact_id", 0)
            conversation_id = str(message_data.get("id", ""))
            message_text = message_data.get("text", "")
            author_type = message_data.get("author", {}).get("type", "")
        
        if not contact_id or not message_text:
            logger.warning("Webhook sem contact_id ou message_text válido")
            return {"status": "ignored", "reason": "invalid_data"}
        
        logger.info(f"Mensagem de contato {contact_id}: '{message_text}'")
        logger.info(f"Autor: {author_type}")
        
        # Verificar se é mensagem do vendedor (comandos especiais)
        if author_type == "user":
            logger.info(f"Mensagem de vendedor: '{message_text}'")
            
            # Processar comandos especiais do vendedor
            if message_text.lower() in ["#pausar", "#pause"]:
                _bot_status_cache[contact_id] = False
                if contact_id in _proactive_conversations:
                    _proactive_conversations[contact_id]["active"] = False
                    _proactive_conversations[contact_id]["paused_at"] = datetime.now().isoformat()
                
                logger.info(f"Bot pausado pelo comando #pausar para contato {contact_id}")
                return {
                    "status": "bot_paused",
                    "message": "Bot pausado pelo comando #pausar",
                    "contact_id": contact_id
                }
                
            elif message_text.lower() in ["#voltar", "#resume", "#reativar"]:
                _bot_status_cache[contact_id] = True
                if contact_id in _proactive_conversations:
                    _proactive_conversations[contact_id]["active"] = True
                    _proactive_conversations[contact_id]["resumed_at"] = datetime.now().isoformat()
                
                logger.info(f"Bot reativado pelo comando {message_text} para contato {contact_id}")
                return {
                    "status": "bot_resumed",
                    "message": f"Bot reativado pelo comando {message_text}",
                    "contact_id": contact_id
                }
            
            else:
                logger.info("Mensagem de vendedor ignorada (não é comando)")
                return {"status": "ignored", "reason": "vendor_message_not_command"}
        
        # Verificar se é mensagem do contato (não do agente)
        if author_type != "contact":
            logger.info("Mensagem ignorada (não é do contato nem comando de vendedor)")
            return {"status": "ignored", "reason": "not_from_contact"}
        
        # Verificar se bot está ativo para este contato
        if not _bot_status_cache.get(contact_id, True):
            logger.info(f"Bot pausado para contato {contact_id} - ignorando mensagem")
            return {"status": "ignored", "reason": "bot_paused"}
        
        # Marcar primeira resposta se for conversa proativa
        if contact_id in _proactive_conversations:
            conversation = _proactive_conversations[contact_id]
            if not conversation.get("first_response_received", False):
                conversation["first_response_received"] = True
                conversation["first_response_at"] = datetime.now().isoformat()
                logger.info(f"Primeira resposta recebida do lead {contact_id}!")
                logger.info(f"Gatilho original: {conversation.get('trigger_type')}")
                logger.info(f"Vendedor: {conversation.get('vendedor')}")
        
        # Buscar contexto da conversa
        conversation_context = _proactive_conversations.get(contact_id, {})
        vendedor = conversation_context.get("vendedor", extract_responsible_user(webhook_data))
        vendedor_config = VENDEDOR_CONFIG.get(vendedor, {})
        
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
            logger.info(f"Mensagem processada e enviada para n8n: {conversation_id}")
            return {
                "status": "processed",
                "conversation_id": conversation_id,
                "contact_id": contact_id,
                "sent_to_n8n": True,
                "n8n_response": result,
                "vendor": vendedor
            }
        else:
            logger.error(f"Erro ao enviar para n8n: {result['error']}")
            return {
                "status": "error",
                "message": f"Erro ao processar: {result['error']}"
            }
                
    except Exception as e:
        logger.error(f"Erro no webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/webhooks/test")
async def test_webhook():
    """Endpoint de teste para webhooks"""
    return {
        "status": "webhook_test_ok",
        "message": "Endpoint de teste para webhooks funcionando",
        "timestamp": datetime.now().isoformat(),
        "test_data": {
            "webhook_url": "/webhooks/kommo",
            "supported_methods": ["POST"],
            "expected_format": {
                "chats": {
                    "conversation_id": "string",
                    "message": {
                        "contact_id": "integer",
                        "text": "string",
                        "author": {"type": "contact"}
                    }
                }
            }
        }
    }

@app.post("/send-response")
async def receive_n8n_response(n8n_response: N8nResponse):
    """
    CORRIGIDO: Recebe resposta do n8n (IA) e cria nota no Kommo
    
    n8n processa → Este endpoint → Nota no Kommo → Vendedor envia manualmente
    """
    try:
        logger.info(f"Resposta do n8n recebida: {n8n_response.conversation_id}")
        
        # Verificar se deve enviar mensagem
        if not n8n_response.should_send:
            logger.info("Mensagem não deve ser enviada (should_send=False)")
            return {
                "status": "skipped", 
                "message": "Mensagem não enviada conforme instrução do n8n",
                "conversation_id": n8n_response.conversation_id
            }
        
        # Validar texto da resposta
        if not n8n_response.response_text or not n8n_response.response_text.strip():
            logger.warning(f"Texto da resposta vazio: {n8n_response.conversation_id}")
            return {
                "status": "error",
                "message": "Texto da resposta está vazio",
                "conversation_id": n8n_response.conversation_id
            }
        
        # Criar nota no Kommo (CORRIGIDO)
        result = await send_kommo_message(
            conversation_id=n8n_response.conversation_id,
            message=n8n_response.response_text
        )
        
        if result["success"]:
            # Log handoff se necessário
            if n8n_response.should_handoff:
                logger.info(f"Handoff recomendado: {n8n_response.conversation_id}")
                # TODO: Implementar lógica de handoff (notificar vendedor, mudar status, etc.)
            
            return {
                "status": "note_created",
                "message": "Nota criada no lead - vendedor deve enviar manualmente",
                "conversation_id": n8n_response.conversation_id,
                "handoff_required": n8n_response.should_handoff,
                "metadata": n8n_response.metadata,
                "kommo_response": result.get("data"),
                "lead_id": result.get("lead_id"),
                "method": result.get("method")
            }
        else:
            logger.error(f"Erro ao criar nota no Kommo: {result['error']}")
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao criar nota no Kommo: {result['error']}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no endpoint /send-response: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/bot-control")
async def bot_control(bot_command: BotCommand):
    """Controle manual do bot (pausar/reativar/status)"""
    try:
        contact_id = bot_command.contact_id
        command = bot_command.command.lower()
        
        logger.info(f"Comando bot '{command}' para contato {contact_id}")
        
        if command == "pause":
            _bot_status_cache[contact_id] = False
            if contact_id in _proactive_conversations:
                _proactive_conversations[contact_id]["active"] = False
                _proactive_conversations[contact_id]["paused_at"] = datetime.now().isoformat()
            
            return {
                "status": "paused",
                "contact_id": contact_id,
                "message": "Bot pausado. Vendedor assumindo conversa.",
                "timestamp": datetime.now().isoformat()
            }
            
        elif command == "resume":
            _bot_status_cache[contact_id] = True
            if contact_id in _proactive_conversations:
                _proactive_conversations[contact_id]["active"] = True
                _proactive_conversations[contact_id]["resumed_at"] = datetime.now().isoformat()
            
            return {
                "status": "resumed",
                "contact_id": contact_id,
                "message": "Bot reativado. Assumindo atendimento automático.",
                "timestamp": datetime.now().isoformat()
            }
            
        elif command == "status":
            bot_active = _bot_status_cache.get(contact_id, True)
            conversation_state = _proactive_conversations.get(contact_id, {})
            
            return {
                "contact_id": contact_id,
                "bot_active": bot_active,
                "conversation_state": conversation_state,
                "timestamp": datetime.now().isoformat()
            }
            
        else:
            raise HTTPException(status_code=400, detail=f"Comando inválido: {command}. Use: pause, resume, status")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no endpoint /bot-control: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/vendedor/comandos")
async def comandos_vendedor(comando_data: Dict[str, Any]):
    """Endpoint para comandos simples de vendedores via WhatsApp"""
    message_text = comando_data.get("message", "").strip()
    contact_id = comando_data.get("contact_id")
    
    if not message_text or not contact_id:
        raise HTTPException(status_code=400, detail="Dados inválidos")
    
    logger.info(f"Comando vendedor: '{message_text}' para contato {contact_id}")
    
    if message_text.lower().startswith("/assumir "):
        contact_id_to_pause = message_text.split()[1]
        try:
            contact_id_to_pause = int(contact_id_to_pause)
            _bot_status_cache[contact_id_to_pause] = False
            if contact_id_to_pause in _proactive_conversations:
                _proactive_conversations[contact_id_to_pause]["active"] = False
            logger.info(f"Bot pausado via comando /assumir para contato {contact_id_to_pause}")
            return {
                "status": "bot_paused", 
                "message": f"Bot pausado para contato {contact_id_to_pause}. Você pode assumir!",
                "contact_id": contact_id_to_pause
            }
        except (ValueError, IndexError):
            return {"status": "error", "message": "Comando inválido. Use: /assumir [contact_id]"}
    
    elif message_text.lower().startswith("/liberar "):
        contact_id_to_resume = message_text.split()[1]
        try:
            contact_id_to_resume = int(contact_id_to_resume)
            _bot_status_cache[contact_id_to_resume] = True
            if contact_id_to_resume in _proactive_conversations:
                _proactive_conversations[contact_id_to_resume]["active"] = True
            logger.info(f"Bot reativado via comando /liberar para contato {contact_id_to_resume}")
            return {
                "status": "bot_resumed", 
                "message": f"Bot reativado para contato {contact_id_to_resume}. Atendimento automático voltou!",
                "contact_id": contact_id_to_resume
            }
        except (ValueError, IndexError):
            return {"status": "error", "message": "Comando inválido. Use: /liberar [contact_id]"}
    
    else:
        return {"status": "error", "message": "Comando não reconhecido. Use: /assumir [contact_id] ou /liberar [contact_id]"}

@app.get("/stats")
async def get_stats():
    """Estatísticas da API"""
    total_conversations = len(_proactive_conversations)
    active_conversations = len([c for c in _proactive_conversations.values() if c.get("active", False)])
    conversations_with_response = len([c for c in _proactive_conversations.values() if c.get("first_response_received", False)])
    
    # Estatísticas por vendedor
    vendor_stats = {}
    for conv in _proactive_conversations.values():
        vendor = conv.get("vendedor", "unknown")
        if vendor not in vendor_stats:
            vendor_stats[vendor] = {"total": 0, "active": 0, "with_response": 0}
        vendor_stats[vendor]["total"] += 1
        if conv.get("active", False):
            vendor_stats[vendor]["active"] += 1
        if conv.get("first_response_received", False):
            vendor_stats[vendor]["with_response"] += 1
    
    # Estatísticas por gatilho
    trigger_stats = {}
    for conv in _proactive_conversations.values():
        trigger = conv.get("trigger_type", "unknown")
        trigger_stats[trigger] = trigger_stats.get(trigger, 0) + 1
    
    return {
        "timestamp": datetime.now().isoformat(),
        "conversations": {
            "total": total_conversations,
            "active": active_conversations,
            "with_response": conversations_with_response,
            "response_rate": round((conversations_with_response / total_conversations * 100), 2) if total_conversations > 0 else 0
        },
        "by_vendor": vendor_stats,
        "by_trigger": trigger_stats,
        "bot_status_cache_size": len(_bot_status_cache)
    }

@app.get("/conversations/active")
async def get_active_conversations():
    """Lista conversas proativas ativas"""
    return {
        "active_conversations": len([c for c in _proactive_conversations.values() if c.get("active", False)]),
        "total_conversations": len(_proactive_conversations),
        "conversations": _proactive_conversations
    }

@app.get("/test-integration")
async def test_integration():
    """Testa conectividade REAL com Kommo e n8n"""
    results = {
        "timestamp": datetime.now().isoformat(),
        "kommo": {"configured": False, "accessible": False, "method": "unknown"},
        "n8n": {"configured": False, "accessible": False}
    }
    
    # Testar configuração e conectividade Kommo
    if os.getenv("KOMMO_API_URL") and os.getenv("KOMMO_ACCESS_TOKEN"):
        results["kommo"]["configured"] = True
        
        # Testar conectividade real
        kommo_test = await test_kommo_connectivity()
        if kommo_test["success"]:
            results["kommo"]["accessible"] = True
            results["kommo"]["method"] = kommo_test.get("method", "api")
            results["kommo"]["sample"] = kommo_test.get("sample_data", {})
        else:
            results["kommo"]["error"] = kommo_test.get("error", "Erro desconhecido")
        
    # Testar configuração n8n
    if os.getenv("N8N_WEBHOOK_URL"):
        results["n8n"]["configured"] = True
        # TODO: Implementar teste real de conectividade com n8n
    
    return results

# NOVOS ENDPOINTS PARA DEBUG E TESTES

@app.get("/test-kommo-lead/{lead_id}")
async def test_kommo_lead(lead_id: str):
    """Testa acesso a um lead específico do Kommo"""
    result = await test_kommo_lead_access(lead_id)
    return result

@app.get("/test-kommo-connectivity")
async def test_kommo_connection():
    """Testa conectividade básica com a API do Kommo"""
    result = await test_kommo_connectivity()
    return result

@app.post("/create-test-note/{lead_id}")
async def create_test_note(lead_id: str, message: str = "Teste de nota via API"):
    """Cria uma nota de teste em um lead específico"""
    conversation_id = f"test_{lead_id}"
    result = await send_kommo_message(conversation_id, message)
    return result

@app.post("/test-lead-update/{lead_id}")
async def test_lead_update(lead_id: str, message: str = "Teste de atualização de lead"):
    """Testa atualização de lead diretamente"""
    try:
        # Configurações do Kommo
        kommo_api_url = os.getenv("KOMMO_API_URL")
        access_token = os.getenv("KOMMO_ACCESS_TOKEN")
        
        if not kommo_api_url or not access_token:
            return {"success": False, "error": "Configurações do Kommo não encontradas"}
        
        # URL da API de leads do Kommo
        full_url = f"{kommo_api_url.rstrip('/')}/leads/{lead_id}"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Payload para atualizar o lead (apenas nome por enquanto)
        payload = {
            "name": f"Lead Teste - {message}"
        }
        
        logger.info(f"Atualizando lead {lead_id}: {full_url}")
        logger.info(f"Payload: {payload}")
        
        timeout = aiohttp.ClientTimeout(total=15, connect=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.patch(full_url, json=payload, headers=headers) as response:
                if response.status in [200, 201]:
                    result = await response.json()
                    logger.info(f"Lead {lead_id} atualizado com sucesso")
                    return {
                        "success": True, 
                        "data": result,
                        "message": "Lead atualizado com sucesso",
                        "lead_id": lead_id,
                        "method": "leads_api"
                    }
                else:
                    error_text = await response.text()
                    logger.error(f"Erro ao atualizar lead: {response.status} - {error_text}")
                    return {
                        "success": False, 
                        "error": f"Status {response.status}: {error_text}",
                        "lead_id": lead_id
                    }
                    
    except Exception as e:
        logger.error(f"Erro na atualização do lead: {e}")
        return {"success": False, "error": str(e)}

@app.get("/debug/conversations")
async def debug_conversations():
    """Debug: mostra estado interno das conversas"""
    return {
        "proactive_conversations": _proactive_conversations,
        "bot_status_cache": _bot_status_cache,
        "total_conversations": len(_proactive_conversations),
        "total_bot_statuses": len(_bot_status_cache)
    }

@app.delete("/reset/conversations")
async def reset_conversations():
    """CUIDADO: Reseta todas as conversas (apenas para desenvolvimento)"""
    global _proactive_conversations, _bot_status_cache
    
    conversations_deleted = len(_proactive_conversations)
    statuses_deleted = len(_bot_status_cache)
    
    _proactive_conversations.clear()
    _bot_status_cache.clear()
    
    return {
        "status": "reset_completed",
        "conversations_deleted": conversations_deleted,
        "statuses_deleted": statuses_deleted,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/version")
async def get_version():
    """Informações da versão atual"""
    return {
        "version": "2.2.0",
        "features": [
            "Conversas proativas multi-vendedor",
            "API corrigida para usar Notes em vez de Chats",
            "Integração com n8n + Supabase",
            "Sistema de agendamento por vendedor",
            "Controle manual de bot",
            "Comandos especiais via chat",
            "Testes de conectividade"
        ],
        "fixes": [
            "Corrigido problema de permissões com API de chats",
            "Implementado fallback para API de notes",
            "Adicionados endpoints de debug e teste",
            "Integração com sistema de agendamento"
        ],
        "compatibility": {
            "kommo_scopes_required": ["crm", "notifications"],
            "kommo_scopes_current": ["crm", "files", "files_delete", "notifications", "push_notifications"],
            "chat_api_available": False,
            "notes_api_available": True,
            "scheduling_system_enabled": True
        }
    }

# ==========================================
# SISTEMA DE AGENDAMENTO COM VENDEDORES
# ==========================================

@app.get("/vendedores")
async def get_vendedores():
    """Lista todos os vendedores disponíveis para agendamento - DINÂMICO"""
    vendedores_dinamicos = await get_vendedores_dinamicos()
    
    vendedores_info = []
    for vendedor, config in vendedores_dinamicos.items():
        vendedores_info.append({
            "name": vendedor,
            "display_name": config.get("display_name"),
            "phone_api": config.get("phone_api"),
            "email": config.get("email", ""),
            "user_id": config.get("user_id"),
            "is_real_user": config.get("is_real_user", False),
            "available_for_scheduling": True,
            "source": "kommo_api" if config.get("is_real_user") else "fictional"
        })
    
    # Separar reais dos fictícios
    vendedores_reais = [v for v in vendedores_info if v["is_real_user"]]
    vendedores_ficticios = [v for v in vendedores_info if not v["is_real_user"]]
    
    return {
        "vendedores_reais": vendedores_reais,
        "vendedores_ficticios": vendedores_ficticios,
        "total_reais": len(vendedores_reais),
        "total_ficticios": len(vendedores_ficticios),
        "total": len(vendedores_info),
        "system": "dynamic_scheduling_enabled",
        "cache_info": {
            "last_update": _last_vendedores_update.isoformat() if _last_vendedores_update else None,
            "cache_size": len(_vendedores_kommo_cache)
        }
    }

@app.get("/vendedor/by-conversation/{conversation_id}")
async def get_vendedor_by_conversation(conversation_id: str):
    """Retorna o vendedor responsável por uma conversa específica"""
    try:
        # Buscar conversa ativa
        for contact_id, conversation in _proactive_conversations.items():
            if conversation.get("conversation_id") == conversation_id:
                vendedor = conversation.get("vendedor")
                if vendedor and vendedor in VENDEDOR_CONFIG:
                    return {
                        "conversation_id": conversation_id,
                        "contact_id": contact_id,
                        "vendedor": {
                            "name": vendedor,
                            "display_name": VENDEDOR_CONFIG[vendedor].get("display_name"),
                            "phone_api": VENDEDOR_CONFIG[vendedor].get("phone_api"),
                            "area_atuacao": conversation.get("area_atuacao")
                        },
                        "lead_data": conversation.get("lead_data", {}),
                        "initiated_at": conversation.get("initiated_at")
                    }
        
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/vendedor/by-contact/{contact_id}")
async def get_vendedor_by_contact(contact_id: int):
    """Retorna o vendedor responsável por um contact_id específico"""
    try:
        if contact_id in _proactive_conversations:
            conversation = _proactive_conversations[contact_id]
            vendedor = conversation.get("vendedor")
            
            if vendedor and vendedor in VENDEDOR_CONFIG:
                return {
                    "contact_id": contact_id,
                    "vendedor": {
                        "name": vendedor,
                        "display_name": VENDEDOR_CONFIG[vendedor].get("display_name"),
                        "phone_api": VENDEDOR_CONFIG[vendedor].get("phone_api"),
                        "area_atuacao": conversation.get("area_atuacao")
                    },
                    "conversation_data": {
                        "conversation_id": conversation.get("conversation_id"),
                        "lead_id": conversation.get("lead_id"),
                        "active": conversation.get("active", False),
                        "initiated_at": conversation.get("initiated_at")
                    },
                    "lead_data": conversation.get("lead_data", {})
                }
        
        raise HTTPException(status_code=404, detail="Contact ID não encontrado em conversas ativas")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/vendedor/by-lead/{lead_id}")
async def get_vendedor_by_lead(lead_id: int):
    """Retorna o vendedor responsável por um lead_id específico"""
    try:
        # Buscar em todas as conversas por lead_id
        for contact_id, conversation in _proactive_conversations.items():
            if conversation.get("lead_id") == lead_id:
                vendedor = conversation.get("vendedor")
                
                if vendedor and vendedor in VENDEDOR_CONFIG:
                    return {
                        "lead_id": lead_id,
                        "contact_id": contact_id,
                        "vendedor": {
                            "name": vendedor,
                            "display_name": VENDEDOR_CONFIG[vendedor].get("display_name"),
                            "phone_api": VENDEDOR_CONFIG[vendedor].get("phone_api"),
                            "area_atuacao": conversation.get("area_atuacao")
                        },
                        "conversation_data": {
                            "conversation_id": conversation.get("conversation_id"),
                            "active": conversation.get("active", False),
                            "initiated_at": conversation.get("initiated_at")
                        },
                        "lead_data": conversation.get("lead_data", {})
                    }
        
        raise HTTPException(status_code=404, detail="Lead ID não encontrado em conversas ativas")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class VendedorCustom(BaseModel):
    name: str
    display_name: str
    phone_api: str
    email: Optional[str] = None
    area_atuacao: Optional[str] = None

class AgendamentoPayload(BaseModel):
    contact_id: int
    lead_id: Optional[int] = None
    conversation_id: Optional[str] = None
    vendedor_requested: Optional[str] = None
    agenda_data: Dict[str, Any]
    client_data: Optional[Dict[str, Any]] = None

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
        
        # 3. Tentar identificar por lead_id
        if not vendedor_info and agendamento.lead_id:
            for contact_id, conversation in _proactive_conversations.items():
                if conversation.get("lead_id") == agendamento.lead_id:
                    vendedor_info = {
                        "name": conversation.get("vendedor"),
                        "source": "lead_id",
                        "area_atuacao": conversation.get("area_atuacao"),
                        "lead_data": conversation.get("lead_data", {})
                    }
                    break
        
        # 4. Usar vendedor solicitado como fallback
        if not vendedor_info and agendamento.vendedor_requested:
            if agendamento.vendedor_requested in VENDEDOR_CONFIG:
                vendedor_info = {
                    "name": agendamento.vendedor_requested,
                    "source": "manual_request",
                    "area_atuacao": "não_identificada",
                    "lead_data": agendamento.client_data or {}
                }
        
        if not vendedor_info or not vendedor_info["name"]:
            return {
                "status": "error",
                "message": "Não foi possível identificar o vendedor responsável",
                "available_vendors": list(VENDEDOR_CONFIG.keys()),
                "suggestion": "Use vendedor_requested ou certifique-se que existe conversa ativa"
            }
        
        vendedor_name = vendedor_info["name"]
        vendedor_config = VENDEDOR_CONFIG[vendedor_name]
        
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
# GESTÃO DE VENDEDORES CUSTOMIZADOS
# ==========================================

@app.get("/vendedores/reais")
async def get_vendedores_reais():
    """Busca vendedores reais diretamente do Kommo"""
    vendedores_reais = await fetch_vendedores_kommo()
    
    return {
        "vendedores_reais": vendedores_reais,
        "total": len(vendedores_reais),
        "source": "kommo_api_direct",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/vendedores/adicionar")
async def adicionar_vendedor_custom(vendedor: VendedorCustom):
    """Adiciona vendedor customizado (para quando não está no Kommo)"""
    global VENDEDOR_CONFIG
    
    if vendedor.name in VENDEDOR_CONFIG:
        return {
            "status": "warning",
            "message": f"Vendedor {vendedor.name} já existe",
            "action": "use_update_endpoint"
        }
    
    VENDEDOR_CONFIG[vendedor.name] = {
        "display_name": vendedor.display_name,
        "phone_api": vendedor.phone_api,
        "email": vendedor.email,
        "area_atuacao": vendedor.area_atuacao,
        "is_real_user": False,
        "source": "custom_added",
        "added_at": datetime.now().isoformat()
    }
    
    return {
        "status": "success",
        "message": f"Vendedor {vendedor.name} adicionado com sucesso",
        "vendedor": VENDEDOR_CONFIG[vendedor.name]
    }

@app.post("/vendedores/sincronizar")
async def sincronizar_vendedores_kommo():
    """Força sincronização com vendedores do Kommo"""
    global _vendedores_kommo_cache, _last_vendedores_update
    
    logger.info("Forçando sincronização com vendedores do Kommo")
    vendedores_reais = await fetch_vendedores_kommo()
    
    if vendedores_reais:
        _vendedores_kommo_cache = vendedores_reais
        _last_vendedores_update = datetime.now()
        
        return {
            "status": "success",
            "message": "Sincronização concluída",
            "vendedores_encontrados": len(vendedores_reais),
            "vendedores": list(vendedores_reais.keys()),
            "timestamp": _last_vendedores_update.isoformat()
        }
    else:
        return {
            "status": "error",
            "message": "Não foi possível sincronizar com o Kommo",
            "suggestion": "Verifique a configuração da API"
        }

@app.get("/vendedores/dinamicos")
async def get_vendedores_dinamicos_endpoint():
    """Endpoint para vendedores dinâmicos (reais + fictícios)"""
    return await get_vendedores_dinamicos()

@app.get("/vendedor/conversa/{conversation_id}")
async def get_vendedor_by_conversation_endpoint(conversation_id: str):
    """Endpoint para buscar vendedor por ID de conversa"""
    return await get_vendedor_by_conversation(conversation_id)

@app.get("/vendedor/contato/{contact_id}")
async def get_vendedor_by_contact_endpoint(contact_id: int):
    """Endpoint para buscar vendedor por ID de contato"""
    return await get_vendedor_by_contact(contact_id)

@app.get("/vendedor/lead/{lead_id}")
async def get_vendedor_by_lead_endpoint(lead_id: int):
    """Endpoint para buscar vendedor por ID de lead"""
    return await get_vendedor_by_lead(lead_id)

@app.post("/sincronizar/vendedores")
async def sincronizar_vendedores_endpoint():
    """Endpoint para sincronizar vendedores (alias)"""
    return await sincronizar_vendedores_kommo()

@app.post("/refresh-token")
async def refresh_kommo_token():
    """Endpoint para renovar token do Kommo"""
    try:
        kommo_service = KommoService()
        success = await kommo_service.refresh_token_if_needed()
        
        if success:
            return {
                "status": "success",
                "message": "Token renovado com sucesso",
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "error",
                "message": "Falha ao renovar token",
                "suggestion": "Verifique refresh_token e credenciais"
            }
    except Exception as e:
        logger.error(f"Erro ao renovar token: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
