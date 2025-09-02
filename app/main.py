import os
import logging
import aiohttp
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

# Configurar logging
logger = logging.getLogger(__name__)

# Inicializar FastAPI
app = FastAPI(
    title="Kommo-n8n Integration API",
    description="""
    ## 🔄 API de Integração Kommo + n8n
    
    ### 🌐 URLs de Produção:
    - **Base URL:** `https://dashboard.previdas.com.br/api/kommo-n8n`
    - **Webhook Kommo:** `https://dashboard.previdas.com.br/api/kommo-n8n/webhooks/kommo`
    - **Resposta n8n:** `https://dashboard.previdas.com.br/api/kommo-n8n/send-response`
    
    ### 📋 Funcionalidades:
    - Recebe webhooks do Kommo CRM
    - Processa mensagens e envia para n8n
    - Recebe respostas da IA e envia para WhatsApp
    - Controle manual do bot (pausar/reativar)
    
    ### 🔧 Configurações Externas:
    - **Kommo:** Configure webhook para "Lead adicionado"
    - **n8n:** Configure saída para endpoint de resposta
    """,
    version="1.0.0",
    contact={
        "name": "Previdas",
        "url": "https://dashboard.previdas.com.br"
    }
)

# Importar e incluir routers
from app.routes import webhooks, oauth

app.include_router(webhooks.router, prefix="/webhooks")
app.include_router(oauth.router, prefix="/oauth")

# Modelo para resposta do n8n
class N8nResponse(BaseModel):
    conversation_id: str
    response_text: str
    should_send: bool = True
    should_handoff: bool = False
    metadata: Optional[Dict[str, Any]] = None

# Serviço para enviar mensagem via Kommo
async def send_kommo_message(conversation_id: str, message: str) -> Dict[str, Any]:
    """Envia mensagem via API do Kommo"""
    try:
        # Verificar se as variáveis de ambiente existem
        kommo_api_url = os.getenv("KOMMO_API_URL")
        access_token = os.getenv("KOMMO_ACCESS_TOKEN")
        
        if not kommo_api_url or not access_token:
            logger.error(" Variáveis de ambiente KOMMO_API_URL ou KOMMO_ACCESS_TOKEN não configuradas")
            return {"success": False, "error": "Configuração de API do Kommo não encontrada"}
        
        # Construir URL completa
        full_url = f"{kommo_api_url.rstrip('/')}/chats/messages"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "conversation_id": conversation_id,
            "message": {
                "text": message
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(full_url, json=payload, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f" Mensagem enviada para conversa {conversation_id}")
                    return {"success": True, "data": result}
                else:
                    error_text = await response.text()
                    logger.error(f" Erro ao enviar mensagem: {response.status} - {error_text}")
                    return {"success": False, "error": f"Status {response.status}: {error_text}"}
                    
    except aiohttp.ClientError as e:
        logger.error(f" Erro de conexão ao enviar mensagem: {e}")
        return {"success": False, "error": f"Erro de conexão: {str(e)}"}
    except Exception as e:
        logger.error(f" Exceção ao enviar mensagem: {e}")
        return {"success": False, "error": str(e)}

# Endpoint para receber resposta do n8n
@app.post("/send-response", 
    summary="Recebe resposta do n8n",
    description="""
    ### 📥 Endpoint para Resposta do n8n
    
    **URL de Produção:** `https://dashboard.previdas.com.br/api/kommo-n8n/send-response`
    
    Recebe a resposta processada pela IA do n8n e envia para o WhatsApp via Kommo.
    
    **Configuração no n8n:**
    - URL: `https://dashboard.previdas.com.br/api/kommo-n8n/send-response`
    - Método: POST
    - Content-Type: application/json
    """,
    tags=["n8n", "whatsapp"]
)
async def receive_n8n_response(n8n_response: N8nResponse):
    """Recebe resposta processada do n8n e envia via Kommo"""
    try:
        logger.info(f" Resposta do n8n recebida: {n8n_response.conversation_id}")
        
        # Verificar se deve enviar mensagem
        if not n8n_response.should_send:
            logger.info("⏸ Mensagem não deve ser enviada (should_send=False)")
            return {
                "status": "skipped", 
                "message": "Mensagem não enviada conforme instrução do n8n",
                "conversation_id": n8n_response.conversation_id
            }
        
        # Validar se há texto para enviar
        if not n8n_response.response_text or not n8n_response.response_text.strip():
            logger.warning(f" Texto da resposta está vazio para conversa {n8n_response.conversation_id}")
            return {
                "status": "error",
                "message": "Texto da resposta está vazio",
                "conversation_id": n8n_response.conversation_id
            }
        
        # Enviar mensagem via Kommo
        result = await send_kommo_message(
            conversation_id=n8n_response.conversation_id,
            message=n8n_response.response_text
        )
        
        if result["success"]:
            # Log adicional se deve fazer handoff
            if n8n_response.should_handoff:
                logger.info(f"🔄 Handoff recomendado para conversa {n8n_response.conversation_id}")
                # Aqui  pode implementar lógica de handoff (tags, notificações, etc.)
            
            return {
                "status": "sent",
                "message": "Resposta enviada com sucesso via Kommo",
                "conversation_id": n8n_response.conversation_id,
                "handoff_required": n8n_response.should_handoff,
                "metadata": n8n_response.metadata
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao enviar via Kommo: {result['error']}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro no endpoint /send-response: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Modelo para teste de envio
class TestMessage(BaseModel):
    conversation_id: str
    message: str

# Endpoint para testar envio manual
@app.post("/test-send")
async def test_send_message(test_data: TestMessage):
    """Endpoint para testar envio de mensagem manual"""
    try:
        if not test_data.message.strip():
            raise HTTPException(status_code=400, detail="Mensagem não pode estar vazia")
            
        result = await send_kommo_message(test_data.conversation_id, test_data.message)
        
        if result["success"]:
            return {
                "status": "success",
                "message": "Mensagem de teste enviada com sucesso",
                "test_result": result
            }
        else:
            raise HTTPException(status_code=500, detail=f"Erro no teste: {result['error']}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro no endpoint /test-send: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint de health check
@app.get("/health")
async def health_check():
    """Endpoint para verificar se a API está funcionando"""
    return {
        "status": "healthy",
        "message": "API está funcionando",
        "kommo_configured": bool(os.getenv("KOMMO_API_URL") and os.getenv("KOMMO_ACCESS_TOKEN"))
    }