from typing import Dict, Any
from app.services.kommo_service import KommoService
from app.services.n8n_service import N8nService
from app.models.kommo_models import N8nPayload, KommoWebhook
from app.utils.logger import setup_logger
from datetime import datetime

logger = setup_logger(__name__)

class WebhookProcessor:
    def __init__(self):
        self.kommo = KommoService()
        self.n8n = N8nService()
    
    async def process_webhook(self, webhook_data: Dict[str, Any]):
        """Processa webhook recebido do Kommo"""
        try:
            logger.info(" Iniciando processamento de webhook")
            logger.info(f" Dados recebidos: {webhook_data}")
            
            # Verificar se é uma mensagem de chat
            if "chats" in webhook_data and "message" in webhook_data["chats"]:
                await self._process_chat_message(webhook_data)
            elif "message" in webhook_data:
                await self._process_direct_message(webhook_data)
            else:
                logger.info("ℹ Webhook recebido mas não é uma mensagem de chat")
            
        except Exception as e:
            logger.error(f"❌ Erro no processamento de webhook: {e}")
    
    async def _process_chat_message(self, webhook_data: Dict[str, Any]):
        """Processa mensagem de chat"""
        try:
            chat_data = webhook_data["chats"]
            message_data = chat_data["message"]
            
            
            conversation_id = (
                chat_data.get("conversation_id") or 
                message_data.get("conversation_id") or 
                str(message_data.get("id", ""))
            )
            
            # Buscar contact_id em múltiplos locais - 
            contact_id = (
                message_data.get("contact_id") or 
                message_data.get("author", {}).get("contact_id") or 
                message_data.get("author", {}).get("id", 0)
            )
            
            message_text = message_data.get("text", "")
            author_type = message_data.get("author", {}).get("type", "")
            
            # Log melhorado para debug
            logger.info(f" Processando mensagem de chat:")
            logger.info(f"     Conversation ID: '{conversation_id}'")
            logger.info(f"     Contact ID: {contact_id}")
            logger.info(f"     Mensagem: '{message_text}'")
            logger.info(f"     Autor: {author_type}")
            logger.info(f"     Dados brutos - chat: {chat_data}")
            logger.info(f"     Dados brutos - message: {message_data}")
            
            # Verificar se a mensagem é do cliente (não do agente/sistema)
            if author_type == "contact":
                logger.info(" Mensagem é do contato - processando...")
                
                # Verificar se é um comando especial
                if await self._is_special_command(message_text):
                    await self._process_special_command(message_text, contact_id)
                    return
                
                # Verificar se o bot está ativo para este contato
                if not await self.kommo.is_bot_active(contact_id):
                    logger.info(f" Bot pausado para contato {contact_id} - ignorando mensagem")
                    return
                
                # Buscar informações adicionais do contato
                contact_info = await self.kommo.get_contact(contact_id) if contact_id > 0 else None
                lead_info = await self.kommo.get_lead_by_contact(contact_id) if contact_id > 0 else None
                
                # Criar payload para n8n - MELHORADO
                n8n_payload = N8nPayload(
                    conversation_id=str(conversation_id),
                    contact_id=contact_id,
                    message_text=message_text,
                    timestamp=datetime.now().isoformat(),
                    chat_type="whatsapp",
                    lead_id=lead_info.get("id") if lead_info else None,
                    contact_name=contact_info.get("name") if contact_info else None
                )
                
                logger.info(f" Enviando payload para n8n: {n8n_payload.dict()}")
                
                # Enviar para n8n
                result = await self.n8n.send_to_n8n(n8n_payload)
                
                if "error" not in result:
                    logger.info(f" Mensagem processada e enviada para n8n: {conversation_id}")
                    logger.info(f" Resposta do n8n: {result}")
                else:
                    logger.error(f" Erro ao enviar para n8n: {result['error']}")
            else:
                logger.info(f" Mensagem ignorada (autor: {author_type} - não é contato)")
                
        except Exception as e:
            logger.error(f" Erro ao processar mensagem de chat: {e}")
            import traceback
            logger.error(f" Traceback: {traceback.format_exc()}")
    
    async def _is_special_command(self, message_text: str) -> bool:
        """Verifica se a mensagem é um comando especial"""
        commands = ["#pausar", "#voltar", "#status", "#help"]
        return any(command in message_text.lower() for command in commands)
    
    async def _process_special_command(self, message_text: str, contact_id: int):
        """Processa comandos especiais dos vendedores"""
        try:
            command = message_text.lower().strip()
            logger.info(f"🔧 Processando comando especial: {command}")
            
            if "#pausar" in command:
                success = await self.kommo.pause_bot(contact_id)
                if success:
                    logger.info(f" Bot pausado com sucesso para contato {contact_id}")
                else:
                    logger.error(f"Erro ao pausar bot para contato {contact_id}")
                    
            elif "#voltar" in command:
                success = await self.kommo.resume_bot(contact_id)
                if success:
                    logger.info(f" Bot reativado com sucesso para contato {contact_id}")
                else:
                    logger.error(f"Erro ao reativar bot para contato {contact_id}")
                    
            elif "#status" in command:
                status = await self.kommo.get_bot_status(contact_id)
                logger.info(f" Status do bot: {status}")
                
                # Enviar status como mensagem
                status_message = f"""
 **Status do Bot**
Contato: {status.get('contact_name', 'N/A')}
 Bot Ativo: {' Sim' if status.get('bot_active') else '❌ Não'}
 Lead ID: {status.get('lead_id', 'N/A')}
 Status Lead: {status.get('lead_status', 'N/A')}
                """.strip()
                
                await self.kommo.send_message_to_contact(contact_id, status_message)
                
            elif "#help" in command:
                help_message = """
 **Comandos Disponíveis**

#pausar - Pausa o bot para este contato
#voltar - Reativa o bot para este contato  
#status - Mostra status atual do bot
#help - Mostra esta ajuda

 O bot só responde quando está ativo.
                """.strip()
                
                await self.kommo.send_message_to_contact(contact_id, help_message)
                
        except Exception as e:
            logger.error(f"❌ Erro ao processar comando especial: {e}")
    
    async def _process_direct_message(self, webhook_data: Dict[str, Any]):
        """Processa mensagem direta"""
        try:
            message_data = webhook_data["message"]
            
            logger.info(" Mensagem direta recebida (implementar se necessário)")
            logger.info(f" Dados da mensagem: {message_data}")
            
        except Exception as e:
            logger.error(f" Erro ao processar mensagem direta: {e}")