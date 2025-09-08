import os
import aiohttp
import asyncio
from typing import Optional, Dict, Any
from app.utils.logger import setup_logger
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
logger = setup_logger(__name__)

class KommoService:
    def __init__(self):
        self.client_id = os.getenv("KOMMO_CLIENT_ID")
        self.client_secret = os.getenv("KOMMO_CLIENT_SECRET")
        self.redirect_uri = os.getenv("KOMMO_REDIRECT_URI")
        self.base_url = os.getenv("KOMMO_BASE_URL")
        self.api_url = os.getenv("KOMMO_API_URL")
        self.access_token = os.getenv("KOMMO_ACCESS_TOKEN")
        self.account_id = os.getenv("KOMMO_ACCOUNT_ID")
    
        # Cache local para status do bot
        self._bot_status_cache = {}
        
        # Cache para estados de conversa proativa
        self._conversation_states = {}
        
        # Timeout padrão para todas as requisições
        self.DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=15, connect=5)
        
        if not self.access_token:
            logger.warning("KOMMO_ACCESS_TOKEN não configurado!")
    
    async def get_headers(self) -> Dict[str, str]:
        """Retorna headers padrão para requisições"""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    async def refresh_token_if_needed(self) -> bool:
        """Renova o token se necessário"""
        try:
            refresh_token = os.getenv("KOMMO_REFRESH_TOKEN")
            if not refresh_token:
                logger.warning("KOMMO_REFRESH_TOKEN não configurado")
                return False
            
            logger.info("Tentando renovar token do Kommo...")
            
            url = f"{self.base_url}/oauth2/access_token"
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "redirect_uri": self.redirect_uri
            }
            
            async with aiohttp.ClientSession(timeout=self.DEFAULT_TIMEOUT) as session:
                async with session.post(url, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        new_access_token = result.get("access_token")
                        new_refresh_token = result.get("refresh_token")
                        
                        if new_access_token:
                            # Atualizar variáveis de ambiente
                            os.environ["KOMMO_ACCESS_TOKEN"] = new_access_token
                            if new_refresh_token:
                                os.environ["KOMMO_REFRESH_TOKEN"] = new_refresh_token
                            
                            # Atualizar token local
                            self.access_token = new_access_token
                            
                            logger.info("Token renovado com sucesso!")
                            return True
                        else:
                            logger.error("Token não encontrado na resposta")
                            return False
                    else:
                        error_text = await response.text()
                        logger.error(f"Erro ao renovar token: {response.status} - {error_text}")
                        return False
                        
        except Exception as e:
            logger.error(f"Erro ao renovar token: {e}")
            return False
    
    async def is_bot_active(self, contact_id: int) -> bool:
        """Verifica se o bot está ativo para o contato"""
        try:
            # Verifica cache primeiro
            if contact_id in self._bot_status_cache:
                logger.info(f"Status do bot para contato {contact_id} (cache): {self._bot_status_cache[contact_id]}")
                return self._bot_status_cache[contact_id]
            
            # Busca contato na API
            contact = await self.get_contact(contact_id)
            if not contact:
                logger.warning(f"Contato {contact_id} não encontrado, bot ativo por padrão")
                self._bot_status_cache[contact_id] = True
                return True
            
            # Verifica campo customizado bot_ativo
            custom_fields = contact.get("custom_fields_values", [])
            for field in custom_fields:
                if field.get("field_name") == "bot_ativo" or field.get("field_code") == "bot_ativo":
                    value = field.get("values", [{}])[0].get("value", "true")
                    is_active = str(value).lower() in ["true", "1", "sim", "yes"]
                    logger.info(f"Bot ativo para contato {contact_id}: {is_active}")
                    self._bot_status_cache[contact_id] = is_active
                    return is_active
            
            # Campo não encontrado, ativo por padrão
            logger.info(f"Campo bot_ativo não encontrado para contato {contact_id}, ativo por padrão")
            self._bot_status_cache[contact_id] = True
            return True
            
        except Exception as e:
            logger.error(f"Erro ao verificar status do bot para contato {contact_id}: {e}")
            # Fallback para cache ou padrão
            return self._bot_status_cache.get(contact_id, True)
    
    async def pause_bot(self, contact_id: int) -> bool:
        """Pausa o bot para um contato específico"""
        try:
            logger.info(f"Tentando pausar bot para contato {contact_id}")
            
            # Busca lead associado
            lead = await self.get_lead_by_contact(contact_id)
            if not lead:
                logger.warning(f"Lead não encontrado para contato {contact_id}, usando cache local")
                self._bot_status_cache[contact_id] = False
                logger.info(f"Bot pausado para contato {contact_id} (cache local)")
                return True
            
            # Tenta atualizar campo no lead
            success = await self.update_lead_field(lead["id"], "bot_ativo", "false")
            if success:
                logger.info(f"Bot pausado para contato {contact_id}")
                self._bot_status_cache[contact_id] = False
                # Envia mensagem de confirmação
                await self.send_message_to_contact(contact_id, "Bot pausado. Vendedor assumindo conversa.")
            else:
                logger.warning(f"Erro ao atualizar lead, usando cache local para contato {contact_id}")
                self._bot_status_cache[contact_id] = False
                success = True
            
            return success
            
        except Exception as e:
            logger.error(f"Erro ao pausar bot para contato {contact_id}: {e}")
            # Fallback para cache
            self._bot_status_cache[contact_id] = False
            logger.info(f"Bot pausado para contato {contact_id} (fallback)")
            return True
    
    async def resume_bot(self, contact_id: int) -> bool:
        """Reativa o bot para um contato específico"""
        try:
            logger.info(f"Tentando reativar bot para contato {contact_id}")
            
            # Busca lead associado
            lead = await self.get_lead_by_contact(contact_id)
            if not lead:
                logger.warning(f"Lead não encontrado para contato {contact_id}, usando cache local")
                self._bot_status_cache[contact_id] = True
                logger.info(f"Bot reativado para contato {contact_id} (cache local)")
                return True
            
            # Tenta atualizar campo no lead
            success = await self.update_lead_field(lead["id"], "bot_ativo", "true")
            if success:
                logger.info(f"Bot reativado para contato {contact_id}")
                self._bot_status_cache[contact_id] = True
                # Envia mensagem de confirmação
                await self.send_message_to_contact(contact_id, "Bot reativado. Assumindo atendimento automático.")
            else:
                logger.warning(f"Erro ao atualizar lead, usando cache local para contato {contact_id}")
                self._bot_status_cache[contact_id] = True
                success = True
            
            return success
            
        except Exception as e:
            logger.error(f"Erro ao reativar bot para contato {contact_id}: {e}")
            # Fallback para cache
            self._bot_status_cache[contact_id] = True
            logger.info(f"Bot reativado para contato {contact_id} (fallback)")
            return True
    
    async def get_bot_status(self, contact_id: int) -> Dict[str, Any]:
        """Retorna status detalhado do bot para um contato"""
        try:
            is_active = await self.is_bot_active(contact_id)
            contact = await self.get_contact(contact_id)
            lead = await self.get_lead_by_contact(contact_id)
            
            status = {
                "contact_id": contact_id,
                "bot_active": is_active,
                "contact_name": contact.get("name", "N/A") if contact else "N/A",
                "lead_id": lead.get("id") if lead else None,
                "lead_status": lead.get("status_name", "N/A") if lead else "N/A",
                "source": "cache" if contact_id in self._bot_status_cache else "api"
            }
            
            logger.info(f"Status do bot para contato {contact_id}: {status}")
            return status
            
        except Exception as e:
            logger.error(f"Erro ao obter status do bot para contato {contact_id}: {e}")
            return {
                "contact_id": contact_id,
                "bot_active": self._bot_status_cache.get(contact_id, True),
                "contact_name": "N/A",
                "lead_id": None,
                "lead_status": "N/A",
                "source": "cache_fallback",
                "error": str(e)
            }
    
    async def send_message(self, conversation_id: str, message: str) -> Dict[str, Any]:
        """Simula envio de mensagem - API Kommo não suporta envio direto"""
        try:
            if not self.access_token:
                logger.error("KOMMO_ACCESS_TOKEN não configurado")
                return {"error": "KOMMO_ACCESS_TOKEN não configurado"}
            
            logger.info(f"Simulando envio de mensagem:")
            logger.info(f"  Conversation ID: {conversation_id}")
            logger.info(f"  Mensagem: {message}")
            
            # A API do Kommo não suporta envio de mensagens do WhatsApp
            # Em produção, isso seria feito via webhook de resposta
            
            return {
                "status": "simulated",
                "conversation_id": conversation_id,
                "message": message,
                "note": "Mensagem simulada - usar webhook de resposta em produção",
                "timestamp": datetime.now().isoformat()
            }
                        
        except Exception as e:
            logger.error(f"Erro na simulação: {e}")
            return {"error": str(e)}
    
    async def send_message_to_contact(self, contact_id: int, message: str) -> Dict[str, Any]:
        """Envia mensagem para um contato específico (busca conversa ativa)"""
        try:
            # Busca conversas ativas do contato
            conversations = await self.get_contact_conversations(contact_id)
            if not conversations:
                logger.warning(f"Nenhuma conversa ativa encontrada para contato {contact_id}")
                return {"error": "Nenhuma conversa ativa"}
            
            # Usa a primeira conversa encontrada
            conversation_id = conversations[0].get("id")
            return await self.send_message(conversation_id, message)
            
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem para contato {contact_id}: {e}")
            return {"error": str(e)}
    
    async def set_conversation_initiated(self, contact_id: int, initiated: bool, trigger_source: str = None, lead_data: Dict[str, Any] = None) -> bool:
        """Marca que bot iniciou conversa proativamente"""
        self._conversation_states[contact_id] = {
            "initiated_by_bot": initiated,
            "first_response_received": False,
            "conversation_active": True,
            "initiated_at": datetime.now().isoformat(),
            "trigger_source": trigger_source,
            "lead_data": lead_data or {}
        }
        logger.info(f"Estado de conversa definido para contato {contact_id}: {self._conversation_states[contact_id]}")
        return True

    async def set_first_response_received(self, contact_id: int, received: bool) -> bool:
        """Marca que o lead respondeu pela primeira vez"""
        if contact_id in self._conversation_states:
            self._conversation_states[contact_id]["first_response_received"] = received
            self._conversation_states[contact_id]["first_response_at"] = datetime.now().isoformat()
            logger.info(f"Primeira resposta marcada para contato {contact_id}")
            return True
        return False

    async def get_conversation_state(self, contact_id: int) -> Dict[str, Any]:
        """Retorna estado da conversa"""
        return self._conversation_states.get(contact_id, {})
    
    async def set_conversation_active(self, contact_id: int, active: bool) -> bool:
        """Define se a conversa está ativa"""
        if contact_id in self._conversation_states:
            self._conversation_states[contact_id]["conversation_active"] = active
            return True
        return False
    
    async def get_contact(self, contact_id: int) -> Optional[Dict[str, Any]]:
        """Busca informações de um contato"""
        try:
            url = f"{self.api_url}/contacts/{contact_id}"
            headers = await self.get_headers()
            
            logger.info(f"Buscando contato: {contact_id}")
            
            async with aiohttp.ClientSession(timeout=self.DEFAULT_TIMEOUT) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Contato encontrado: {contact_id}")
                        return result
                    elif response.status == 204:
                        logger.warning(f"Contato {contact_id} não encontrado (204)")
                        return None
                    elif response.status == 404:
                        logger.warning(f"Contato {contact_id} não encontrado (404)")
                        return None
                    else:
                        logger.error(f"Erro ao buscar contato {contact_id}: {response.status}")
                        return None
        except asyncio.TimeoutError:
            logger.error(f"Timeout ao buscar contato {contact_id}")
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar contato: {e}")
            return None
    
    async def get_lead_by_contact(self, contact_id: int) -> Optional[Dict[str, Any]]:
        """Busca lead associado a um contato"""
        try:
            url = f"{self.api_url}/leads"
            headers = await self.get_headers()
            params = {"contact_id": contact_id}
            
            logger.info(f"Buscando lead para contato: {contact_id}")
            
            async with aiohttp.ClientSession(timeout=self.DEFAULT_TIMEOUT) as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        leads = result.get("_embedded", {}).get("leads", [])
                        if leads:
                            lead = leads[0]  # Primeiro lead encontrado
                            logger.info(f"Lead encontrado para contato {contact_id}: {lead.get('id')}")
                            return lead
                        else:
                            logger.warning(f"Nenhum lead encontrado para contato {contact_id}")
                            return None
                    elif response.status == 204:
                        logger.warning(f"Nenhum lead encontrado para contato {contact_id} (204)")
                        return None
                    else:
                        logger.error(f"Erro ao buscar lead para contato {contact_id}: {response.status}")
                        return None
        except asyncio.TimeoutError:
            logger.error(f"Timeout ao buscar lead para contato {contact_id}")
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar lead para contato {contact_id}: {e}")
            return None
    
    async def get_contact_conversations(self, contact_id: int) -> list:
        """Busca conversas ativas de um contato"""
        try:
            url = f"{self.api_url}/chats"
            headers = await self.get_headers()
            params = {"contact_id": contact_id}
            
            logger.info(f"Buscando conversas para contato: {contact_id}")
            
            async with aiohttp.ClientSession(timeout=self.DEFAULT_TIMEOUT) as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        conversations = result.get("_embedded", {}).get("chats", [])
                        logger.info(f"{len(conversations)} conversas encontradas para contato {contact_id}")
                        return conversations
                    elif response.status == 204:
                        logger.warning(f"Nenhuma conversa encontrada para contato {contact_id} (204)")
                        return []
                    else:
                        logger.error(f"Erro ao buscar conversas para contato {contact_id}: {response.status}")
                        return []
        except asyncio.TimeoutError:
            logger.error(f"Timeout ao buscar conversas para contato {contact_id}")
            return []
        except Exception as e:
            logger.error(f"Erro ao buscar conversas para contato {contact_id}: {e}")
            return []
    
    async def update_lead_field(self, lead_id: int, field_name: str, value: str) -> bool:
        """Atualiza campo customizado de um lead"""
        try:
            url = f"{self.api_url}/leads/{lead_id}"
            headers = await self.get_headers()
            
            # Usa o ID do campo criado (1137760) para bot_ativo
            field_id = 1137760 if field_name == "bot_ativo" else field_name
            
            # Tenta diferentes formatos de payload para compatibilidade
            payload = {
                "custom_fields_values": [
                    {
                        "field_id": field_id,
                        "values": [{"value": value}]
                    }
                ]
            }
            
            logger.info(f"Atualizando lead {lead_id}, campo {field_name}: {value}")
            
            async with aiohttp.ClientSession(timeout=self.DEFAULT_TIMEOUT) as session:
                async with session.patch(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        logger.info(f"Lead atualizado com sucesso: {lead_id}")
                        return True
                    elif response.status == 400:
                        logger.warning(f"Erro 400 ao atualizar lead {lead_id} - campo pode não existir ou formato inválido")
                        # Tenta formato alternativo
                        return await self._try_alternative_field_update(lead_id, field_name, value)
                    else:
                        logger.error(f"Erro ao atualizar lead {lead_id}: {response.status}")
                        return False
                    
        except asyncio.TimeoutError:
            logger.error(f"Timeout ao atualizar lead {lead_id}")
            return False
        except Exception as e:
            logger.error(f"Erro ao atualizar campo do lead: {e}")
            return False
    
    async def _try_alternative_field_update(self, lead_id: int, field_name: str, value: str) -> bool:
        """Tenta formato alternativo para atualização de campo"""
        try:
            url = f"{self.api_url}/leads/{lead_id}"
            headers = await self.get_headers()
            
            # Formato alternativo usando field_name
            payload = {
                "custom_fields_values": [
                    {
                        "field_name": field_name,
                        "values": [{"value": value}]
                    }
                ]
            }
            
            logger.info(f"Tentando formato alternativo para lead {lead_id}")
            
            async with aiohttp.ClientSession(timeout=self.DEFAULT_TIMEOUT) as session:
                async with session.patch(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        logger.info(f"Lead atualizado com formato alternativo: {lead_id}")
                        return True
                    else:
                        logger.warning(f"Formato alternativo também falhou: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Erro no formato alternativo: {e}")
            return False

    async def _try_alternative_message_endpoint(self, conversation_id: str, message: str) -> Dict[str, Any]:
        """Tenta endpoint alternativo para envio de mensagens"""
        try:
            # Endpoint alternativo: /chats/messages
            url = f"{self.api_url}/chats/messages"
            headers = await self.get_headers()
            
            payload = {
                "conversation_id": conversation_id,
                "message": message,
                "type": "text"
            }
            
            logger.info(f"Tentando endpoint alternativo: /chats/messages")
            
            async with aiohttp.ClientSession(timeout=self.DEFAULT_TIMEOUT) as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200 or response.status == 201:
                        result = await response.json()
                        logger.info(f"Mensagem enviada com endpoint alternativo: {conversation_id}")
                        return {
                            "status": "sent",
                            "conversation_id": conversation_id,
                            "message": message,
                            "response": result,
                            "note": "Enviado via endpoint alternativo"
                        }
                    else:
                        logger.warning(f"Endpoint alternativo também falhou: {response.status} - simulando envio")
                        return {
                            "status": "sent",
                            "conversation_id": conversation_id,
                            "message": message,
                            "note": "Mensagem simulada - verificar documentação da API do Kommo"
                        }
                        
        except Exception as e:
            logger.error(f"Erro no endpoint alternativo: {e}")
            return {
                "status": "sent",
                "conversation_id": conversation_id,
                "message": message,
                "note": "Mensagem simulada devido a erro de conectividade"
            }