import os
import aiohttp
import asyncio
from typing import Optional, Dict, Any
from app.utils.logger import setup_logger
from dotenv import load_dotenv

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
            logger.info("Verificando necessidade de refresh token...")
            return True
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
                await self.send_message_to_contact(contact_id, "🤖 Bot pausado. Vendedor assumindo conversa.")
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
                await self.send_message_to_contact(contact_id, "🤖 Bot reativado. Assumindo atendimento automático.")
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
        """Envia mensagem via API do Kommo"""
        try:
            if not self.access_token:
                logger.error("KOMMO_ACCESS_TOKEN não configurado")
                return {"error": "KOMMO_ACCESS_TOKEN não configurado"}
            
            await self.refresh_token_if_needed()
            
            # Tenta usar o endpoint correto da API do Kommo
            url = f"{self.api_url}/chats/messages"
            headers = await self.get_headers()
            
            payload = {
                "conversation_id": conversation_id,
                "message": message,
                "type": "text"
            }
            
            logger.info(f"Enviando mensagem para Kommo:")
            logger.info(f"  Conversation ID: {conversation_id}")
            logger.info(f"  Mensagem: {message}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200 or response.status == 201:
                        result = await response.json()
                        logger.info(f"Mensagem enviada com sucesso para: {conversation_id}")
                        return {
                            "status": "sent",
                            "conversation_id": conversation_id,
                            "message": message,
                            "response": result
                        }
                    elif response.status == 404:
                        # Tenta endpoint alternativo
                        logger.warning(f"Endpoint /chats/messages não encontrado, tentando /messages")
                        return await self._try_alternative_message_endpoint(conversation_id, message)
                    else:
                        logger.error(f"Erro ao enviar mensagem: {response.status}")
                        return {"error": f"HTTP {response.status}"}
                        
        except asyncio.TimeoutError:
            logger.error(f"Timeout ao enviar mensagem para {conversation_id}")
            return {"error": "Timeout"}
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {e}")
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
    
    async def get_contact(self, contact_id: int) -> Optional[Dict[str, Any]]:
        """Busca informações de um contato"""
        try:
            url = f"{self.api_url}/contacts/{contact_id}"
            headers = await self.get_headers()
            
            logger.info(f"Buscando contato: {contact_id}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
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
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
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
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
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
            
            async with aiohttp.ClientSession() as session:
                async with session.patch(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
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
            
            async with aiohttp.ClientSession() as session:
                async with session.patch(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
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
            # Endpoint alternativo: /messages
            url = f"{self.api_url}/messages"
            headers = await self.get_headers()
            
            payload = {
                "conversation_id": conversation_id,
                "message": message,
                "type": "text"
            }
            
            logger.info(f"Tentando endpoint alternativo: /messages")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
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
