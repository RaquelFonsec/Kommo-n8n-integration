from typing import Dict, Any
from app.services.kommo_service import KommoService
from app.services.n8n_service import N8nService
from app.models.kommo_models import N8nPayload, KommoWebhook, ConversationState
from app.utils.logger import setup_logger
from datetime import datetime

logger = setup_logger(__name__)

class WebhookProcessor:
    def __init__(self):
        self.kommo = KommoService()
        self.n8n = N8nService()
        
        # Mapeamento vendedor -> configurações WhatsApp
        self.vendedor_config = {
            "Asaf": {
                "phone_api": "asaf_whatsapp",
                "display_name": "Asaf - Previdas"
            },
            "João": {
                "phone_api": "joao_whatsapp", 
                "display_name": "João - Previdas"
            },
            "Maria": {
                "phone_api": "maria_whatsapp",
                "display_name": "Maria - Previdas"
            }
        }
    
    async def process_webhook(self, webhook_data: Dict[str, Any]):
        """Processa webhook recebido do Kommo"""
        try:
            logger.info("Iniciando processamento de webhook")
            logger.info(f"Dados recebidos: {webhook_data}")
            
            # Verificar se é uma mensagem de chat
            if "chats" in webhook_data and "message" in webhook_data["chats"]:
                await self._process_chat_message(webhook_data)
            elif "message" in webhook_data:
                await self._process_direct_message(webhook_data)
            else:
                logger.info("Webhook recebido mas não é uma mensagem de chat")
            
        except Exception as e:
            logger.error(f"Erro no processamento de webhook: {e}")
    
    async def _process_chat_message(self, webhook_data: Dict[str, Any]):
        """Processa mensagem de chat"""
        try:
            chat_data = webhook_data["chats"]
            message_data = chat_data["message"]
            
            # Extrair informações da mensagem
            conversation_id = (
                chat_data.get("conversation_id") or 
                message_data.get("conversation_id") or 
                str(message_data.get("id", ""))
            )
            
            # Buscar contact_id em múltiplos locais
            contact_id = (
                message_data.get("contact_id") or 
                message_data.get("author", {}).get("contact_id") or 
                message_data.get("author", {}).get("id", 0)
            )
            
            message_text = message_data.get("text", "")
            author_type = message_data.get("author", {}).get("type", "")
            
            # Extrair informações do vendedor responsável
            responsible_user = self._extract_responsible_user(webhook_data)
            
            # Log melhorado para debug
            logger.info(f"Processando mensagem de chat:")
            logger.info(f"    Conversation ID: '{conversation_id}'")
            logger.info(f"    Contact ID: {contact_id}")
            logger.info(f"    Mensagem: '{message_text}'")
            logger.info(f"    Autor: {author_type}")
            logger.info(f"    Vendedor responsável: {responsible_user}")
            logger.info(f"    Dados brutos - chat: {chat_data}")
            logger.info(f"    Dados brutos - message: {message_data}")
            
            # Verificar se a mensagem é do cliente (não do agente/sistema)
            if author_type == "contact":
                logger.info("Mensagem é do contato - processando...")
                
                # Verificar se é primeira resposta a mensagem proativa
                conversation_state = await self.kommo.get_conversation_state(contact_id)
                
                if conversation_state and conversation_state.get("initiated_by_bot") and not conversation_state.get("first_response_received"):
                    # Marcar que lead respondeu à abordagem proativa
                    await self.kommo.set_first_response_received(contact_id, True)
                    logger.info(f"Lead {contact_id} respondeu à abordagem proativa!")
                    logger.info(f"Trigger original: {conversation_state.get('trigger_source', 'N/A')}")
                    logger.info(f"Vendedor: {conversation_state.get('responsible_user', 'N/A')}")
                
                # Verificar se é um comando especial
                if await self._is_special_command(message_text):
                    await self._process_special_command(message_text, contact_id, responsible_user)
                    return
                
                # Verificar se o bot está ativo para este contato
                if not await self.kommo.is_bot_active(contact_id):
                    logger.info(f"Bot pausado para contato {contact_id} - ignorando mensagem")
                    return
                
                # Buscar informações adicionais do contato
                contact_info = await self.kommo.get_contact(contact_id) if contact_id > 0 else None
                lead_info = await self.kommo.get_lead_by_contact(contact_id) if contact_id > 0 else None
                
                # Verificar área de atuação se disponível
                area_atuacao = self._extract_area_atuacao(lead_info)
                if not self._should_activate_bot(area_atuacao):
                    logger.info(f"Área de atuação '{area_atuacao}' não elegível para bot - ignorando mensagem")
                    return
                
                # Extrair telefone do contato/lead
                phone_number = None
                if lead_info and lead_info.get("id"):
                    phone_number = await self.kommo.extract_phone_from_lead(lead_info.get("id"))
                elif contact_info:
                    # Tentar extrair telefone do contato diretamente
                    custom_fields = contact_info.get("custom_fields_values", [])
                    for field in custom_fields:
                        field_name = field.get("field_name", "").lower()
                        if field_name in ["whatsapp", "telefone", "celular", "phone"]:
                            values = field.get("values", [])
                            if values:
                                phone_number = values[0].get("value")
                                break
                
                # Criar payload para n8n com informações de contexto proativo e vendedor
                n8n_payload = N8nPayload(
                    conversation_id=str(conversation_id),
                    contact_id=contact_id,
                    message_text=message_text,
                    timestamp=datetime.now().isoformat(),
                    chat_type="whatsapp",
                    lead_id=lead_info.get("id") if lead_info else None,
                    contact_name=contact_info.get("name") if contact_info else None,
                    phone_number=phone_number
                )
                
                # Adicionar contexto de conversa proativa e vendedor ao payload
                n8n_payload_dict = n8n_payload.dict()
                
                # Contexto proativo
                if conversation_state:
                    n8n_payload_dict["proactive_context"] = {
                        "initiated_by_bot": conversation_state.get("initiated_by_bot", False),
                        "trigger_source": conversation_state.get("trigger_source"),
                        "first_response": conversation_state.get("first_response_received", False),
                        "initiated_at": conversation_state.get("initiated_at"),
                        "responsible_user": conversation_state.get("responsible_user")
                    }
                    logger.info(f"Contexto proativo adicionado: {n8n_payload_dict['proactive_context']}")
                
                # Contexto do vendedor
                if responsible_user:
                    vendor_config = self.vendedor_config.get(responsible_user, {})
                    n8n_payload_dict["vendor_context"] = {
                        "responsible_user": responsible_user,
                        "phone_api": vendor_config.get("phone_api"),
                        "display_name": vendor_config.get("display_name"),
                        "area_atuacao": area_atuacao
                    }
                    logger.info(f"Contexto vendedor adicionado: {n8n_payload_dict['vendor_context']}")
                
                logger.info(f"Enviando payload para n8n: {n8n_payload_dict}")
                
                # Enviar para n8n
                result = await self.n8n.send_to_n8n_with_dict(n8n_payload_dict)
                
                if "error" not in result:
                    logger.info(f"Mensagem processada e enviada para n8n: {conversation_id}")
                    logger.info(f"Resposta do n8n: {result}")
                else:
                    logger.error(f"Erro ao enviar para n8n: {result['error']}")
            else:
                logger.info(f"Mensagem ignorada (autor: {author_type} - não é contato)")
                
        except Exception as e:
            logger.error(f"Erro ao processar mensagem de chat: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    def _extract_responsible_user(self, webhook_data: Dict[str, Any]) -> str:
        """Extrai informações do vendedor responsável do webhook"""
        # Tentar diferentes locais onde o vendedor pode estar
        lead_data = webhook_data.get("leads", {})
        if lead_data:
            responsible_user = lead_data.get("responsible_user_name")
            if responsible_user:
                return responsible_user
        
        # Tentar em chat data
        chat_data = webhook_data.get("chats", {})
        if chat_data:
            responsible_user = chat_data.get("responsible_user_name")
            if responsible_user:
                return responsible_user
        
        # Tentar em message data
        message_data = webhook_data.get("chats", {}).get("message", {})
        responsible_user = message_data.get("responsible_user_name")
        if responsible_user:
            return responsible_user
        
        return "default"
    
    def _extract_area_atuacao(self, lead_info: Dict[str, Any]) -> str:
        """Extrai área de atuação do lead"""
        if not lead_info:
            return "unknown"
        
        # Buscar em campos customizados
        custom_fields = lead_info.get("custom_fields_values", [])
        for field in custom_fields:
            if field.get("field_name") == "area_atuacao" or field.get("field_code") == "area_atuacao":
                value = field.get("values", [{}])[0].get("value", "")
                return str(value).lower()
        
        return "unknown"
    
    def _should_activate_bot(self, area_atuacao: str) -> bool:
        """Verifica se deve ativar bot baseado na área de atuação"""
        areas_elegive = ["previdenciario", "tributario", "outros", "previdenciário", "tributário"]
        return area_atuacao.lower() in areas_elegive
    
    async def _is_special_command(self, message_text: str) -> bool:
        """Verifica se a mensagem é um comando especial"""
        commands = ["#pausar", "#voltar", "#status", "#help"]
        return any(command in message_text.lower() for command in commands)
    
    async def _process_special_command(self, message_text: str, contact_id: int, responsible_user: str = None):
        """Processa comandos especiais dos vendedores"""
        try:
            command = message_text.lower().strip()
            logger.info(f"Processando comando especial: {command}")
            
            if "#pausar" in command:
                success = await self.kommo.pause_bot(contact_id)
                if success:
                    logger.info(f"Bot pausado com sucesso para contato {contact_id}")
                else:
                    logger.error(f"Erro ao pausar bot para contato {contact_id}")
                    
            elif "#voltar" in command:
                success = await self.kommo.resume_bot(contact_id)
                if success:
                    logger.info(f"Bot reativado com sucesso para contato {contact_id}")
                else:
                    logger.error(f"Erro ao reativar bot para contato {contact_id}")
                    
            elif "#status" in command:
                status = await self.kommo.get_bot_status(contact_id)
                logger.info(f"Status do bot: {status}")
                
                # Buscar informações de conversa proativa
                conversation_state = await self.kommo.get_conversation_state(contact_id)
                proactive_info = ""
                vendor_info = ""
                
                if conversation_state and conversation_state.get("initiated_by_bot"):
                    proactive_info = f"""
Origem: {conversation_state.get('trigger_source', 'N/A')}
Iniciado em: {conversation_state.get('initiated_at', 'N/A')}
Primeira resposta: {'Sim' if conversation_state.get('first_response_received') else 'Não'}"""
                
                if responsible_user:
                    vendor_config = self.vendedor_config.get(responsible_user, {})
                    vendor_info = f"""
Vendedor: {responsible_user}
WhatsApp: {vendor_config.get('phone_api', 'N/A')}"""
                
                # Enviar status como mensagem
                status_message = f"""
**Status do Bot**
Contato: {status.get('contact_name', 'N/A')}
Bot Ativo: {'Sim' if status.get('bot_active') else 'Não'}
Lead ID: {status.get('lead_id', 'N/A')}
Status Lead: {status.get('lead_status', 'N/A')}{proactive_info}{vendor_info}
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
Funciona apenas para áreas: previdenciário, tributário, outros
                """.strip()
                
                await self.kommo.send_message_to_contact(contact_id, help_message)
                
        except Exception as e:
            logger.error(f"Erro ao processar comando especial: {e}")
    
    async def _process_direct_message(self, webhook_data: Dict[str, Any]):
        """Processa mensagem direta"""
        try:
            message_data = webhook_data["message"]
            
            logger.info("Mensagem direta recebida (implementar se necessário)")
            logger.info(f"Dados da mensagem: {message_data}")
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem direta: {e}")
    
    async def process_proactive_trigger(self, trigger_data: Dict[str, Any]) -> Dict[str, Any]:
        """Processa gatilho para iniciar conversa proativa"""
        try:
            logger.info(f"Processando gatilho proativo: {trigger_data}")
            
            contact_id = trigger_data.get("contact_id")
            trigger_type = trigger_data.get("trigger_type", "unknown")
            lead_data = trigger_data.get("lead_data", {})
            responsible_user = trigger_data.get("responsible_user", "default")
            area_atuacao = trigger_data.get("area_atuacao", "unknown")
            
            # Verificar se área é elegível
            if not self._should_activate_bot(area_atuacao):
                logger.info(f"Área '{area_atuacao}' não elegível para bot - ignorando gatilho")
                return {"status": "skipped", "reason": "area_not_eligible"}
            
            # Verificar se já existe conversa ativa para evitar spam
            existing_state = await self.kommo.get_conversation_state(contact_id)
            if existing_state and existing_state.get("conversation_active"):
                logger.warning(f"Conversa já ativa para contato {contact_id} - ignorando gatilho")
                return {"status": "skipped", "reason": "conversation_already_active"}
            
            # Personalizar mensagem baseada no gatilho e vendedor
            message_template = self._get_message_template(trigger_type, lead_data, responsible_user)
            
            # Enviar mensagem inicial
            result = await self.kommo.send_message_to_contact(contact_id, message_template)
            
            if "error" not in result:
                # Criar estado de conversa proativa
                await self.kommo.set_conversation_initiated(
                    contact_id=contact_id,
                    initiated=True,
                    trigger_source=trigger_type,
                    lead_data={
                        **lead_data,
                        "responsible_user": responsible_user,
                        "area_atuacao": area_atuacao
                    }
                )
                
                logger.info(f"Conversa proativa iniciada para contato {contact_id}")
                return {
                    "status": "initiated",
                    "contact_id": contact_id,
                    "trigger_type": trigger_type,
                    "responsible_user": responsible_user,
                    "message_sent": True
                }
            else:
                logger.error(f"Erro ao enviar mensagem proativa: {result}")
                return {"status": "error", "message": result.get("error")}
                
        except Exception as e:
            logger.error(f"Erro ao processar gatilho proativo: {e}")
            return {"status": "error", "message": str(e)}
    
    def _get_message_template(self, trigger_type: str, lead_data: Dict[str, Any], responsible_user: str = "default") -> str:
        """Retorna template de mensagem baseado no tipo de gatilho e vendedor"""
        name = lead_data.get("name", "")
        interest = lead_data.get("interest", "nossos serviços")
        vendor_config = self.vendedor_config.get(responsible_user, {"display_name": "Previdas"})
        vendor_name = vendor_config.get("display_name", "Previdas")
        
        templates = {
            "formulario_preenchido": f"""Olá {name}! 

Aqui é {vendor_name}. Vi que você preencheu nosso formulário sobre {interest}. 

Posso esclarecer dúvidas iniciais sobre perícias médicas?""",
            
            "material_baixado": f"""Olá {name}! 

Aqui é {vendor_name}. Obrigado por baixar nosso material sobre {interest}. 

Tenho algumas informações adicionais que podem te interessar. Gostaria de saber mais?""",
            
            "reuniao_agendada": f"""Olá {name}! 

Aqui é {vendor_name}. Vi que você agendou uma reunião conosco. 

Antes do nosso encontro, posso esclarecer alguma dúvida inicial sobre perícias médicas?""",
            
            "default": f"""Olá {name}! 

Aqui é {vendor_name}. Vi que você demonstrou interesse em {interest}. 

Como posso te ajudar?"""
        }
        
        return templates.get(trigger_type, templates["default"])