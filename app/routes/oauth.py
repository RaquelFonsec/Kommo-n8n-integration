from fastapi import APIRouter, HTTPException
from app.services.kommo_service import KommoService
from app.utils.logger import setup_logger
from app.models.kommo_models import (
    OAuthTokenRequest, 
    RefreshTokenRequest, 
    OAuthTokenResponse, 
    OAuthStatusResponse
)
from datetime import datetime

router = APIRouter()
logger = setup_logger(__name__)

@router.get("/callback")
async def oauth_callback(code: str = None, state: str = None):
    """Callback do OAuth2 do Kommo"""
    if not code:
        raise HTTPException(status_code=400, detail="Código de autorização não fornecido")
    
    try:
        kommo = KommoService()
        logger.info(f"OAuth callback recebido - code: {code[:20]}...")
        
        # Troca código por token
        tokens = await kommo.exchange_code_for_token(code)
        
        if not tokens:
            raise HTTPException(status_code=400, detail="Falha ao trocar código por token")
        
        # Salva tokens no .env
        saved = await kommo.save_tokens_to_env(tokens)
        
        return {
            "status": "success", 
            "message": "Tokens OAuth obtidos e salvos com sucesso",
            "access_token": tokens.get("access_token")[:20] + "..." if tokens.get("access_token") else None,
            "expires_at": tokens.get("expires_at"),
            "saved_to_env": saved
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no OAuth callback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status", response_model=OAuthStatusResponse)
async def oauth_status():
    """Verifica status da autenticação OAuth"""
    kommo = KommoService()
    
    token_expired = None
    if kommo.token_expires_at:
        token_expired = kommo.is_token_expired()
    
    return OAuthStatusResponse(
        oauth_configured=bool(kommo.access_token),
        client_id=kommo.client_id[:8] + "..." if kommo.client_id else None,
        account_id=kommo.account_id,
        api_url=kommo.api_url,
        token_expires_at=kommo.token_expires_at,
        token_expired=token_expired
    )

@router.post("/refresh", response_model=OAuthTokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """Renova o access token usando refresh token"""
    try:
        kommo = KommoService()
        
        # Usa refresh token do request ou do serviço
        refresh_token = request.refresh_token or kommo.refresh_token
        if not refresh_token:
            raise HTTPException(status_code=400, detail="Refresh token não fornecido")
        
        logger.info("Renovando token via endpoint...")
        
        # Renova o token
        tokens = await kommo.refresh_access_token(refresh_token)
        
        if not tokens:
            raise HTTPException(status_code=400, detail="Falha ao renovar token")
        
        # Salva tokens no .env
        saved = await kommo.save_tokens_to_env(tokens)
        
        return OAuthTokenResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens.get("refresh_token", refresh_token),
            token_type="Bearer",
            expires_in=tokens.get("expires_in", 86400)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao renovar token: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/exchange")
async def exchange_code(request: OAuthTokenRequest):
    """Troca código de autorização por tokens (alternativo ao callback)"""
    try:
        kommo = KommoService()
        
        logger.info("Trocando código por token via endpoint...")
        
        # Troca código por token
        tokens = await kommo.exchange_code_for_token(request.code)
        
        if not tokens:
            raise HTTPException(status_code=400, detail="Falha ao trocar código por token")
        
        # Salva tokens no .env
        saved = await kommo.save_tokens_to_env(tokens)
        
        return {
            "status": "success",
            "message": "Tokens obtidos com sucesso",
            "tokens": OAuthTokenResponse(
                access_token=tokens["access_token"],
                refresh_token=tokens["refresh_token"],
                token_type="Bearer",
                expires_in=tokens.get("expires_in", 86400)
            ),
            "saved_to_env": saved
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao trocar código por token: {e}")
        raise HTTPException(status_code=500, detail=str(e))
