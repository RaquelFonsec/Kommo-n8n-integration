import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv
import logging
from datetime import datetime
from typing import Dict, Any

# Importar serviços
from app.services.webhook_processor import WebhookProcessor
from app.services.kommo_service import KommoService
from app.services.n8n_service import N8nService

# Importar routers
from app.routes import oauth

load_dotenv()

# Setup básico de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Kommo-n8n Integration", 
    version="1.0.0",
    description="Integração entre Kommo CRM e n8n para agente inteligente"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(oauth.router, prefix="/oauth", tags=["oauth"])

@app.get("/")
async def root():
    return {
        "message": "Kommo-n8n Integration Active",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/webhooks/kommo")
async def receive_kommo_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """Recebe webhooks do Kommo"""
    try:
        webhook_data = await request.json()
        logger.info(f"📥 Webhook recebido do Kommo: {webhook_data}")
        
        # Processar webhook em background
        processor = WebhookProcessor()
        background_tasks.add_task(
            processor.process_webhook, 
            webhook_data
        )
        
        return {
            "status": "received", 
            "message": "Webhook recebido e sendo processado",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao processar webhook: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/send-response")
async def receive_n8n_response(request: Request):
    """Recebe resposta do n8n e envia para Kommo"""
    try:
        response_data = await request.json()
        logger.info(f"🤖 Resposta recebida do n8n: {response_data}")
        
        conversation_id = response_data.get("conversation_id")
        response_text = response_data.get("response")
        should_send = response_data.get("should_send", True)
        
        if should_send and conversation_id and response_text:
            kommo = KommoService()
            result = await kommo.send_message(conversation_id, response_text)
            
            if "error" not in result:
                logger.info(f"✅ Resposta enviada com sucesso para: {conversation_id}")
                return {
                    "status": "sent",
                    "conversation_id": conversation_id,
                    "message": "Resposta enviada para Kommo"
                }
            else:
                logger.error(f"❌ Erro ao enviar resposta: {result['error']}")
                return {"status": "error", "message": result['error']}
        else:
            logger.info("⏭️ Resposta não enviada (should_send=False ou dados incompletos)")
            return {"status": "skipped", "message": "Resposta não enviada"}
            
    except Exception as e:
        logger.error(f"❌ Erro ao processar resposta do n8n: {e}")
        return {"status": "error", "message": str(e)}

# Endpoints para controle manual do bot
@app.post("/bot/pause/{contact_id}")
async def pause_bot(contact_id: int):
    """Pausa o bot para um contato específico"""
    try:
        kommo = KommoService()
        success = await kommo.pause_bot(contact_id)
        
        if success:
            logger.info(f"⏸️ Bot pausado manualmente para contato {contact_id}")
            return {
                "status": "success",
                "message": f"Bot pausado para contato {contact_id}",
                "contact_id": contact_id
            }
        else:
            logger.error(f"❌ Erro ao pausar bot para contato {contact_id}")
            raise HTTPException(status_code=500, detail="Erro ao pausar bot")
            
    except Exception as e:
        logger.error(f"❌ Erro ao pausar bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/bot/resume/{contact_id}")
async def resume_bot(contact_id: int):
    """Reativa o bot para um contato específico"""
    try:
        kommo = KommoService()
        success = await kommo.resume_bot(contact_id)
        
        if success:
            logger.info(f"▶️ Bot reativado manualmente para contato {contact_id}")
            return {
                "status": "success",
                "message": f"Bot reativado para contato {contact_id}",
                "contact_id": contact_id
            }
        else:
            logger.error(f"❌ Erro ao reativar bot para contato {contact_id}")
            raise HTTPException(status_code=500, detail="Erro ao reativar bot")
            
    except Exception as e:
        logger.error(f"❌ Erro ao reativar bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/bot/status/{contact_id}")
async def get_bot_status(contact_id: int):
    """Retorna status do bot para um contato"""
    try:
        kommo = KommoService()
        status = await kommo.get_bot_status(contact_id)
        
        if "error" not in status:
            logger.info(f"📊 Status consultado para contato {contact_id}")
            return status
        else:
            logger.error(f"❌ Erro ao obter status para contato {contact_id}")
            raise HTTPException(status_code=500, detail="Erro ao obter status")
            
    except Exception as e:
        logger.error(f"❌ Erro ao obter status do bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/bot/command")
async def execute_bot_command(request: Request):
    """Executa comando do bot via API"""
    try:
        data = await request.json()
        contact_id = data.get("contact_id")
        command = data.get("command", "").lower()
        
        if not contact_id:
            raise HTTPException(status_code=400, detail="contact_id é obrigatório")
        
        kommo = KommoService()
        
        if command == "pause":
            success = await kommo.pause_bot(contact_id)
            message = "Bot pausado" if success else "Erro ao pausar bot"
        elif command == "resume":
            success = await kommo.resume_bot(contact_id)
            message = "Bot reativado" if success else "Erro ao reativar bot"
        elif command == "status":
            status = await kommo.get_bot_status(contact_id)
            return status
        else:
            raise HTTPException(status_code=400, detail="Comando inválido. Use: pause, resume, status")
        
        return {
            "status": "success" if success else "error",
            "message": message,
            "contact_id": contact_id,
            "command": command
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao executar comando: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/test")
async def test():
    return {
        "message": "API funcionando!", 
        "kommo_configured": bool(os.getenv("KOMMO_ACCESS_TOKEN")),
        "kommo_account_id": os.getenv("KOMMO_ACCOUNT_ID"),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/config")
async def show_config():
    return {
        "kommo_client_id": os.getenv("KOMMO_CLIENT_ID")[:8] + "..." if os.getenv("KOMMO_CLIENT_ID") else None,
        "kommo_base_url": os.getenv("KOMMO_BASE_URL"),
        "kommo_account_id": os.getenv("KOMMO_ACCOUNT_ID"),
        "n8n_webhook_url": os.getenv("N8N_WEBHOOK_URL"),
        "n8n_api_key_configured": bool(os.getenv("N8N_API_KEY")),
        "environment": os.getenv("ENVIRONMENT", "development")
    }

@app.get("/test/n8n")
async def test_n8n_connectivity():
    """Testa conectividade com o n8n"""
    try:
        n8n = N8nService()
        result = await n8n.test_connectivity()
        
        logger.info(f"🔍 Teste de conectividade n8n: {result}")
        return {
            "test_type": "n8n_connectivity",
            "timestamp": datetime.now().isoformat(),
            **result
        }
        
    except Exception as e:
        logger.error(f"❌ Erro no teste de conectividade n8n: {e}")
        return {
            "test_type": "n8n_connectivity",
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/test/kommo")
async def test_kommo_connectivity():
    """Testa conectividade com o Kommo"""
    try:
        kommo = KommoService()
        
        # Testar busca de um contato de exemplo
        test_contact_id = 999
        contact = await kommo.get_contact(test_contact_id)
        
        if contact:
            status = "success"
            message = "Kommo API acessível"
        else:
            status = "warning"
            message = "Kommo API acessível mas contato de teste não encontrado (normal)"
        
        logger.info(f"🔍 Teste de conectividade Kommo: {status}")
        return {
            "test_type": "kommo_connectivity",
            "status": status,
            "message": message,
            "test_contact_id": test_contact_id,
            "contact_found": bool(contact),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Erro no teste de conectividade Kommo: {e}")
        return {
            "test_type": "kommo_connectivity",
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    debug = os.getenv("DEBUG", "true").lower() == "true"
    
    print(f"🚀 Iniciando Kommo-n8n Integration na porta {port}")
    print(f"📖 Documentação: http://localhost:{port}/docs")
    print(f"🔗 Webhook Kommo: http://localhost:{port}/webhooks/kommo")
    print(f"🔗 Resposta n8n: http://localhost:{port}/send-response")
    print(f"🤖 Controle Bot: http://localhost:{port}/bot/status/[contact_id]")
    print(f"🔐 OAuth Status: http://localhost:{port}/oauth/status")
    print(f"🧪 Teste n8n: http://localhost:{port}/test/n8n")
    print(f"🧪 Teste Kommo: http://localhost:{port}/test/kommo")
    
    uvicorn.run(
        "app.main:app", 
        host=host, 
        port=port, 
        reload=debug,
        log_level="info"
    )
