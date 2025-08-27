from fastapi import APIRouter, HTTPException
from app.services.kommo_service import KommoService
from app.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)

@router.get("/callback")
async def oauth_callback(code: str = None, state: str = None):
    """Callback do OAuth2 do Kommo"""
    if not code:
        raise HTTPException(status_code=400, detail="Código de autorização não fornecido")
    
    try:
        # Aqui você implementaria a troca do código por token
        # Por agora, vamos apenas logar que recebeu o callback
        logger.info(f"OAuth callback recebido - code: {code[:20]}...")
        
        return {
            "status": "success", 
            "message": "Callback OAuth recebido com sucesso",
            "note": "Token já configurado via .env"
        }
        
    except Exception as e:
        logger.error(f"Erro no OAuth callback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def oauth_status():
    """Verifica status da autenticação OAuth"""
    kommo = KommoService()
    
    return {
        "oauth_configured": bool(kommo.access_token),
        "client_id": kommo.client_id[:8] + "..." if kommo.client_id else None,
        "account_id": kommo.account_id,
        "api_url": kommo.api_url
    }
