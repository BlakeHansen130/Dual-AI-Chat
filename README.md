# 🧠🎭 Dual AI Chat

本项目基于[yeahhe365](https://github.com/yeahhe365)的[Dual-AI-Chat](https://github.com/yeahhe365/Dual-AI-Chat)项目进行修改，使用python和终端运行。本项目是一个让两个AI（Cognito和Muse）进行辩论的终端应用程序。Cognito专注逻辑分析，Muse负责创意质疑，通过深度辩论为您的问题提供全面的答案。

## ✨ 特色功能

- 🧠 **双AI辩论**: Cognito(逻辑) vs Muse(创意) 的思辨对话
- 📝 **协作记事本**: AI间共享的工作记录空间
- 💭 **思考透明**: 显示AI思考过程，但保持辩论自然性
- 🎨 **美化终端**: 使用Rich库打造的精美终端体验
- 🔌 **多API支持**: 兼容OpenAI、Ollama、Qwen等多种API
- 🛡️ **健壮设计**: 完整的错误处理和自动重试机制
- 📤 **导出功能**: 支持导出完整的Markdown格式聊天记录

## 🎯 工作原理

```
用户输入问题
    ↓
🧠 Cognito 初始分析
    ↓
🔄 AI辩论循环 (Muse ↔ Cognito)
    ↓
🧠 Cognito 最终答案
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置API

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置文件
nano .env
```

### 3. 启动程序

```bash
python main.py
```

## 📋 配置选项

### API配置 (必需)
| 参数 | 说明 | 示例 |
|------|------|------|
| `OPENAI_API_KEY` | API密钥 | `sk-xxx` 或 `EMPTY` |
| `OPENAI_BASE_URL` | API端点 | `https://api.openai.com/v1` |
| `DEFAULT_MODEL` | 模型名称 | `gpt-4-turbo` |
| `RESPONSE_HANDLER_TYPE` | 响应处理类型 | `standard` |

### 响应处理类型
| 类型 | 适用场景 | 说明 |
|------|----------|------|
| `standard` | 大多数API | 标准OpenAI格式 |
| `think_tags_in_content` | 思考标签 | 移除`<think>`标签 |
| `qwen_stream_with_thinking` | Qwen流式 | 分离思考和回答 |
| `content_with_separate_reasoning` | 独立思考字段 | JSON包含独立思考字段 |

### 思考过程配置 (可选)
| 参数 | 默认值 | 说明 |
|------|-------|------|
| `SHOW_THINKING_TO_USER` | `true` | 向用户显示思考过程 |
| `SEND_THINKING_TO_AI` | `false` | 发送思考过程给另一个AI |

### 讨论配置
| 参数 | 默认值 | 说明 |
|------|-------|------|
| 讨论轮数 | `3轮` | 可通过 `--turns` 选项调整 (1-8轮) |
| 讨论模式 | `固定轮次` | 未来可扩展AI驱动模式 |

## 🎨 使用示例

### 启动效果
```
╔═══════════════ 🚀 欢迎使用 ═══════════════╗
║              Dual AI Chat                 ║  
║        🧠 Cognito vs 🎭 Muse - AI辩论助手 ║
║                                           ║
║  🌐 API端点: http://localhost:11434/v1    ║
║  🤖 模型: qwen:7b-chat                    ║
║  ⚙️ 处理器: standard                      ║
╚═══════════════════════════════════════════╝
```

### 对话效果
```
💭 请输入您的问题: 什么是机器学习？

╔═ 💬 您的问题 ═════════════════════════════════╗
║ 什么是机器学习？                               ║
╚═══════════════════════════════════════════════╝

💭 Cognito思考: "用户询问机器学习定义，需要准确全面..."

╔═ 🧠 Cognito → 🎭 Muse (2.1s) ═══════════════╗
║ 机器学习是人工智能的重要分支...                ║
╚══════════════════════════════════════════════╝

╔═ 🎭 Muse → 🧠 Cognito (1.8s) ════════════════╗
║ 等等Cognito，你这定义太简单了！什么叫"学习"？    ║
╚═══════════════════════════════════════════════╝

📝 记事本已更新 by 🎭 Muse
```

## 🔧 命令行选项

```bash
# 基本使用
python main.py                          # 默认3轮讨论
python main.py --turns 4                # 设置4轮讨论 (1-8轮)

# 导出功能
python main.py --export                 # 自动导出聊天记录
python main.py --export-file chat.md    # 指定导出文件名
python main.py --no-thinking            # 导出时不包含思考过程

# 配置检查
python main.py --check                  # 检查配置
python main.py --config                 # 显示当前配置

# 其他选项
python main.py -e .env.local            # 使用指定环境文件
python main.py --version                # 显示版本信息
python main.py --verbose                # 启用详细输出
```

## 📤 导出功能

Dual AI Chat 支持将完整的聊天记录导出为Markdown格式，便于分享和存档。

### 导出内容
- **会话信息**: 时间、时长、消息数量、模型配置
- **完整对话**: 用户问题、AI回复、讨论过程
- **思考过程**: AI的内部思考（可选）
- **记事本状态**: 协作记事本的最终内容和统计
- **讨论摘要**: 整个辩论过程的关键点

### 使用方式
```bash
# 会话结束后自动导出
python main.py --export

# 指定导出文件名
python main.py --export-file "我的AI辩论_20241201.md"

# 不包含思考过程（文件更简洁）
python main.py --export --no-thinking
```

### 导出示例
生成的Markdown文件包含：
- 📊 会话统计和配置信息
- 💬 完整的对话内容（带时间戳）
- 💭 AI思考过程（可折叠显示）
- 📝 记事本协作历史
- 🎯 讨论轮次和最终结果

## 📁 项目结构

```
dual_ai_chat/
├── main.py                    # 程序入口
├── requirements.txt           # 依赖列表
├── .env.example              # 配置模板
├── config/                   # 配置模块
│   ├── constants.py         # 常量定义
│   └── models.py            # 数据模型
├── core/                    # 核心模块
│   ├── openai_service.py    # API服务
│   ├── response_parser.py   # 响应解析
│   ├── notepad_manager.py   # 记事本管理
│   └── chat_engine.py       # 对话引擎
└── ui/                      # 界面模块
    └── terminal_ui.py       # 终端界面
```

### 调试技巧

```bash
# 检查配置
python main.py --check

# 详细输出模式
python main.py --verbose

# 查看环境变量
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('OPENAI_BASE_URL'))"
```

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

[MIT License](./LICENSE)

## 🙏 致谢

- 感谢[yeahhe365](https://github.com/yeahhe365)的[Dual-AI-Chat](https://github.com/yeahhe365/Dual-AI-Chat)项目，以及其撰写的优秀提示词！

---

**🚀 立即开始您的AI辩论之旅！**