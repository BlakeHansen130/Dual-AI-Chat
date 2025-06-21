"""
配置模块

包含项目的常量定义、数据模型和配置类。
"""

from .constants import (
    MessageSender, MessagePurpose, DiscussionMode, ResponseHandlerType,
    COGNITO_SYSTEM_PROMPT, MUSE_SYSTEM_PROMPT, INITIAL_NOTEPAD_CONTENT,
    NOTEPAD_UPDATE_START, NOTEPAD_UPDATE_END, DISCUSSION_COMPLETE_TAG
)

from .models import (
    ChatMessage, APIResponse, ParsedAIResponse, FailedStepPayload, SessionState
)

__all__ = [
    # 枚举类
    'MessageSender', 'MessagePurpose', 'DiscussionMode', 'ResponseHandlerType',
    
    # 系统提示词
    'COGNITO_SYSTEM_PROMPT', 'MUSE_SYSTEM_PROMPT',
    
    # 标签常量
    'NOTEPAD_UPDATE_START', 'NOTEPAD_UPDATE_END', 'DISCUSSION_COMPLETE_TAG',
    
    # 初始内容
    'INITIAL_NOTEPAD_CONTENT',
    
    # 数据模型
    'ChatMessage', 'APIResponse', 'ParsedAIResponse', 'FailedStepPayload', 'SessionState'
]