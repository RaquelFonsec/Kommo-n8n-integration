from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Union
from datetime import datetime

# ==========================================
# MODELOS BASE KOMMO
# ==========================================

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

# ==========================================
# MODELOS PRINCIPAIS - COMPATÍVEIS COM MAIN.PY
# ==========================================

class ProactiveStart(BaseModel):
    """CORRIGIDO: Modelo compatível com main.py"""
    contact_id: int = Field(..., description="ID do contato no Kommo")
    lead_id: int = Field(..., description="ID do lead no Kommo")
    vendedor: str = Field(..., description="Nome do vendedor responsável")
    area_atuacao: str = Field(..., description="Área de atuação (previdenciario, tributario, outros)")
    trigger_type: str = Field(default="formulario_preenchido", description="Tipo de gatilho (formulario_preenchido, material_baixado, etc)")
    lead_data: Optional[Dict[str, Any]] = Field(None, description="Dados do lead para personalização")
    custom_message: Optional[str] = Field(None, description="Mensagem customizada (opcional)")

# REMOVIDO: DistribuicaoPayload - distribuição automática feita pelo n8n
# class DistribuicaoPayload(BaseModel): - REMOVIDO

class N8nResponse(BaseModel):
    """CORRIGIDO: Modelo compatível com main.py"""
    conversation_id: str = Field(..., description="ID da conversa")
    response_text: str = Field(..., description="Texto da resposta da IA")
    response_type: Optional[str] = Field(None, description="Tipo de resposta")
    confidence: Optional[float] = Field(None, description="Confiança da IA")
    should_send: bool = Field(default=True, description="Se deve enviar a resposta")
    should_handoff: bool = Field(default=False, description="Se deve transferir para humano")
    next_action: Optional[str] = Field(None, description="Próxima ação sugerida")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadados adicionais")

class BotCommand(BaseModel):
    """Modelo para controle do bot"""
    contact_id: int = Field(..., description="ID do contato")
    command: str = Field(..., description="Comando (pause, resume, status)")

class VendedorCustom(BaseModel):
    """NOVO: Modelo para adicionar vendedores customizados"""
    name: str = Field(..., description="Nome do vendedor")
    display_name: str = Field(..., description="Nome para exibição")
    phone_api: str = Field(..., description="ID da API do telefone")
    whatsapp_number: str = Field(..., description="Número do WhatsApp Business")
    email: Optional[str] = Field(None, description="Email do vendedor")
    area_atuacao: Optional[str] = Field(None, description="Área de atuação especializada")

class AgendamentoPayload(BaseModel):
    """NOVO: Modelo para solicitações de agendamento"""
    contact_id: int = Field(..., description="ID do contato")
    lead_id: Optional[int] = Field(None, description="ID do lead")
    conversation_id: Optional[str] = Field(None, description="ID da conversa")
    vendedor_requested: Optional[str] = Field(None, description="Vendedor solicitado")
    agenda_data: Dict[str, Any] = Field(..., description="Dados do agendamento")
    client_data: Optional[Dict[str, Any]] = Field(None, description="Dados adicionais do cliente")

# ==========================================
# MODELOS DE PAYLOAD PARA N8N
# ==========================================

class N8nPayload(BaseModel):
    """Payload completo para envio ao n8n"""
    conversation_id: str = Field(..., description="ID da conversa")
    contact_id: int = Field(..., description="ID do contato")
    message_text: str = Field(..., description="Texto da mensagem")
    timestamp: str = Field(..., description="Timestamp da mensagem")
    chat_type: str = Field(default="whatsapp", description="Tipo do chat")
    lead_id: Optional[int] = Field(None, description="ID do lead")
    contact_name: Optional[str] = Field(None, description="Nome do contato")
    
    # Contexto proativo
    proactive_context: Optional[Dict[str, Any]] = Field(None, description="Contexto de conversas proativas")
    
    # Contexto do vendedor
    vendor_context: Optional[Dict[str, Any]] = Field(None, description="Contexto do vendedor responsável")
    
    # Contexto para Supabase/agendamento
    supabase_context: Optional[Dict[str, Any]] = Field(None, description="Contexto para sistema de agendamento")

class WhatsAppPayload(BaseModel):
    """Payload para envio via WhatsApp Business API"""
    action: str = Field(..., description="Ação a executar")
    from_vendor: Optional[Dict[str, Any]] = Field(None, description="Dados do vendedor remetente")
    to_client: Dict[str, Any] = Field(..., description="Dados do cliente destinatário")
    message: str = Field(..., description="Mensagem a enviar")
    timestamp: str = Field(..., description="Timestamp do envio")
    source: str = Field(default="proactive_bot", description="Fonte da mensagem")
    routing: Optional[Dict[str, Any]] = Field(None, description="Dados de roteamento")

# ==========================================
# MODELOS DE RESPOSTA
# ==========================================

class WebhookResponse(BaseModel):
    """Resposta padrão para webhooks"""
    status: str = Field(..., description="Status da operação")
    message: str = Field(..., description="Mensagem de resposta")
    timestamp: str = Field(..., description="Timestamp da operação")
    conversation_id: Optional[str] = Field(None, description="ID da conversa")
    contact_id: Optional[int] = Field(None, description="ID do contato")

class ProactiveResponse(BaseModel):
    """Resposta para conversas proativas"""
    status: str = Field(..., description="Status (sent, error, skipped)")
    conversation_id: str = Field(..., description="ID da conversa criada")
    contact_id: int = Field(..., description="ID do contato")
    lead_id: int = Field(..., description="ID do lead")
    vendedor: str = Field(..., description="Vendedor responsável")
    message_sent: str = Field(..., description="Mensagem enviada")
    message_sent_at: str = Field(..., description="Timestamp do envio")
    vendor_config: Optional[Dict[str, Any]] = Field(None, description="Configuração do vendedor")
    send_result: Optional[Dict[str, Any]] = Field(None, description="Resultado do envio")
    next_step: str = Field(..., description="Próximo passo no fluxo")

class DistribuicaoResponse(BaseModel):
    """Resposta para distribuição de leads"""
    status: str = Field(..., description="Status da distribuição")
    lead_id: int = Field(..., description="ID do lead")
    vendedor: str = Field(..., description="Vendedor atribuído")
    area_atuacao: str = Field(..., description="Área de atuação")
    proativo_resultado: Dict[str, Any] = Field(..., description="Resultado do envio proativo")
    next_steps: List[str] = Field(..., description="Próximos passos")
    distribuicao_id: int = Field(..., description="ID da distribuição")
    timestamp: str = Field(..., description="Timestamp da distribuição")

class BotStatusResponse(BaseModel):
    """Resposta de status do bot"""
    contact_id: int = Field(..., description="ID do contato")
    bot_active: bool = Field(..., description="Se o bot está ativo")
    conversation_state: Optional[Dict[str, Any]] = Field(None, description="Estado da conversa")
    timestamp: str = Field(..., description="Timestamp da consulta")

class ApiHealthResponse(BaseModel):
    """Resposta de health check da API"""
    status: str = Field(..., description="Status da API")
    version: str = Field(..., description="Versão da API")
    timestamp: str = Field(..., description="Timestamp da verificação")
    configuration: Dict[str, Any] = Field(..., description="Status da configuração")
    features: List[str] = Field(..., description="Funcionalidades ativas")

class VendedorResponse(BaseModel):
    """Resposta com dados de vendedores"""
    vendedores_reais: List[Dict[str, Any]] = Field(..., description="Vendedores reais do Kommo")
    vendedores_ficticios: List[Dict[str, Any]] = Field(..., description="Vendedores fictícios configurados")
    total_reais: int = Field(..., description="Total de vendedores reais")
    total_ficticios: int = Field(..., description="Total de vendedores fictícios")
    total: int = Field(..., description="Total geral")
    system: str = Field(..., description="Sistema utilizado")
    cache_info: Optional[Dict[str, Any]] = Field(None, description="Informações do cache")

# ==========================================
# MODELOS DE ESTADO E CONFIGURAÇÃO
# ==========================================

class ConversationState(BaseModel):
    """Estado de uma conversa"""
    lead_id: int = Field(..., description="ID do lead")
    conversation_id: str = Field(..., description="ID da conversa")
    vendedor: str = Field(..., description="Vendedor responsável")
    area_atuacao: str = Field(..., description="Área de atuação")
    trigger_type: str = Field(..., description="Tipo de gatilho")
    initiated_at: str = Field(..., description="Timestamp de início")
    initiated_by_bot: bool = Field(default=True, description="Se foi iniciada pelo bot")
    active: bool = Field(default=True, description="Se está ativa")
    message_sent: str = Field(..., description="Mensagem enviada")
    lead_data: Dict[str, Any] = Field(..., description="Dados do lead")
    phone_number: Optional[str] = Field(None, description="Número de telefone")
    first_response_received: Optional[bool] = Field(None, description="Se recebeu primeira resposta")
    first_response_at: Optional[str] = Field(None, description="Timestamp da primeira resposta")
    paused_at: Optional[str] = Field(None, description="Timestamp de pausa")
    resumed_at: Optional[str] = Field(None, description="Timestamp de retomada")

class VendedorConfig(BaseModel):
    """Configuração de um vendedor"""
    name: str = Field(..., description="Nome do vendedor")
    whatsapp_number: str = Field(..., description="Número do WhatsApp Business")
    display_name: str = Field(..., description="Nome para exibição")
    phone_api: str = Field(..., description="ID da API do telefone")
    user_id: Optional[int] = Field(None, description="ID no Kommo")
    is_real_user: bool = Field(default=False, description="Se é usuário real do Kommo")
    source: str = Field(..., description="Fonte da configuração")
    area_especialidade: List[str] = Field(default_factory=list, description="Áreas de especialidade")
    email: Optional[str] = Field(None, description="Email do vendedor")

# ==========================================
# MODELOS DE RELATÓRIOS E ESTATÍSTICAS
# ==========================================

class ConversationStats(BaseModel):
    """Estatísticas de conversas"""
    total: int = Field(..., description="Total de conversas")
    active: int = Field(..., description="Conversas ativas")
    with_response: int = Field(..., description="Com resposta do lead")
    response_rate: float = Field(..., description="Taxa de resposta (%)")

class VendorStats(BaseModel):
    """Estatísticas por vendedor"""
    total: int = Field(default=0, description="Total de conversas")
    active: int = Field(default=0, description="Conversas ativas")
    with_response: int = Field(default=0, description="Com resposta")

class ApiStats(BaseModel):
    """Estatísticas gerais da API"""
    timestamp: str = Field(..., description="Timestamp das estatísticas")
    conversations: ConversationStats = Field(..., description="Estatísticas de conversas")
    by_vendor: Dict[str, VendorStats] = Field(..., description="Estatísticas por vendedor")
    by_trigger: Dict[str, int] = Field(..., description="Estatísticas por gatilho")
    bot_status_cache_size: int = Field(..., description="Tamanho do cache de status")

class ProactiveReport(BaseModel):
    """Relatório de contatos proativos"""
    period_start: str = Field(..., description="Início do período")
    period_end: str = Field(..., description="Fim do período")
    total_initiated: int = Field(..., description="Total de conversas iniciadas")
    responses_received: int = Field(..., description="Total de respostas recebidas")
    conversion_rate: float = Field(..., description="Taxa de conversão")
    by_trigger: Dict[str, int] = Field(..., description="Breakdown por gatilho")
    by_vendor: Dict[str, int] = Field(..., description="Breakdown por vendedor")

# ==========================================
# MODELOS DE TESTE E DEBUG
# ==========================================

class TestRequest(BaseModel):
    """Requisição de teste"""
    test_type: str = Field(..., description="Tipo de teste")
    contact_id: Optional[int] = Field(None, description="ID de contato para teste")
    vendedor_name: Optional[str] = Field(None, description="Nome do vendedor para teste")
    target_number: Optional[str] = Field(None, description="Número de destino")
    message: Optional[str] = Field(None, description="Mensagem de teste")

class TestResponse(BaseModel):
    """Resposta de teste"""
    test_type: str = Field(..., description="Tipo de teste executado")
    status: str = Field(..., description="Status do teste")
    message: str = Field(..., description="Mensagem do resultado")
    timestamp: str = Field(..., description="Timestamp do teste")
    test_data: Optional[Dict[str, Any]] = Field(None, description="Dados do teste")
    errors: Optional[List[str]] = Field(None, description="Erros encontrados")

class DebugInfo(BaseModel):
    """Informações de debug"""
    proactive_conversations: Dict[str, Any] = Field(..., description="Conversas proativas ativas")
    bot_status_cache: Dict[str, Any] = Field(..., description="Cache de status dos bots")
    total_conversations: int = Field(..., description="Total de conversas")
    total_bot_statuses: int = Field(..., description="Total de status de bot")
    memory_usage: Optional[Dict[str, Any]] = Field(None, description="Uso de memória")

# ==========================================
# MODELOS DE TEMPLATES E CONFIGURAÇÃO
# ==========================================

class MessageTemplate(BaseModel):
    """Template de mensagem"""
    template_id: str = Field(..., description="ID único do template")
    name: str = Field(..., description="Nome do template")
    content: str = Field(..., description="Conteúdo com placeholders")
    trigger_types: List[str] = Field(..., description="Tipos de gatilho compatíveis")
    active: bool = Field(default=True, description="Se está ativo")
    variables: List[str] = Field(default_factory=list, description="Variáveis disponíveis")

class ProactiveConfig(BaseModel):
    """Configuração do sistema proativo"""
    enabled: bool = Field(default=True, description="Se está habilitado")
    default_template: str = Field(..., description="Template padrão")
    delay_minutes: int = Field(default=5, description="Delay antes do envio")
    max_attempts: int = Field(default=1, description="Máximo de tentativas")
    business_hours_only: bool = Field(default=True, description="Apenas horário comercial")
    eligible_areas: List[str] = Field(default_factory=lambda: ["previdenciario", "tributario", "outros"], description="Áreas elegíveis")

class SystemConfig(BaseModel):
    """Configuração geral do sistema"""
    kommo_configured: bool = Field(..., description="Se Kommo está configurado")
    n8n_configured: bool = Field(..., description="Se n8n está configurado")
    vendedores_configurados: int = Field(..., description="Número de vendedores configurados")
    environment: str = Field(..., description="Ambiente (development/production)")
    features_enabled: List[str] = Field(..., description="Funcionalidades habilitadas")
    version: str = Field(..., description="Versão da API")