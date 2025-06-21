#!/usr/bin/env python3
"""
Dual AI Chat - AI辩论助手

一个让两个AI（Cognito和Muse）进行辩论的终端应用程序。
支持多种OpenAI兼容的API，包括本地模型和云服务。
"""

import asyncio
import os
import sys
import signal
from pathlib import Path
from typing import Optional

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from core.chat_engine import ChatEngine
    from config.constants import ResponseHandlerType
except ImportError as e:
    console = Console()
    console.print(f"[red]导入错误: {e}[/red]")
    console.print("[yellow]请确保所有依赖已安装: pip install -r requirements.txt[/yellow]")
    sys.exit(1)


class DualAIChatApp:
    """Dual AI Chat 应用程序主类"""
    
    def __init__(self, export_enabled: bool = False, export_filename: str = None, 
                 include_thinking: bool = True, max_turns: int = 3):
        self.console = Console()
        self.chat_engine: Optional[ChatEngine] = None
        self.shutdown_requested = False
        
        # 导出配置
        self.export_enabled = export_enabled
        self.export_filename = export_filename
        self.include_thinking = include_thinking
        self.max_turns = max_turns
    
    def setup_signal_handlers(self):
        """设置信号处理器，支持优雅退出"""
        def signal_handler(signum, frame):
            self.shutdown_requested = True
            self.console.print("\n[yellow]正在优雅退出...[/yellow]")
            if self.chat_engine:
                self.chat_engine.ui.show_system_message("收到退出信号，正在关闭...", "系统")
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def check_environment(self) -> bool:
        """检查环境配置"""
        # 检查必需的环境变量
        required_vars = ["OPENAI_API_KEY", "OPENAI_BASE_URL", "DEFAULT_MODEL"]
        missing_vars = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            self.console.print("[red]❌ 缺少必需的环境变量:[/red]")
            for var in missing_vars:
                self.console.print(f"  - {var}")
            self.console.print("\n[yellow]请检查您的 .env 文件配置[/yellow]")
            return False
        
        # 验证响应处理器类型
        handler_type = os.getenv("RESPONSE_HANDLER_TYPE", "standard")
        try:
            ResponseHandlerType(handler_type)
        except ValueError:
            self.console.print(f"[red]❌ 无效的 RESPONSE_HANDLER_TYPE: {handler_type}[/red]")
            valid_types = [t.value for t in ResponseHandlerType]
            self.console.print(f"[yellow]有效选项: {', '.join(valid_types)}[/yellow]")
            return False
        
        return True
    
    def show_startup_info(self):
        """显示启动信息"""
        startup_text = Text()
        startup_text.append("🚀 启动 ", style="bold bright_blue")
        startup_text.append("Dual AI Chat", style="bold bright_green")
        startup_text.append(" v1.0", style="dim")
        
        info_panel = Panel(
            startup_text,
            title="初始化中",
            border_style="bright_blue",
            padding=(0, 2)
        )
        self.console.print(info_panel)
        self.console.print()
    
    def show_configuration(self):
        """显示当前配置"""
        config_info = f"""🌐 API端点: {os.getenv('OPENAI_BASE_URL')}
🤖 默认模型: {os.getenv('DEFAULT_MODEL')}
⚙️ 响应处理器: {os.getenv('RESPONSE_HANDLER_TYPE', 'standard')}
💭 显示思考过程: {os.getenv('SHOW_THINKING_TO_USER', 'true')}
🔄 发送思考给AI: {os.getenv('SEND_THINKING_TO_AI', 'false')}
🎯 讨论轮数: {self.max_turns}
📝 导出功能: {'启用' if self.export_enabled else '禁用'}"""
        
        config_panel = Panel(
            config_info,
            title="📋 当前配置",
            border_style="cyan",
            padding=(0, 1)
        )
        self.console.print(config_panel)
        self.console.print()
    
    async def run(self):
        """运行主程序"""
        try:
            # 显示启动信息
            self.show_startup_info()
            
            # 检查环境
            if not self.check_environment():
                return 1
            
            # 显示配置
            self.show_configuration()
            
            # 设置信号处理
            self.setup_signal_handlers()
            
            # 初始化聊天引擎
            self.console.print("[dim]正在初始化聊天引擎...[/dim]")
            self.chat_engine = ChatEngine()
            
            # 设置讨论轮数
            self.chat_engine.max_turns = self.max_turns
            self.console.print(f"[dim]讨论轮数设置为: {self.max_turns}[/dim]")
            
            if self.shutdown_requested:
                return 0
            
            # 启动交互式会话
            await self.chat_engine.start_interactive_session()
            
            return 0
            
        except KeyboardInterrupt:
            self.console.print("\n[yellow]用户中断程序[/yellow]")
            return 0
        except Exception as e:
            self.console.print(f"[red]❌ 程序运行出错: {e}[/red]")
            return 1
        finally:
            # 导出聊天记录
            if self.export_enabled and self.chat_engine and self.chat_engine.messages:
                try:
                    self.console.print("\n[yellow]正在导出聊天记录...[/yellow]")
                    
                    saved_file = self.chat_engine.save_markdown_export(
                        filename=self.export_filename,
                        include_thinking=self.include_thinking
                    )
                    
                    self.console.print(f"[green]✅ 聊天记录已导出到: {saved_file}[/green]")
                    
                    # 显示文件大小
                    try:
                        import os
                        file_size = os.path.getsize(saved_file)
                        self.console.print(f"[dim]文件大小: {file_size} 字节[/dim]")
                    except:
                        pass
                        
                except Exception as e:
                    self.console.print(f"[red]❌ 导出失败: {e}[/red]")
            
            # 清理资源
            if self.chat_engine:
                try:
                    session_summary = self.chat_engine.get_session_summary()
                    self.console.print(f"[dim]会话结束 - 总消息数: {session_summary['total_messages']}[/dim]")
                except:
                    pass


@click.command()
@click.option('--env-file', '-e', 
              default='.env',
              help='环境变量文件路径 (默认: .env)',
              type=click.Path())
@click.option('--config', '-c',
              help='显示当前配置并退出',
              is_flag=True)
@click.option('--check', 
              help='检查环境配置并退出',
              is_flag=True)
@click.option('--export', 
              help='会话结束后自动导出Markdown文件',
              is_flag=True)
@click.option('--export-file',
              help='指定导出文件名',
              type=str)
@click.option('--no-thinking',
              help='导出时不包含思考过程',
              is_flag=True)
@click.option('--turns', '-t',
              help='设置讨论轮数 (1-8)',
              type=click.IntRange(1, 8),
              default=3)
@click.option('--version', '-v',
              help='显示版本信息',
              is_flag=True)
@click.option('--verbose',
              help='启用详细输出',
              is_flag=True)
def main(env_file: str, config: bool, check: bool, export: bool, export_file: str, 
         no_thinking: bool, turns: int, version: bool, verbose: bool):
    """
    Dual AI Chat - AI辩论助手
    
    让两个AI（Cognito和Muse）针对您的问题进行深度辩论，
    最后由Cognito提供综合的最终答案。
    
    \b
    使用示例:
        python main.py                        # 使用默认配置启动
        python main.py -e .env.local          # 使用指定的环境文件
        python main.py --turns 4              # 设置4轮讨论
        python main.py --export               # 会话结束后导出MD文件
        python main.py --export-file chat.md  # 指定导出文件名
        python main.py --no-thinking          # 导出时不包含思考过程
        python main.py --check                # 检查配置
        python main.py --config               # 显示当前配置
    
    \b
    配置文件:
        复制 .env.example 为 .env，然后修改其中的配置：
        - OPENAI_API_KEY: API密钥
        - OPENAI_BASE_URL: API端点地址
        - DEFAULT_MODEL: 模型名称
        - RESPONSE_HANDLER_TYPE: 响应处理类型
        
    \b
    导出功能:
        使用 --export 选项可在会话结束后自动导出聊天记录为Markdown格式，
        包含完整的对话内容、思考过程、记事本状态和会话统计信息。
    """
    console = Console()
    
    # 显示版本信息
    if version:
        version_text = Text()
        version_text.append("Dual AI Chat ", style="bold bright_blue")
        version_text.append("v1.0.0", style="bold bright_green")
        version_text.append("\n🧠 Cognito vs 🎭 Muse - AI辩论助手", style="italic")
        console.print(version_text)
        return
    
    # 加载环境变量
    if not Path(env_file).exists():
        console.print(f"[red]❌ 环境文件不存在: {env_file}[/red]")
        console.print("[yellow]请复制 .env.example 为 .env 并配置相关参数[/yellow]")
        return
    
    if verbose:
        console.print(f"[dim]加载环境文件: {env_file}[/dim]")
    
    load_dotenv(env_file, override=True)
    
    # 创建应用实例
    app = DualAIChatApp(
        export_enabled=export,
        export_filename=export_file,
        include_thinking=not no_thinking,
        max_turns=turns
    )
    
    # 检查配置
    if check:
        console.print("[bold]🔍 检查环境配置...[/bold]\n")
        if app.check_environment():
            console.print("[green]✅ 所有配置检查通过！[/green]")
        else:
            console.print("[red]❌ 配置检查失败[/red]")
        return
    
    # 显示配置
    if config:
        console.print("[bold]📋 当前配置信息:[/bold]\n")
        app.show_configuration()
        return
    
    # 运行主程序
    try:
        exit_code = asyncio.run(app.run())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        console.print("\n[yellow]程序被中断[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]启动失败: {e}[/red]")
        if verbose:
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


if __name__ == "__main__":
    main()