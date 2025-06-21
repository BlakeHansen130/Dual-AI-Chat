#!/usr/bin/env python3
"""
测试脚本 - 验证所有模块可以正常导入
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """测试所有模块导入"""
    print("🔍 测试模块导入...")
    
    try:
        # 测试config模块
        print("  ✓ 导入 config.constants...")
        from config.constants import MessageSender, ResponseHandlerType
        
        print("  ✓ 导入 config.models...")
        from config.models import ChatMessage, ParsedAIResponse
        
        # 测试core模块
        print("  ✓ 导入 core.response_parser...")
        from core.response_parser import ResponseParser
        
        print("  ✓ 导入 core.notepad_manager...")
        from core.notepad_manager import NotepadManager
        
        print("  ✓ 导入 ui.terminal_ui...")
        from ui.terminal_ui import TerminalUI
        
        print("  ✓ 导入 core.openai_service...")
        from core.openai_service import OpenAIService
        
        print("  ✓ 导入 core.chat_engine...")
        from core.chat_engine import ChatEngine
        
        print("\n✅ 所有模块导入成功！")
        return True
        
    except Exception as e:
        print(f"\n❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_basic_functionality():
    """测试基本功能"""
    print("\n🧪 测试基本功能...")
    
    try:
        from config.constants import MessageSender, INITIAL_NOTEPAD_CONTENT
        from core.notepad_manager import NotepadManager
        from core.response_parser import ResponseParser
        
        # 测试记事本管理器
        print("  ✓ 测试记事本管理器...")
        notepad = NotepadManager()
        assert notepad.get_content() == INITIAL_NOTEPAD_CONTENT
        
        # 测试响应解析器
        print("  ✓ 测试响应解析器...")
        test_response = {
            "choices": [
                {
                    "message": {
                        "content": "这是测试回复"
                    }
                }
            ]
        }
        
        from config.constants import ResponseHandlerType
        parsed = ResponseParser.parse_ai_response(
            test_response, 
            ResponseHandlerType.STANDARD,
            "test-model",
            "TestAI"
        )
        
        assert parsed.spoken_text == "这是测试回复"
        
        print("\n✅ 基本功能测试通过！")
        return True
        
    except Exception as e:
        print(f"\n❌ 功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Dual AI Chat - 导入测试")
    print("=" * 40)
    
    # 测试导入
    import_success = test_imports()
    
    if import_success:
        # 测试基本功能
        function_success = test_basic_functionality()
        
        if function_success:
            print("\n🎉 所有测试通过！项目可以正常运行。")
            sys.exit(0)
        else:
            print("\n⚠️ 功能测试失败，但导入正常。")
            sys.exit(1)
    else:
        print("\n❌ 导入测试失败，请检查代码。")
        sys.exit(1)