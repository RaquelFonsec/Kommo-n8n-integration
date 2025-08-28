from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Union
from datetime import datetime

class KommoMessage(BaseModel):
    id: int
    contact_id: int
    conversation_id: str
    text: str
    timestamp: datetime
    chat_type: str = "whatsapp"
    author: Optional[Dict[str, Any]] = None

class KommoWebhook(BaseModel):
    account: Optional[Dict[str, Any]] = None
    leads: Optional[Dict[str, Any]] = None
    contacts: Optional[Dict[str, Any]] = None
    message: Optional[Dict[str, Any]] = None
    chats: Optional[Dict[str, Any]] = None

class N8nPayload(BaseModel):
    conversation_id: str
    contact_id: int
    message_text: str
    timestamp: str
    chat_type: str = "whatsapp"
    lead_id: Optional[int] = None
    contact_name: Optional[str] = None
    
class KommoContact(BaseModel):
    id: int
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None

class KommoLead(BaseModel):
    id: int
    name: str
    status_id: int
    pipeline_id: int
    contact_id: Optional[int] = None
    custom_fields: Optional[Dict[str, Any]] = None

# Modelos para endpoints específicos
class N8nResponse(BaseModel):
    conversation_id: str = Field(..., description="ID da conversa")
    response: str = Field(..., description="Resposta da IA")
    should_send: bool = Field(default=True, description="Se deve enviar a resposta")

class BotCommand(BaseModel):
    contact_id: int = Field(..., description="ID do contato")
    command: str = Field(..., description="Comando a executar (pause, resume, status)")

class WebhookResponse(BaseModel):
    status: str = Field(..., description="Status da operação")
    message: str = Field(..., description="Mensagem de resposta")
    timestamp: str = Field(..., description="Timestamp da operação")

class BotStatusResponse(BaseModel):
    contact_id: int = Field(..., description="ID do contato")
    bot_active: bool = Field(..., description="Se o bot está ativo")
    contact_name: str = Field(..., description="Nome do contato")
    lead_id: Optional[int] = Field(None, description="ID do lead")
    lead_status: Optional[str] = Field(None, description="Status do lead")
    source: Optional[str] = Field(None, description="Fonte dos dados")

class TestResponse(BaseModel):
    test_type: str = Field(..., description="Tipo de teste")
    status: str = Field(..., description="Status do teste")
    message: str = Field(..., description="Mensagem do teste")
    timestamp: str = Field(..., description="Timestamp do teste")
    test_contact_id: Optional[int] = Field(None, description="ID do contato de teste")
    contact_found: Optional[bool] = Field(None, description="Se o contato foi encontrado")

# Modelo unificado para resposta do bot command
class BotCommandResponse(BaseModel):
    response_type: str = Field(..., description="Tipo de resposta (status ou command)")
    data: Union[WebhookResponse, BotStatusResponse] = Field(..., description="Dados da resposta")
