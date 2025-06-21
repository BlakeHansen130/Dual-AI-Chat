from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
from .constants import MessageSender, MessagePurpose, DiscussionMode, ResponseHandlerType

class ChatMessage(BaseModel):
    id: str
    text: str
    sender: MessageSender
    purpose: MessagePurpose
    timestamp: datetime
    duration_ms: Optional[float] = None

    class Config:
        use_enum_values = True

class APIResponse(BaseModel):
    text: str
    duration_ms: float
    error: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None

class ParsedAIResponse(BaseModel):
    spoken_text: str
    thinking_content: Optional[str] = None  # 🆕 思考过程内容
    new_notepad_content: Optional[str] = None
    discussion_should_end: bool = False

class FailedStepPayload(BaseModel):
    step_identifier: str
    prompt: str
    model_name: str
    system_instruction: Optional[str] = None
    sender: MessageSender
    purpose: MessagePurpose
    original_system_error_msg_id: str

    class Config:
        protected_namespaces = ()  # 禁用受保护命名空间检查

class SessionState(BaseModel):
    messages: List[ChatMessage] = []
    notepad_content: str = ""
    last_notepad_updated_by: Optional[MessageSender] = None
    current_turn: int = 0
    discussion_in_progress: bool = False
    
    class Config:
        use_enum_values = True