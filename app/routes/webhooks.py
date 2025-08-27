from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
from app.services.webhook_processor import WebhookProcessor
from app.utils.logger import setup_logger
from typing import Dict, Any

router = APIRouter()
logger = setup_logger(__name__)

@router.post("/kommo")
async def receive_kommo_webhook(
    webhook_data: Dict[Any, Any],
    background_tasks: BackgroundTasks
):
    """Recebe webhooks do Kommo e processa mensagens"""
    try:
        logger.info(f"Webhook recebido do Kommo: {webhook_data}")
        
        processor = WebhookProcessor()
        background_tasks.add_task(
            processor.process_webhook, 
            webhook_data
        )
        
        return {
            "status": "received", 
            "message": "Webhook recebido e sendo processado",
            "timestamp": webhook_data.get("timestamp")
        }
        
    except Exception as e:
        logger.error(f"Erro ao processar webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/test")
async def test_webhook():
    """Endpoint para testar se os webhooks estão funcionando"""
    return {
        "status": "ok",
        "message": "Webhook endpoint está funcionando",
        "webhook_url": "/webhooks/kommo"
    }
