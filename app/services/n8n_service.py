import os
import aiohttp
import asyncio
from typing import Dict, Any
from app.models.kommo_models import N8nPayload
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class N8nService:
    def __init__(self):
        self.webhook_url = os.getenv("N8N_WEBHOOK_URL")
        self.api_key = os.getenv("N8N_API_KEY")
        
        if not self.webhook_url:
            logger.warning("⚠️ N8N_WEBHOOK_URL não configurada!")
    
    async def send_to_n8n(self, payload: N8nPayload) -> Dict[str, Any]:
        """Envia payload para o webhook do n8n"""
        try:
            if not self.webhook_url:
                logger.error("❌ N8N_WEBHOOK_URL não configurada")
                return {"error": "N8N_WEBHOOK_URL não configurada"}
            
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            payload_dict = payload.dict()
            logger.info(f"📤 Enviando para n8n:")
            logger.info(f"   🔗 URL: {self.webhook_url}")
            logger.info(f"   📦 Payload: {payload_dict}")
            
            # Configurar timeout para evitar travamentos
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    self.webhook_url, 
                    json=payload_dict, 
                    headers=headers
                ) as response:
                    logger.info(f"📡 Status da resposta: {response.status}")
                    
                    if response.status == 200:
                        try:
                            result = await response.json()
                            logger.info(f"✅ Payload enviado para n8n com sucesso: {payload.conversation_id}")
                            logger.info(f"📨 Resposta do n8n: {result}")
                            return result
                        except Exception as json_error:
                            logger.warning(f"⚠️ Erro ao parsear JSON da resposta: {json_error}")
                            text_response = await response.text()
                            logger.info(f"📄 Resposta em texto: {text_response}")
                            return {"status": "success", "response_text": text_response}
                    elif response.status == 404:
                        logger.error(f"❌ n8n não encontrado (404) - verificar URL: {self.webhook_url}")
                        return {"error": "n8n não encontrado - verificar URL"}
                    elif response.status == 401:
                        logger.error(f"❌ Erro de autenticação (401) - verificar API key")
                        return {"error": "Erro de autenticação - verificar API key"}
                    elif response.status == 500:
                        logger.error(f"❌ Erro interno do n8n (500)")
                        return {"error": "Erro interno do n8n"}
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Erro ao enviar para n8n: {response.status} - {error_text}")
                        return {"error": f"Status {response.status}: {error_text}"}
                        
        except asyncio.TimeoutError:
            logger.error(f"⏰ Timeout ao conectar com n8n: {self.webhook_url}")
            return {"error": "Timeout ao conectar com n8n"}
        except aiohttp.ClientConnectorError as e:
            logger.error(f"🔌 Erro de conectividade com n8n: {e}")
            return {"error": f"Erro de conectividade: {str(e)}"}
        except aiohttp.ClientError as e:
            logger.error(f"🌐 Erro de cliente HTTP com n8n: {e}")
            return {"error": f"Erro HTTP: {str(e)}"}
        except Exception as e:
            logger.error(f"❌ Erro inesperado ao enviar para n8n: {e}")
            return {"error": str(e)}
    
    async def test_connectivity(self) -> Dict[str, Any]:
        """Testa conectividade com o n8n"""
        try:
            if not self.webhook_url:
                return {"status": "error", "message": "N8N_WEBHOOK_URL não configurada"}
            
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            # Teste simples de conectividade
            timeout = aiohttp.ClientTimeout(total=10, connect=5)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(self.webhook_url, headers=headers) as response:
                    if response.status in [200, 404, 405]:  # 404/405 são normais para webhooks
                        return {
                            "status": "success", 
                            "message": "n8n acessível",
                            "response_status": response.status
                        }
                    else:
                        return {
                            "status": "warning",
                            "message": f"n8n respondeu com status {response.status}",
                            "response_status": response.status
                        }
                        
        except asyncio.TimeoutError:
            return {"status": "error", "message": "Timeout ao conectar com n8n"}
        except aiohttp.ClientConnectorError as e:
            return {"status": "error", "message": f"Erro de conectividade: {str(e)}"}
        except Exception as e:
            return {"status": "error", "message": f"Erro inesperado: {str(e)}"}
