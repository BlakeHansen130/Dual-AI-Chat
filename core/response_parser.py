import re
from typing import Dict, Any, Optional
from config.constants import ResponseHandlerType, NOTEPAD_UPDATE_START, NOTEPAD_UPDATE_END, DISCUSSION_COMPLETE_TAG
from config.models import ParsedAIResponse


class ResponseParser:
    """AI响应解析器 - 处理不同格式的API响应并解析业务标签"""
    
    @staticmethod
    def parse_ai_response(
        raw_response: Any, 
        handler_type: ResponseHandlerType,
        model_name: str = "未知模型",
        player_name: str = "AI"
    ) -> ParsedAIResponse:
        """
        解析AI响应的主入口
        
        Args:
            raw_response: API的原始响应
            handler_type: 响应处理类型
            model_name: 模型名称（用于日志）
            player_name: AI角色名称（用于日志）
            
        Returns:
            ParsedAIResponse: 解析后的响应对象
        """
        try:
            # 第一步：从原始响应中提取内容和思考过程
            content, thinking_content = ResponseParser._extract_content_from_response(
                raw_response, handler_type, model_name, player_name
            )
            
            # 第二步：解析业务标签
            parsed_response = ResponseParser._parse_special_tags(content)
            
            # 第三步：添加思考过程
            parsed_response.thinking_content = thinking_content
            
            return parsed_response
            
        except Exception as e:
            print(f"!! [{player_name}] 响应解析出错: {e}")
            return ParsedAIResponse(
                spoken_text=f"(AI回复解析失败: {str(e)})",
                thinking_content=None,
                new_notepad_content=None,
                discussion_should_end=False
            )
    
    @staticmethod
    def _extract_content_from_response(
        raw_response: Any,
        handler_type: ResponseHandlerType, 
        model_name: str,
        player_name: str
    ) -> tuple[str, Optional[str]]:
        """从不同格式的响应中提取内容"""
        
        if handler_type == ResponseHandlerType.STANDARD:
            content = ResponseParser._extract_standard_openai_content(raw_response, model_name, player_name)
            return content, None
            
        elif handler_type == ResponseHandlerType.THINK_TAGS_IN_CONTENT:
            content = ResponseParser._extract_standard_openai_content(raw_response, model_name, player_name)
            return ResponseParser._remove_think_tags(content)
            
        elif handler_type == ResponseHandlerType.QWEN_STREAM_WITH_THINKING:
            content, thinking = ResponseParser._extract_qwen_stream_content(raw_response, model_name, player_name)
            return content, thinking
            
        elif handler_type == ResponseHandlerType.CONTENT_WITH_SEPARATE_REASONING:
            content, thinking = ResponseParser._extract_content_with_separate_reasoning(raw_response, model_name, player_name)
            return content, thinking
                
        else:
            raise ValueError(f"不支持的响应处理类型: {handler_type}")
    
    @staticmethod
    def _extract_standard_openai_content(raw_response: Any, model_name: str, player_name: str) -> str:
        """提取标准OpenAI格式的内容"""
        
        if not isinstance(raw_response, dict):
            raise ValueError(f"标准格式期望dict类型，实际得到: {type(raw_response)}")
        
        if "choices" not in raw_response:
            raise ValueError("响应中缺少'choices'字段")
        
        choices = raw_response["choices"]
        if not choices or len(choices) == 0:
            raise ValueError("响应中'choices'数组为空")
        
        choice = choices[0]
        if "message" not in choice:
            raise ValueError("响应中缺少'message'字段")
        
        message = choice["message"]
        if "content" not in message:
            raise ValueError("响应中缺少'content'字段")
        
        content = message["content"]
        if content is None:
            raise ValueError("响应content为None")
            
        return str(content).strip()
    
    @staticmethod
    def _extract_qwen_stream_content(raw_response: Any, model_name: str, player_name: str) -> tuple[str, Optional[str]]:
        """提取Qwen流式响应的内容"""
        
        if not isinstance(raw_response, dict):
            raise ValueError(f"Qwen流式格式期望dict类型，实际得到: {type(raw_response)}")
        
        # 提取回复内容
        if "answer_content" not in raw_response:
            raise ValueError("Qwen流式响应中缺少'answer_content'字段")
        
        answer_content = raw_response["answer_content"]
        if answer_content is None:
            raise ValueError("Qwen流式响应answer_content为None")
        
        # 提取思考内容
        thinking_content = None
        if "reasoning_content" in raw_response and raw_response["reasoning_content"]:
            thinking_content = str(raw_response["reasoning_content"]).strip()
            
        return str(answer_content).strip(), thinking_content
    
    @staticmethod
    def _extract_content_with_separate_reasoning(raw_response: Any, model_name: str, player_name: str) -> tuple[str, Optional[str]]:
        """提取包含独立reasoning_content字段的响应内容"""
        
        if not isinstance(raw_response, dict):
            raise ValueError(f"content_with_separate_reasoning格式期望dict类型，实际得到: {type(raw_response)}")
        
        # 提取标准的message.content作为主要回复
        main_content = ResponseParser._extract_standard_openai_content(raw_response, model_name, player_name)
        
        # 提取思考内容
        thinking_content = None
        if "reasoning_content" in raw_response and raw_response["reasoning_content"]:
            thinking_content = str(raw_response["reasoning_content"]).strip()
            
        return main_content, thinking_content
    
    @staticmethod
    def _remove_think_tags(content: str) -> tuple[str, Optional[str]]:
        """提取并移除内容中的<think>...</think>标签"""
        if not isinstance(content, str):
            return content, None
        
        # 查找思考标签
        think_pattern = re.compile(r"<think.*?>(.*?)</think>", re.DOTALL | re.IGNORECASE)
        think_matches = think_pattern.findall(content)
        
        # 提取思考内容
        thinking_content = None
        if think_matches:
            # 合并所有思考内容
            thinking_content = "\n".join(match.strip() for match in think_matches)
        
        # 移除思考标签
        cleaned = re.sub(
            r"<think.*?>.*?</think>\s*", 
            "", 
            content, 
            flags=re.DOTALL | re.IGNORECASE
        )
        
        return cleaned.strip(), thinking_content
    
    @staticmethod
    def _parse_special_tags(content: str) -> ParsedAIResponse:
        """解析内容中的业务标签（记事本更新和讨论结束）"""
        
        current_text = content.strip()
        spoken_text = ""
        new_notepad_content = None
        discussion_should_end = False
        
        # 解析记事本更新标签
        notepad_start_index = current_text.rfind(NOTEPAD_UPDATE_START)
        notepad_end_index = current_text.rfind(NOTEPAD_UPDATE_END)
        
        if (notepad_start_index != -1 and 
            notepad_end_index != -1 and 
            notepad_end_index > notepad_start_index and 
            current_text.endswith(NOTEPAD_UPDATE_END)):
            
            # 提取记事本内容
            new_notepad_content = current_text[
                notepad_start_index + len(NOTEPAD_UPDATE_START):notepad_end_index
            ].strip()
            
            # 提取spoken text（记事本更新之前的部分）
            spoken_text = current_text[:notepad_start_index].strip()
        else:
            spoken_text = current_text
        
        # 检查讨论结束标志
        if DISCUSSION_COMPLETE_TAG in spoken_text:
            discussion_should_end = True
            # 移除讨论结束标签
            spoken_text = re.sub(
                re.escape(DISCUSSION_COMPLETE_TAG).replace(r'\/', '/'), 
                "", 
                spoken_text
            ).strip()
        
        # 处理空的spoken_text情况
        if not spoken_text.strip():
            action_parts = []
            if new_notepad_content:
                action_parts.append("更新了记事本")
            if discussion_should_end:
                action_parts.append("建议结束讨论")
            
            if action_parts:
                spoken_text = f"(AI {' 并 '.join(action_parts)})"
            else:
                spoken_text = "(AI 未提供文本回复)"
        
        return ParsedAIResponse(
            spoken_text=spoken_text.strip(),
            thinking_content=None,  # 将在主函数中设置
            new_notepad_content=new_notepad_content,
            discussion_should_end=discussion_should_end
        )