from typing import Optional, List, Dict, Any
from datetime import datetime
from config.constants import MessageSender, INITIAL_NOTEPAD_CONTENT
from config.models import ChatMessage


class NotepadManager:
    """共享记事本管理器 - 管理AI间的协作记事本"""
    
    def __init__(self, initial_content: Optional[str] = None):
        """
        初始化记事本管理器
        
        Args:
            initial_content: 初始记事本内容，默认使用常量中的内容
        """
        self.content = initial_content or INITIAL_NOTEPAD_CONTENT
        self.last_updated_by: Optional[MessageSender] = None
        self.last_updated_at: Optional[datetime] = None
        self.update_history: List[Dict[str, Any]] = []
        self.total_updates = 0
    
    def update_content(self, new_content: str, updated_by: MessageSender) -> bool:
        """
        更新记事本内容
        
        Args:
            new_content: 新的记事本内容
            updated_by: 更新者（Cognito或Muse）
            
        Returns:
            bool: 更新是否成功
        """
        if not isinstance(new_content, str):
            print(f"!! 记事本更新失败: 内容必须是字符串，实际类型: {type(new_content)}")
            return False
        
        if not isinstance(updated_by, MessageSender):
            print(f"!! 记事本更新失败: 更新者必须是MessageSender枚举，实际类型: {type(updated_by)}")
            return False
        
        # 保存更新历史
        old_content = self.content
        timestamp = datetime.now()
        
        self.update_history.append({
            "timestamp": timestamp,
            "updated_by": updated_by,
            "old_content": old_content,
            "new_content": new_content,
            "content_length": len(new_content),
            "change_type": self._detect_change_type(old_content, new_content)
        })
        
        # 更新内容
        self.content = new_content.strip()
        self.last_updated_by = updated_by
        self.last_updated_at = timestamp
        self.total_updates += 1
        
        # 记录更新日志
        change_info = self._get_change_summary(old_content, new_content)
        print(f"📝 记事本已更新 (by {updated_by.value}) - {change_info}")
        
        return True
    
    def get_content(self) -> str:
        """获取当前记事本内容"""
        return self.content
    
    def get_last_updated_by(self) -> Optional[MessageSender]:
        """获取最后更新者"""
        return self.last_updated_by
    
    def get_last_updated_at(self) -> Optional[datetime]:
        """获取最后更新时间"""
        return self.last_updated_at
    
    def reset(self, initial_content: Optional[str] = None):
        """
        重置记事本到初始状态
        
        Args:
            initial_content: 重置后的初始内容，默认使用常量
        """
        self.content = initial_content or INITIAL_NOTEPAD_CONTENT
        self.last_updated_by = None
        self.last_updated_at = None
        self.update_history.clear()
        self.total_updates = 0
        print("📝 记事本已重置到初始状态")
    
    def get_content_with_placeholder(self, placeholder_text: str) -> str:
        """
        获取用于AI提示的记事本内容（替换占位符）
        
        Args:
            placeholder_text: 要替换{notepad_content}的文本
            
        Returns:
            str: 替换后的内容
        """
        return placeholder_text.replace("{notepad_content}", self.content)
    
    def is_empty(self) -> bool:
        """检查记事本是否为空（只包含初始内容）"""
        return self.content.strip() == INITIAL_NOTEPAD_CONTENT.strip()
    
    def has_been_updated(self) -> bool:
        """检查记事本是否被AI更新过"""
        return self.total_updates > 0
    
    def get_update_stats(self) -> Dict[str, Any]:
        """获取更新统计信息"""
        cognito_updates = sum(1 for update in self.update_history 
                             if update["updated_by"] == MessageSender.COGNITO)
        muse_updates = sum(1 for update in self.update_history 
                          if update["updated_by"] == MessageSender.MUSE)
        
        return {
            "total_updates": self.total_updates,
            "cognito_updates": cognito_updates,
            "muse_updates": muse_updates,
            "content_length": len(self.content),
            "last_updated_by": self.last_updated_by.value if self.last_updated_by else None,
            "last_updated_at": self.last_updated_at.isoformat() if self.last_updated_at else None
        }
    
    def get_recent_updates(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        获取最近的更新历史
        
        Args:
            limit: 返回的更新记录数量限制
            
        Returns:
            List[Dict]: 最近的更新记录
        """
        recent_updates = self.update_history[-limit:] if self.update_history else []
        
        # 转换为可序列化的格式
        serializable_updates = []
        for update in recent_updates:
            serializable_updates.append({
                "timestamp": update["timestamp"].isoformat(),
                "updated_by": update["updated_by"].value,
                "content_length": update["content_length"],
                "change_type": update["change_type"]
            })
        
        return serializable_updates
    
    def _detect_change_type(self, old_content: str, new_content: str) -> str:
        """检测内容变更类型"""
        if len(new_content) > len(old_content) * 1.5:
            return "大幅扩展"
        elif len(new_content) > len(old_content):
            return "内容增加"
        elif len(new_content) < len(old_content) * 0.7:
            return "大幅精简"
        elif len(new_content) < len(old_content):
            return "内容精简"
        else:
            return "内容修改"
    
    def _get_change_summary(self, old_content: str, new_content: str) -> str:
        """生成变更摘要"""
        old_len = len(old_content)
        new_len = len(new_content)
        
        if new_len > old_len:
            return f"内容增加 ({old_len} → {new_len} 字符)"
        elif new_len < old_len:
            return f"内容精简 ({old_len} → {new_len} 字符)"
        else:
            return f"内容修改 ({new_len} 字符)"
    
    def __str__(self) -> str:
        """返回记事本的字符串表示"""
        update_info = f"(更新{self.total_updates}次)" if self.total_updates > 0 else "(未更新)"
        return f"记事本 {update_info}: {self.content[:50]}..."