import os
import time
from typing import List, Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv
from config.constants import ResponseHandlerType
from config.models import APIResponse

# 加载环境变量
load_dotenv()


class OpenAIService:
    """OpenAI兼容API服务 - 支持多种响应格式"""
    
    def __init__(self):
        """初始化OpenAI客户端"""
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.default_model = os.getenv("DEFAULT_MODEL", "gpt-3.5-turbo")
        self.response_handler_type = ResponseHandlerType(os.getenv("RESPONSE_HANDLER_TYPE", "standard"))
        
        if not self.api_key:
            raise ValueError("未找到OPENAI_API_KEY环境变量")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    def generate_response(
        self,
        prompt: str,
        model: Optional[str] = None,
        system_instruction: Optional[str] = None,
        handler_type: Optional[ResponseHandlerType] = None
    ) -> APIResponse:
        """
        生成AI响应
        
        Args:
            prompt: 用户提示
            model: 模型名称（可选，默认使用环境变量）
            system_instruction: 系统指令（可选）
            handler_type: 响应处理类型（可选，默认使用环境变量）
            
        Returns:
            APIResponse: 包含原始响应和元数据的对象
        """
        start_time = time.time()
        
        # 使用传入的参数或默认值
        model_name = model or self.default_model
        current_handler_type = handler_type or self.response_handler_type
        
        try:
            # 构建消息
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({"role": "user", "content": prompt})
            
            # 根据处理类型选择不同的调用方式
            if current_handler_type == ResponseHandlerType.QWEN_STREAM_WITH_THINKING:
                raw_response = self._generate_qwen_stream_response(messages, model_name)
            else:
                raw_response = self._generate_standard_response(messages, model_name)
            
            duration_ms = (time.time() - start_time) * 1000
            
            return APIResponse(
                text="",  # 这里留空，让parser从raw_response中提取
                duration_ms=duration_ms,
                error=None,
                raw_response=raw_response
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_message = f"API调用失败: {str(e)}"
            
            return APIResponse(
                text=error_message,
                duration_ms=duration_ms,
                error=str(e),
                raw_response=None
            )
    
    def _generate_standard_response(self, messages: List[Dict], model_name: str) -> Dict[str, Any]:
        """生成标准（非流式）响应"""
        
        response = self.client.chat.completions.create(
            model=model_name,
            messages=messages,
            stream=False
        )
        
        # 转换为dict格式
        return response.model_dump()
    
    def _generate_qwen_stream_response(self, messages: List[Dict], model_name: str) -> Dict[str, Any]:
        """生成Qwen流式响应（带思考过程）"""
        
        completion = self.client.chat.completions.create(
            model=model_name,
            messages=messages,
            # 强制开启思考，去掉思考预算限制
            extra_body={
                "enable_thinking": True
            },
            stream=True
        )
        
        reasoning_content = ""  # 完整思考过程
        answer_content = ""     # 完整回复内容
        is_answering = False    # 是否进入回复阶段
        
        print("\n" + "=" * 20 + " 思考过程 " + "=" * 20 + "\n")
        
        for chunk in completion:
            # 跳过没有choices的chunk（通常是usage信息）
            if not chunk.choices:
                continue
            
            delta = chunk.choices[0].delta
            
            # 收集思考内容
            if hasattr(delta, "reasoning_content") and delta.reasoning_content is not None:
                if not is_answering:
                    print(delta.reasoning_content, end="", flush=True)
                reasoning_content += delta.reasoning_content
            
            # 收集回复内容
            if hasattr(delta, "content") and delta.content:
                if not is_answering:
                    print("\n" + "=" * 20 + " 完整回复 " + "=" * 20 + "\n")
                    is_answering = True
                print(delta.content, end="", flush=True)
                answer_content += delta.content
        
        print("\n")  # 换行结束
        
        # 返回包含思考过程和回复的字典
        return {
            "reasoning_content": reasoning_content,
            "answer_content": answer_content,
            "is_stream_response": True
        }
    
    def get_current_config(self) -> Dict[str, Any]:
        """获取当前配置信息"""
        return {
            "base_url": self.base_url,
            "model": self.default_model,
            "handler_type": self.response_handler_type.value
        }