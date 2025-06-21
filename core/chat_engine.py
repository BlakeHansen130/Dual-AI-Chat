import os
import asyncio
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dotenv import load_dotenv

from config.constants import (
    MessageSender, MessagePurpose, DiscussionMode, ResponseHandlerType,
    COGNITO_SYSTEM_PROMPT, MUSE_SYSTEM_PROMPT, INITIAL_NOTEPAD_CONTENT,
    MAX_AUTO_RETRIES, RETRY_DELAY_BASE_MS, DISCUSSION_COMPLETE_TAG,
    DEFAULT_SHOW_THINKING_TO_USER, DEFAULT_SEND_THINKING_TO_AI
)
from config.models import ChatMessage, ParsedAIResponse, FailedStepPayload
from core.openai_service import OpenAIService
from core.response_parser import ResponseParser
from core.notepad_manager import NotepadManager
from ui.terminal_ui import TerminalUI

# 加载环境变量
load_dotenv()


class ChatEngine:
    """AI辩论聊天引擎 - 整合所有模块实现完整的辩论流程"""
    
    def __init__(self):
        """初始化聊天引擎"""
        # 初始化核心服务
        self.openai_service = OpenAIService()
        self.notepad_manager = NotepadManager()
        self.ui = TerminalUI()
        
        # 读取配置
        self.model_name = os.getenv("DEFAULT_MODEL", "gpt-3.5-turbo")
        self.handler_type = ResponseHandlerType(os.getenv("RESPONSE_HANDLER_TYPE", "standard"))
        self.show_thinking_to_user = os.getenv("SHOW_THINKING_TO_USER", "true").lower() == "true"
        self.send_thinking_to_ai = os.getenv("SEND_THINKING_TO_AI", "false").lower() == "true"
        
        # 讨论配置
        self.discussion_mode = DiscussionMode.FIXED_TURNS  # 可以后续改为可配置
        self.max_turns = 3  # 更新为3轮，提供更充分的辩论
        
        # 会话状态
        self.messages: List[ChatMessage] = []
        self.discussion_log: List[str] = []
        self.current_turn = 0
        self.session_id = f"session_{int(time.time())}"
        self.session_start_time = datetime.now()  # 添加会话开始时间
        self.thinking_records: List[Dict[str, Any]] = []  # 记录思考过程
        
        # 显示配置信息
        config_info = self.openai_service.get_current_config()
        self.ui.show_header(config_info)
    
    async def start_interactive_session(self):
        """启动交互式会话"""
        self.ui.show_welcome_animation()
        
        try:
            while True:
                # 获取用户输入
                user_input = self.ui.get_user_input()
                
                if not user_input.strip():
                    self.ui.show_system_message("请输入有效的问题", "提示")
                    continue
                
                # 处理用户输入
                await self.process_user_input(user_input)
                
                # 显示会话统计
                self.ui.show_session_stats()
                
        except KeyboardInterrupt:
            self.ui.show_system_message("用户终止会话", "信息")
        except Exception as e:
            self.ui.show_error(f"会话出现异常: {str(e)}", "严重错误")
        finally:
            self.ui.show_system_message("感谢使用 Dual AI Chat！", "再见")
    
    async def process_user_input(self, user_input: str) -> bool:
        """
        处理用户输入，执行完整的AI辩论流程
        
        Args:
            user_input: 用户输入的问题
            
        Returns:
            bool: 处理是否成功
        """
        # 重置状态
        self.discussion_log.clear()
        self.current_turn = 0
        
        # 显示用户消息
        self.ui.show_user_message(user_input)
        
        # 添加用户消息到历史
        user_message = ChatMessage(
            id=self._generate_message_id(),
            text=user_input,
            sender=MessageSender.USER,
            purpose=MessagePurpose.USER_INPUT,
            timestamp=datetime.now()
        )
        self.messages.append(user_message)
        
        try:
            # 第一阶段：Cognito初始分析
            cognito_initial_success = await self._cognito_initial_analysis(user_input)
            if not cognito_initial_success:
                return False
            
            # 第二阶段：AI辩论循环
            discussion_success = await self._discussion_loop(user_input)
            if not discussion_success:
                return False
            
            # 第三阶段：Cognito最终答案
            final_answer_success = await self._cognito_final_answer(user_input)
            if not final_answer_success:
                return False
            
            # 显示讨论结束
            self.ui.show_discussion_end("AI辩论完成，已生成最终答案")
            return True
            
        except Exception as e:
            self.ui.show_error(f"处理用户输入时出错: {str(e)}", "处理错误")
            return False
    
    async def _cognito_initial_analysis(self, user_input: str) -> bool:
        """Cognito初始分析阶段"""
        self.ui.show_system_message("🧠 Cognito 开始初步分析...")
        
        # 构建初始分析提示
        initial_prompt = f"""用户的查询是: "{user_input}"

请针对此查询提供您的初步想法或分析，以便 {MessageSender.MUSE.value} (创意型AI) 可以回应并与您开始讨论。请用中文回答。"""
        
        # 构建包含记事本的系统提示
        system_prompt = self._build_prompt_with_notepad(COGNITO_SYSTEM_PROMPT)
        
        # 执行AI调用
        parsed_response = await self._execute_ai_turn(
            sender=MessageSender.COGNITO,
            prompt=initial_prompt,
            system_prompt=system_prompt,
            purpose=MessagePurpose.COGNITO_TO_MUSE,
            step_identifier="cognito-initial-analysis"
        )
        
        if not parsed_response:
            return False
        
        # 更新讨论日志
        self.discussion_log.append(f"{MessageSender.COGNITO.value}: {parsed_response.spoken_text}")
        
        return True
    
    async def _discussion_loop(self, user_input: str) -> bool:
        """AI辩论循环"""
        previous_ai_signaled_stop = False
        
        for turn in range(self.max_turns):
            self.current_turn = turn + 1
            self.ui.show_discussion_progress(self.current_turn, self.max_turns, "fixed")
            
            # Muse回应Cognito
            muse_success = await self._muse_response_turn(user_input, previous_ai_signaled_stop)
            if not muse_success:
                return False
                
            # 检查Muse是否建议结束讨论
            last_muse_response = self._get_last_parsed_response(MessageSender.MUSE)
            if last_muse_response and self.discussion_mode == DiscussionMode.AI_DRIVEN:
                if last_muse_response.discussion_should_end:
                    if previous_ai_signaled_stop:
                        self.ui.show_system_message("双方AI已同意结束讨论")
                        break
                    previous_ai_signaled_stop = True
                    self.ui.show_system_message(f"{MessageSender.MUSE.value} 建议结束讨论，等待 {MessageSender.COGNITO.value} 回应")
                else:
                    previous_ai_signaled_stop = False
            
            # 如果是最后一轮，不需要Cognito再回应
            if turn >= self.max_turns - 1:
                break
                
            # Cognito回应Muse  
            cognito_success = await self._cognito_response_turn(user_input, previous_ai_signaled_stop)
            if not cognito_success:
                return False
                
            # 检查Cognito是否建议结束讨论
            last_cognito_response = self._get_last_parsed_response(MessageSender.COGNITO)
            if last_cognito_response and self.discussion_mode == DiscussionMode.AI_DRIVEN:
                if last_cognito_response.discussion_should_end:
                    if previous_ai_signaled_stop:
                        self.ui.show_system_message("双方AI已同意结束讨论")
                        break
                    previous_ai_signaled_stop = True
                    self.ui.show_system_message(f"{MessageSender.COGNITO.value} 建议结束讨论，等待 {MessageSender.MUSE.value} 回应")
                else:
                    previous_ai_signaled_stop = False
        
        return True
    
    async def _muse_response_turn(self, user_input: str, previous_ai_signaled_stop: bool) -> bool:
        """Muse回应Cognito的轮次"""
        self.ui.show_system_message(f"🎭 {MessageSender.MUSE.value} 正在回应 {MessageSender.COGNITO.value}...")
        
        # 获取最后一条Cognito消息
        last_cognito_text = self._get_last_spoken_text(MessageSender.COGNITO)
        
        # 构建Muse的提示
        muse_prompt = f"""用户的查询是: "{user_input}"

当前讨论 (均为中文):
{chr(10).join(self.discussion_log)}

{MessageSender.COGNITO.value} (逻辑AI) 刚刚说: "{last_cognito_text}"

请回复 {MessageSender.COGNITO.value}。继续讨论。保持您的回复简洁并使用中文。"""
        
        # 如果前一个AI建议结束讨论，添加相关指令
        if previous_ai_signaled_stop:
            muse_prompt += f"\n\n{MessageSender.COGNITO.value} 已包含 {DISCUSSION_COMPLETE_TAG} 建议结束讨论。如果您同意，请在您的回复中也包含 {DISCUSSION_COMPLETE_TAG}。否则，请继续讨论。"
        
        # 构建系统提示
        system_prompt = self._build_prompt_with_notepad(MUSE_SYSTEM_PROMPT)
        
        # 执行AI调用
        parsed_response = await self._execute_ai_turn(
            sender=MessageSender.MUSE,
            prompt=muse_prompt,
            system_prompt=system_prompt,
            purpose=MessagePurpose.MUSE_TO_COGNITO,
            step_identifier=f"muse-response-turn-{self.current_turn}"
        )
        
        if not parsed_response:
            return False
        
        # 更新讨论日志
        self.discussion_log.append(f"{MessageSender.MUSE.value}: {parsed_response.spoken_text}")
        
        return True
    
    async def _cognito_response_turn(self, user_input: str, previous_ai_signaled_stop: bool) -> bool:
        """Cognito回应Muse的轮次"""
        self.ui.show_system_message(f"🧠 {MessageSender.COGNITO.value} 正在回应 {MessageSender.MUSE.value}...")
        
        # 获取最后一条Muse消息
        last_muse_text = self._get_last_spoken_text(MessageSender.MUSE)
        
        # 构建Cognito的提示
        cognito_prompt = f"""用户的查询是: "{user_input}"

当前讨论 (均为中文):
{chr(10).join(self.discussion_log)}

{MessageSender.MUSE.value} (创意AI) 刚刚说: "{last_muse_text}"

请回复 {MessageSender.MUSE.value}。继续讨论。保持您的回复简洁并使用中文。"""
        
        # 如果前一个AI建议结束讨论，添加相关指令
        if previous_ai_signaled_stop:
            cognito_prompt += f"\n\n{MessageSender.MUSE.value} 已包含 {DISCUSSION_COMPLETE_TAG} 建议结束讨论。如果您同意，请在您的回复中也包含 {DISCUSSION_COMPLETE_TAG}。否则，请继续讨论。"
        
        # 构建系统提示
        system_prompt = self._build_prompt_with_notepad(COGNITO_SYSTEM_PROMPT)
        
        # 执行AI调用
        parsed_response = await self._execute_ai_turn(
            sender=MessageSender.COGNITO,
            prompt=cognito_prompt,
            system_prompt=system_prompt,
            purpose=MessagePurpose.COGNITO_TO_MUSE,
            step_identifier=f"cognito-response-turn-{self.current_turn}"
        )
        
        if not parsed_response:
            return False
        
        # 更新讨论日志
        self.discussion_log.append(f"{MessageSender.COGNITO.value}: {parsed_response.spoken_text}")
        
        return True
    
    async def _cognito_final_answer(self, user_input: str) -> bool:
        """Cognito最终答案阶段"""
        self.ui.show_system_message("🧠 Cognito 正在综合讨论内容，准备最终答案...")
        
        # 构建最终答案提示
        final_prompt = f"""用户最初的查询是: "{user_input}"

您 ({MessageSender.COGNITO.value}) 和 {MessageSender.MUSE.value} 进行了以下讨论 (均为中文):
{chr(10).join(self.discussion_log)}

基于整个交流过程和共享记事本的最终状态，综合所有关键点，并为用户制定一个全面、有用的最终答案。

直接回复用户，而不是 {MessageSender.MUSE.value}。确保答案结构良好，易于理解，并使用中文。如果相关，您可以在答案中引用记事本。如果认为有必要，您也可以使用标准的记事本更新说明最后一次更新记事本。"""
        
        # 构建系统提示
        system_prompt = self._build_prompt_with_notepad(COGNITO_SYSTEM_PROMPT)
        
        # 执行AI调用
        parsed_response = await self._execute_ai_turn(
            sender=MessageSender.COGNITO,
            prompt=final_prompt,
            system_prompt=system_prompt,
            purpose=MessagePurpose.FINAL_RESPONSE,
            step_identifier="cognito-final-answer"
        )
        
        return parsed_response is not None
    
    async def _execute_ai_turn(
        self,
        sender: MessageSender,
        prompt: str,
        system_prompt: str,
        purpose: MessagePurpose,
        step_identifier: str
    ) -> Optional[ParsedAIResponse]:
        """
        执行单个AI回合，包含重试机制
        
        Returns:
            ParsedAIResponse: 解析后的AI响应，失败返回None
        """
        # 显示思考动画
        target_ai = MessageSender.MUSE if sender == MessageSender.COGNITO else MessageSender.COGNITO
        if purpose != MessagePurpose.FINAL_RESPONSE:
            status = self.ui.show_ai_thinking(sender, target_ai)
        else:
            status = self.ui.show_ai_thinking(sender)
        
        try:
            # 重试循环
            for attempt in range(MAX_AUTO_RETRIES + 1):
                try:
                    # 调用API
                    api_response = self.openai_service.generate_response(
                        prompt=prompt,
                        model=self.model_name,
                        system_instruction=system_prompt,
                        handler_type=self.handler_type
                    )
                    
                    # 检查API错误
                    if api_response.error:
                        raise Exception(api_response.error)
                    
                    # 解析响应
                    parsed_response = ResponseParser.parse_ai_response(
                        raw_response=api_response.raw_response,
                        handler_type=self.handler_type,
                        model_name=self.model_name,
                        player_name=sender.value
                    )
                    
                    # 停止思考动画
                    status.stop()
                    
                    # 显示思考过程（如果启用且存在）
                    if (self.show_thinking_to_user and 
                        parsed_response.thinking_content and 
                        parsed_response.thinking_content.strip()):
                        self.ui.show_thinking_process(sender, parsed_response.thinking_content)
                        
                        # 记录思考过程用于导出
                        self.thinking_records.append({
                            "sender": sender,
                            "thinking_content": parsed_response.thinking_content,
                            "timestamp": datetime.now(),
                            "purpose": purpose
                        })
                    
                    # 显示AI消息
                    self.ui.show_ai_message(
                        sender=sender,
                        message=parsed_response.spoken_text,
                        purpose=purpose,
                        duration_ms=api_response.duration_ms
                    )
                    
                    # 处理记事本更新
                    if parsed_response.new_notepad_content:
                        self.notepad_manager.update_content(
                            parsed_response.new_notepad_content,
                            sender
                        )
                        self.ui.show_notepad_update(
                            parsed_response.new_notepad_content,
                            sender
                        )
                    
                    # 添加消息到历史
                    message = ChatMessage(
                        id=self._generate_message_id(),
                        text=parsed_response.spoken_text,
                        sender=sender,
                        purpose=purpose,
                        timestamp=datetime.now(),
                        duration_ms=api_response.duration_ms
                    )
                    self.messages.append(message)
                    
                    return parsed_response
                    
                except Exception as e:
                    if attempt < MAX_AUTO_RETRIES:
                        status.stop()
                        self.ui.show_system_message(
                            f"[{sender.value} {step_identifier}] 调用失败，正在重试 ({attempt + 1}/{MAX_AUTO_RETRIES})... {str(e)}",
                            "重试"
                        )
                        await asyncio.sleep(RETRY_DELAY_BASE_MS * (attempt + 1) / 1000)
                        status = self.ui.show_ai_thinking(sender, target_ai if purpose != MessagePurpose.FINAL_RESPONSE else None)
                    else:
                        status.stop()
                        self.ui.show_error(
                            f"[{sender.value} {step_identifier}] 在 {MAX_AUTO_RETRIES + 1} 次尝试后失败: {str(e)}",
                            "API调用失败"
                        )
                        return None
            
        except Exception as e:
            status.stop()
            self.ui.show_error(f"执行AI回合时出现异常: {str(e)}", "严重错误")
            return None
    
    def _build_prompt_with_notepad(self, base_system_prompt: str) -> str:
        """构建包含记事本内容的系统提示"""
        current_notepad_content = self.notepad_manager.get_content()
        return base_system_prompt.replace("{notepad_content}", current_notepad_content)
    
    def _get_last_spoken_text(self, sender: MessageSender) -> str:
        """获取指定发送者的最后一条spoken_text"""
        for message in reversed(self.messages):
            if message.sender == sender:
                return message.text
        return ""
    
    def _get_last_parsed_response(self, sender: MessageSender) -> Optional[ParsedAIResponse]:
        """获取指定发送者的最后一条解析响应（需要从消息历史重构）"""
        # 这里简化处理，实际项目中可能需要保存ParsedAIResponse到历史
        # 暂时返回None，如果需要可以扩展
        return None
    
    def _generate_message_id(self) -> str:
        """生成唯一的消息ID"""
        return f"{self.session_id}_{len(self.messages)}_{int(time.time() * 1000)}"
    
    def get_session_summary(self) -> Dict[str, Any]:
        """获取会话摘要"""
        return {
            "session_id": self.session_id,
            "total_messages": len(self.messages),
            "notepad_stats": self.notepad_manager.get_update_stats(),
            "current_notepad": self.notepad_manager.get_content(),
            "discussion_turns": self.current_turn,
            "model_used": self.model_name,
            "handler_type": self.handler_type.value
        }
    
    def reset_session(self):
        """重置会话状态"""
        self.messages.clear()
        self.discussion_log.clear()
        self.thinking_records.clear()
        self.notepad_manager.reset()
        self.current_turn = 0
        self.session_id = f"session_{int(time.time())}"
        self.session_start_time = datetime.now()
        self.ui.show_system_message("会话已重置", "信息")
    
    def export_to_markdown(self, include_thinking: bool = True) -> str:
        """
        导出聊天记录为Markdown格式
        
        Args:
            include_thinking: 是否包含思考过程
            
        Returns:
            str: Markdown格式的聊天记录
        """
        md_content = []
        
        # 标题和会话信息
        md_content.append("# 🧠🎭 Dual AI Chat 会话记录")
        md_content.append("")
        
        # 会话元信息
        session_duration = datetime.now() - self.session_start_time
        session_stats = self.get_session_summary()
        
        md_content.append("## 📊 会话信息")
        md_content.append("")
        md_content.append(f"- **会话ID**: `{self.session_id}`")
        md_content.append(f"- **开始时间**: {self.session_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        md_content.append(f"- **结束时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        md_content.append(f"- **会话时长**: {str(session_duration).split('.')[0]}")
        md_content.append(f"- **消息总数**: {session_stats['total_messages']}")
        md_content.append(f"- **讨论轮数**: {session_stats['discussion_turns']}")
        md_content.append(f"- **使用模型**: {session_stats['model_used']}")
        md_content.append(f"- **处理器类型**: {session_stats['handler_type']}")
        md_content.append("")
        
        # 配置信息
        config = self.openai_service.get_current_config()
        md_content.append("## ⚙️ 配置信息")
        md_content.append("")
        md_content.append(f"- **API端点**: `{config['base_url']}`")
        md_content.append(f"- **模型**: `{config['model']}`")
        md_content.append(f"- **响应处理器**: `{config['handler_type']}`")
        md_content.append(f"- **显示思考过程**: {self.show_thinking_to_user}")
        md_content.append(f"- **发送思考给AI**: {self.send_thinking_to_ai}")
        md_content.append("")
        
        # 对话内容
        md_content.append("## 💬 对话内容")
        md_content.append("")
        
        # 按时间顺序处理消息和思考记录
        all_records = []
        
        # 添加消息记录
        for msg in self.messages:
            all_records.append({
                "type": "message",
                "timestamp": msg.timestamp,
                "data": msg
            })
        
        # 添加思考记录（如果启用）
        if include_thinking:
            for thinking in self.thinking_records:
                all_records.append({
                    "type": "thinking",
                    "timestamp": thinking["timestamp"],
                    "data": thinking
                })
        
        # 按时间排序
        all_records.sort(key=lambda x: x["timestamp"])
        
        # 生成内容
        for record in all_records:
            if record["type"] == "message":
                msg = record["data"]
                md_content.extend(self._format_message_for_export(msg))
            elif record["type"] == "thinking" and include_thinking:
                thinking = record["data"]
                md_content.extend(self._format_thinking_for_export(thinking))
        
        # 最终记事本状态
        if self.notepad_manager.has_been_updated():
            md_content.append("## 📝 最终记事本状态")
            md_content.append("")
            md_content.append("```markdown")
            md_content.append(self.notepad_manager.get_content())
            md_content.append("```")
            md_content.append("")
            
            # 记事本统计
            notepad_stats = self.notepad_manager.get_update_stats()
            md_content.append("### 记事本统计")
            md_content.append("")
            md_content.append(f"- **总更新次数**: {notepad_stats['total_updates']}")
            md_content.append(f"- **Cognito更新**: {notepad_stats['cognito_updates']} 次")
            md_content.append(f"- **Muse更新**: {notepad_stats['muse_updates']} 次")
            md_content.append(f"- **最后更新者**: {notepad_stats['last_updated_by']}")
            md_content.append(f"- **最终长度**: {notepad_stats['content_length']} 字符")
            md_content.append("")
        
        # 讨论摘要
        if self.discussion_log:
            md_content.append("## 🔄 讨论摘要")
            md_content.append("")
            for i, discussion_item in enumerate(self.discussion_log, 1):
                md_content.append(f"{i}. {discussion_item}")
            md_content.append("")
        
        # 生成时间
        md_content.append("---")
        md_content.append("")
        md_content.append(f"*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        md_content.append(f"*生成工具: Dual AI Chat v1.0*")
        
        return "\n".join(md_content)
    
    def _format_message_for_export(self, message: ChatMessage) -> List[str]:
        """格式化消息用于导出"""
        content = []
        
        # 消息头部
        timestamp = message.timestamp.strftime('%H:%M:%S')
        
        if message.sender == MessageSender.USER:
            content.append(f"### 💬 用户提问 `{timestamp}`")
            content.append("")
            content.append(f"> {message.text}")
            
        elif message.sender == MessageSender.COGNITO:
            if message.purpose == MessagePurpose.FINAL_RESPONSE:
                title = "🧠 Cognito 最终答案"
            elif message.purpose == MessagePurpose.COGNITO_TO_MUSE:
                title = "🧠 Cognito → Muse"
            else:
                title = "🧠 Cognito"
                
            content.append(f"### {title} `{timestamp}`")
            if message.duration_ms:
                content.append(f"*耗时: {message.duration_ms/1000:.1f}秒*")
            content.append("")
            content.append(message.text)
            
        elif message.sender == MessageSender.MUSE:
            content.append(f"### 🎭 Muse → Cognito `{timestamp}`")
            if message.duration_ms:
                content.append(f"*耗时: {message.duration_ms/1000:.1f}秒*")
            content.append("")
            content.append(message.text)
            
        elif message.sender == MessageSender.SYSTEM:
            content.append(f"### ℹ️ 系统消息 `{timestamp}`")
            content.append("")
            content.append(f"```")
            content.append(message.text)
            content.append(f"```")
        
        content.append("")
        return content
    
    def _format_thinking_for_export(self, thinking_record: Dict[str, Any]) -> List[str]:
        """格式化思考过程用于导出"""
        content = []
        
        timestamp = thinking_record["timestamp"].strftime('%H:%M:%S')
        sender = thinking_record["sender"]
        
        if sender == MessageSender.COGNITO:
            emoji = "💭🧠"
        else:
            emoji = "💭🎭"
            
        content.append(f"#### {emoji} {sender.value} 思考过程 `{timestamp}`")
        content.append("")
        content.append("<details>")
        content.append("<summary>点击展开思考过程</summary>")
        content.append("")
        content.append("```")
        content.append(thinking_record["thinking_content"])
        content.append("```")
        content.append("")
        content.append("</details>")
        content.append("")
        
        return content
    
    def save_markdown_export(self, filename: Optional[str] = None, include_thinking: bool = True) -> str:
        """
        保存聊天记录为Markdown文件
        
        Args:
            filename: 文件名（可选，默认自动生成）
            include_thinking: 是否包含思考过程
            
        Returns:
            str: 保存的文件路径
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"dual_ai_chat_{timestamp}.md"
        
        # 确保文件名以.md结尾
        if not filename.endswith('.md'):
            filename += '.md'
        
        md_content = self.export_to_markdown(include_thinking)
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(md_content)
            return filename
        except Exception as e:
            raise Exception(f"保存文件失败: {str(e)}")