from fastapi import APIRouter
from datetime import datetime
import os

router = APIRouter()

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development")
    }

@router.get("/status")
async def status():
    """Status detalhado da aplicação"""
    return {
        "application": "kommo-n8n-integration",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "config": {
            "kommo_configured": bool(os.getenv("KOMMO_ACCESS_TOKEN")),
            "n8n_configured": bool(os.getenv("N8N_WEBHOOK_URL")),
            "environment": os.getenv("ENVIRONMENT", "development")
        }
    }
