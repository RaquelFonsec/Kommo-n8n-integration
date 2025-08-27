from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
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
