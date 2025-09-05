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
    should_handoff: bool = Field(default=False, description="Se deve transferir para humano")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadados adicionais")

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

# Modelos para funcionalidade proativa
class ProactiveStart(BaseModel):
    lead_id: int = Field(..., description="ID do lead no Kommo")
    contact_id: int = Field(..., description="ID do contato no Kommo")
    trigger: str = Field(..., description="Gatilho que iniciou o contato (formulario_preenchido, material_baixado, etc)")
    lead_data: Dict[str, Any] = Field(..., description="Dados do lead para personalização")
    message_template: Optional[str] = Field(None, description="Template customizado da mensagem inicial")
    
class ConversationState(BaseModel):
    contact_id: int = Field(..., description="ID do contato")
    initiated_by_bot: bool = Field(default=False, description="Se a conversa foi iniciada pelo bot")
    first_response_received: bool = Field(default=False, description="Se o lead já respondeu à primeira mensagem")
    conversation_active: bool = Field(default=True, description="Se a conversa está ativa")
    initiated_at: Optional[str] = Field(None, description="Timestamp de quando foi iniciada")
    trigger_source: Optional[str] = Field(None, description="Fonte que originou o contato")

class ProactiveResponse(BaseModel):
    status: str = Field(..., description="Status da operação (initiated, error)")
    lead_id: int = Field(..., description="ID do lead")
    contact_id: int = Field(..., description="ID do contato")
    message_sent: bool = Field(..., description="Se a mensagem foi enviada com sucesso")
    conversation_state: Optional[ConversationState] = Field(None, description="Estado da conversa criado")
    message_content: Optional[str] = Field(None, description="Conteúdo da mensagem enviada")
    timestamp: str = Field(..., description="Timestamp da operação")

# Modelos para templates de mensagens proativas
class MessageTemplate(BaseModel):
    template_id: str = Field(..., description="ID único do template")
    name: str = Field(..., description="Nome do template")
    content: str = Field(..., description="Conteúdo do template com placeholders")
    trigger_types: List[str] = Field(..., description="Tipos de gatilho compatíveis")
    active: bool = Field(default=True, description="Se o template está ativo")

class ProactiveConfig(BaseModel):
    enabled: bool = Field(default=True, description="Se a funcionalidade proativa está habilitada")
    default_template: str = Field(..., description="Template padrão a usar")
    delay_minutes: int = Field(default=5, description="Delay em minutos antes de enviar")
    max_attempts: int = Field(default=1, description="Máximo de tentativas de contato proativo")
    business_hours_only: bool = Field(default=True, description="Apenas em horário comercial")

# Modelo para relatórios de contatos proativos
class ProactiveReport(BaseModel):
    period_start: str = Field(..., description="Início do período")
    period_end: str = Field(..., description="Fim do período")
    total_initiated: int = Field(..., description="Total de conversas iniciadas")
    responses_received: int = Field(..., description="Total de respostas recebidas")
    conversion_rate: float = Field(..., description="Taxa de conversão (respostas/iniciadas)")
    by_trigger: Dict[str, int] = Field(..., description="Breakdown por tipo de gatilho")
    by_template: Dict[str, int] = Field(..., description="Breakdown por template usado")

# Modelos para OAuth2 e Token Management
class OAuthTokenRequest(BaseModel):
    code: str = Field(..., description="Código de autorização OAuth")
    client_id: str = Field(..., description="Client ID da aplicação")
    client_secret: str = Field(..., description="Client Secret da aplicação")
    redirect_uri: str = Field(..., description="URI de redirecionamento")

class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="Refresh token para renovação")
    client_id: Optional[str] = Field(None, description="Client ID da aplicação")
    client_secret: Optional[str] = Field(None, description="Client Secret da aplicação")

class OAuthTokenResponse(BaseModel):
    access_token: str = Field(..., description="Token de acesso")
    refresh_token: str = Field(..., description="Token de renovação")
    token_type: str = Field(default="Bearer", description="Tipo do token")
    expires_in: int = Field(..., description="Tempo de expiração em segundos")

class OAuthStatusResponse(BaseModel):
    oauth_configured: bool = Field(..., description="Se OAuth está configurado")
    client_id: Optional[str] = Field(None, description="Client ID (parcial)")
    account_id: Optional[str] = Field(None, description="ID da conta")
    api_url: Optional[str] = Field(None, description="URL da API")
    token_expires_at: Optional[str] = Field(None, description="Data de expiração do token")
    token_expired: Optional[bool] = Field(None, description="Se o token está expirado")

# Modelos para sistema de agendamento
class AgendamentoPayload(BaseModel):
    contact_id: int = Field(..., description="ID do contato no Kommo")
    lead_id: int = Field(..., description="ID do lead no Kommo")
    vendedor: str = Field(..., description="Nome do vendedor")
    area_atuacao: str = Field(..., description="Área de atuação")
    trigger_type: str = Field(..., description="Tipo de gatilho")
    lead_data: Dict[str, Any] = Field(..., description="Dados do lead")
    agenda_data: Optional[Dict[str, Any]] = Field(None, description="Dados específicos do agendamento")

class VendedorCustom(BaseModel):
    name: str = Field(..., description="Nome do vendedor")
    phone_api: str = Field(..., description="API do telefone")
    display_name: str = Field(..., description="Nome de exibição")
    area_atuacao: Optional[str] = Field(None, description="Área de atuação")
    ativo: bool = Field(default=True, description="Se o vendedor está ativo")
