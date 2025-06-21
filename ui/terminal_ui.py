import time
import os
from typing import Optional, Dict, Any, List
from datetime import datetime
from rich.console import Console, Group
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich.markdown import Markdown
from rich.rule import Rule
from rich.align import Align
from rich.columns import Columns
from rich.box import ROUNDED, DOUBLE, HEAVY, SIMPLE, ASCII
from rich.style import Style
from rich.prompt import Prompt
from rich.tree import Tree
from rich.status import Status
from rich.spinner import Spinner
from config.constants import MessageSender, MessagePurpose


class TerminalUI:
    """终端美化界面 - 使用Rich库的全部特性创造极致视觉体验"""
    
    def __init__(self):
        # 初始化控制台，启用所有高级特性
        self.console = Console(
            width=120,           # 更宽的显示区域
            force_terminal=True,  # 强制终端模式
            color_system="truecolor",  # 支持真彩色
            legacy_windows=False  # 禁用旧Windows兼容模式
        )
        
        # AI角色配置
        self.ai_configs = {
            MessageSender.COGNITO: {
                "emoji": "🧠",
                "color": "bright_green", 
                "style": "bold bright_green",
                "box": ROUNDED
            },
            MessageSender.MUSE: {
                "emoji": "🎭", 
                "color": "bright_magenta",
                "style": "bold bright_magenta", 
                "box": HEAVY
            },
            MessageSender.USER: {
                "emoji": "💬",
                "color": "bright_blue",
                "style": "bold bright_blue",
                "box": DOUBLE
            },
            MessageSender.SYSTEM: {
                "emoji": "ℹ️",
                "color": "yellow",
                "style": "bold yellow",
                "box": SIMPLE
            }
        }
        
        # 思考过程样式
        self.thinking_style = {
            "emoji": "💭",
            "color": "bright_black",
            "style": "italic bright_black",
            "box": ASCII
        }
        
        # 记事本样式
        self.notepad_style = {
            "emoji": "📝",
            "color": "cyan",
            "style": "bold cyan",
            "box": ROUNDED
        }
        
        # 统计数据
        self.message_count = 0
        self.session_start_time = datetime.now()
    
    def clear_screen(self):
        """清屏并重置光标"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def show_header(self, config_info: Optional[Dict] = None):
        """显示应用标题和配置信息"""
        # 创建渐变标题
        title_text = Text("Dual AI Chat", style="bold")
        title_text.stylize("bright_blue", 0, 4)  # "Dual"
        title_text.stylize("bright_green", 5, 7) # "AI" 
        title_text.stylize("bright_magenta", 8, 12) # "Chat"
        
        # 副标题
        subtitle = Text("🧠 Cognito vs 🎭 Muse - AI辩论助手", style="italic bright_cyan")
        
        # 配置信息表格
        config_table = None
        if config_info:
            config_table = Table(show_header=False, box=None, padding=(0, 1))
            config_table.add_column(style="dim")
            config_table.add_column(style="bright_white")
            
            config_table.add_row("🌐 API端点:", config_info.get("base_url", "未知"))
            config_table.add_row("🤖 模型:", config_info.get("model", "未知"))
            config_table.add_row("⚙️ 处理器:", config_info.get("handler_type", "未知"))
        
        # 组合内容
        header_content = Group(
            Align.center(title_text),
            Align.center(subtitle),
            "",
            Align.center(config_table) if config_table else Text(""),
            "",
            Align.center(Text("输入您的问题，观看两个AI进行深度讨论", style="dim italic"))
        )
        
        # 创建面板
        header_panel = Panel(
            header_content,
            title="🚀 欢迎使用",
            title_align="center",
            border_style="bright_blue",
            box=DOUBLE,
            padding=(1, 2)
        )
        
        self.console.print(header_panel)
        self.console.print()
    
    def show_user_message(self, message: str):
        """显示用户消息"""
        config = self.ai_configs[MessageSender.USER]
        
        # 创建用户消息面板
        user_panel = Panel(
            Markdown(message),
            title=f"{config['emoji']} 您的问题",
            title_align="left",
            border_style=config["color"],
            box=config["box"],
            padding=(0, 1)
        )
        
        self.console.print(user_panel)
        self.console.print()
        self.message_count += 1
    
    def show_ai_thinking(self, sender: MessageSender, target: Optional[MessageSender] = None) -> Status:
        """显示AI思考动画"""
        config = self.ai_configs[sender]
        
        if target:
            status_text = f"[{config['color']}]{config['emoji']} {sender.value}[/] 正在为 [{self.ai_configs[target]['color']}]{target.value}[/] 思考中..."
        else:
            status_text = f"[{config['color']}]{config['emoji']} {sender.value}[/] 正在思考中..."
        
        # 创建状态显示器
        status = Status(
            status_text,
            spinner="dots12",
            spinner_style=config["color"]
        )
        status.start()
        return status
    
    def show_thinking_process(self, sender: MessageSender, thinking_content: str):
        """显示思考过程"""
        config = self.ai_configs[sender]
        thinking_config = self.thinking_style
        
        # 创建思考过程面板
        thinking_panel = Panel(
            Markdown(thinking_content),
            title=f"{thinking_config['emoji']} {sender.value} 的思考过程",
            title_align="left",
            border_style=thinking_config["color"],
            box=thinking_config["box"],
            padding=(0, 1)
        )
        
        self.console.print(thinking_panel)
        self.console.print()
    
    def show_ai_message(
        self, 
        sender: MessageSender, 
        message: str, 
        purpose: MessagePurpose,
        duration_ms: Optional[float] = None
    ):
        """显示AI消息"""
        config = self.ai_configs[sender]
        
        # 构建标题
        title_parts = [f"{config['emoji']} {sender.value}"]
        
        # 添加目的说明
        if purpose == MessagePurpose.COGNITO_TO_MUSE:
            title_parts.append("→ 🎭 Muse")
        elif purpose == MessagePurpose.MUSE_TO_COGNITO:
            title_parts.append("→ 🧠 Cognito")
        elif purpose == MessagePurpose.FINAL_RESPONSE:
            title_parts.append("💫 最终答案")
        
        # 添加耗时信息
        if duration_ms:
            title_parts.append(f"({duration_ms/1000:.1f}s)")
        
        title = " ".join(title_parts)
        
        # 创建消息面板
        message_panel = Panel(
            Markdown(message),
            title=title,
            title_align="left",
            border_style=config["color"],
            box=config["box"],
            padding=(0, 1)
        )
        
        self.console.print(message_panel)
        self.console.print()
        self.message_count += 1
    
    def show_notepad_update(self, content: str, updated_by: MessageSender):
        """显示记事本更新"""
        config = self.ai_configs[updated_by]
        notepad_config = self.notepad_style
        
        # 创建更新提示
        update_text = Text()
        update_text.append("📝 记事本已更新 by ", style="bold cyan")
        update_text.append(f"{config['emoji']} {updated_by.value}", style=config["style"])
        
        self.console.print(update_text)
        
        # 显示记事本内容
        notepad_panel = Panel(
            Markdown(content),
            title=f"{notepad_config['emoji']} 共享记事本",
            title_align="center",
            border_style=notepad_config["color"],
            box=notepad_config["box"],
            padding=(1, 1)
        )
        
        self.console.print(notepad_panel)
        self.console.print()
    
    def show_discussion_progress(self, current_turn: int, total_turns: Optional[int] = None, mode: str = "fixed"):
        """显示讨论进度"""
        if mode == "fixed" and total_turns:
            # 固定轮次模式 - 显示进度条
            progress_percentage = (current_turn / total_turns) * 100
            
            progress_bar = "█" * int(progress_percentage // 10) + "░" * (10 - int(progress_percentage // 10))
            
            progress_text = Text()
            progress_text.append("🔄 讨论进度: ", style="bold")
            progress_text.append(f"[{progress_bar}] ", style="bright_blue")
            progress_text.append(f"{current_turn}/{total_turns} 轮", style="bright_white")
            
        else:
            # AI驱动模式
            progress_text = Text()
            progress_text.append("🔄 讨论进行中: ", style="bold")
            progress_text.append(f"第 {current_turn} 轮", style="bright_cyan")
            progress_text.append(" (AI 将决定何时结束)", style="dim")
        
        # 创建进度面板
        progress_panel = Panel(
            Align.center(progress_text),
            border_style="bright_yellow",
            box=SIMPLE,
            padding=(0, 1)
        )
        
        self.console.print(progress_panel)
        self.console.print()
    
    def show_discussion_end(self, reason: str = "讨论完成"):
        """显示讨论结束"""
        end_text = Text()
        end_text.append("🎯 ", style="bright_green")
        end_text.append(reason, style="bold bright_green")
        
        end_panel = Panel(
            Align.center(end_text),
            title="✨ 讨论结束",
            title_align="center", 
            border_style="bright_green",
            box=DOUBLE,
            padding=(0, 2)
        )
        
        self.console.print(end_panel)
        self.console.print()
    
    def show_error(self, error_message: str, error_type: str = "错误"):
        """显示错误信息"""
        error_panel = Panel(
            f"❌ {error_message}",
            title=f"🚨 {error_type}",
            title_align="left",
            border_style="bright_red",
            box=HEAVY,
            padding=(0, 1)
        )
        
        self.console.print(error_panel)
        self.console.print()
    
    def show_system_message(self, message: str, message_type: str = "信息"):
        """显示系统消息"""
        config = self.ai_configs[MessageSender.SYSTEM]
        
        # 根据消息类型选择样式
        if "警告" in message or "失败" in message:
            style = "bright_red"
            emoji = "⚠️"
        elif "成功" in message:
            style = "bright_green" 
            emoji = "✅"
        else:
            style = config["color"]
            emoji = config["emoji"]
        
        system_panel = Panel(
            f"{emoji} {message}",
            title=f"📢 {message_type}",
            title_align="left",
            border_style=style,
            box=config["box"],
            padding=(0, 1)
        )
        
        self.console.print(system_panel)
        self.console.print()
    
    def show_session_stats(self):
        """显示会话统计信息"""
        session_duration = datetime.now() - self.session_start_time
        
        stats_table = Table(show_header=False, box=ROUNDED, border_style="dim")
        stats_table.add_column("📊", style="bold")
        stats_table.add_column("统计", style="bright_white")
        
        stats_table.add_row("💬", f"消息总数: {self.message_count}")
        stats_table.add_row("⏱️", f"会话时长: {str(session_duration).split('.')[0]}")
        stats_table.add_row("🕒", f"开始时间: {self.session_start_time.strftime('%H:%M:%S')}")
        
        stats_panel = Panel(
            stats_table,
            title="📈 会话统计",
            title_align="center",
            border_style="bright_cyan",
            box=ROUNDED
        )
        
        self.console.print(stats_panel)
        self.console.print()
    
    def get_user_input(self, prompt_text: str = "请输入您的问题") -> str:
        """获取用户输入 - 美化版"""
        self.console.print(Rule(style="dim"))
        
        # 创建输入提示
        prompt_style = Text()
        prompt_style.append("💭 ", style="bright_blue")
        prompt_style.append(prompt_text, style="bold bright_blue")
        prompt_style.append(" (回车发送, Ctrl+C 退出)", style="dim")
        
        return Prompt.ask(prompt_style, console=self.console)
    
    def show_loading_with_progress(self, task_name: str, estimated_duration: int = 10):
        """显示带进度条的加载动画"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        ) as progress:
            task = progress.add_task(f"🔄 {task_name}...", total=estimated_duration * 10)
            
            for i in range(estimated_duration * 10):
                time.sleep(0.1)
                progress.update(task, advance=1)
    
    def create_live_layout(self) -> Layout:
        """创建实时更新的布局"""
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=8),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        
        layout["main"].split_row(
            Layout(name="chat", ratio=2),
            Layout(name="notepad", ratio=1)
        )
        
        return layout
    
    def show_typing_effect(self, text: str, delay: float = 0.03):
        """打字机效果显示文本"""
        displayed_text = Text()
        
        with Live(displayed_text, refresh_per_second=30, console=self.console) as live:
            for char in text:
                displayed_text.append(char)
                time.sleep(delay)
    
    def show_welcome_animation(self):
        """显示欢迎动画"""
        # ASCII艺术标题
        ascii_art = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║    ██████╗ ██╗   ██╗ █████╗ ██╗         █████╗ ██╗        ║
║    ██╔══██╗██║   ██║██╔══██╗██║        ██╔══██╗██║        ║
║    ██║  ██║██║   ██║███████║██║        ███████║██║        ║
║    ██║  ██║██║   ██║██╔══██║██║        ██╔══██║██║        ║
║    ██████╔╝╚██████╔╝██║  ██║███████╗   ██║  ██║██║        ║
║    ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚══════╝   ╚═╝  ╚═╝╚═╝        ║
║                                                           ║
║            ██████╗██╗  ██╗ █████╗ ████████╗               ║
║           ██╔════╝██║  ██║██╔══██╗╚══██╔══╝               ║
║           ██║     ███████║███████║   ██║                  ║
║           ██║     ██╔══██║██╔══██║   ██║                  ║
║           ╚██████╗██║  ██║██║  ██║   ██║                  ║
║            ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝                  ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
        """
        
        # 渐变显示ASCII艺术
        lines = ascii_art.strip().split('\n')
        for line in lines:
            self.console.print(Text(line, style="bright_blue"))
            time.sleep(0.1)
        
        # 欢迎文字
        welcome_text = Text("🚀 启动 AI 辩论系统...", style="bold bright_green")
        self.console.print(Align.center(welcome_text))
        time.sleep(1)
    
    def show_separator(self, style: str = "dim", char: str = "─"):
        """显示分隔线"""
        self.console.print(Rule(style=style, characters=char))
    
    def __del__(self):
        """析构函数 - 显示再见消息"""
        if hasattr(self, 'console'):
            goodbye_text = Text("👋 感谢使用 Dual AI Chat！", style="bold bright_cyan")
            self.console.print(Align.center(goodbye_text))