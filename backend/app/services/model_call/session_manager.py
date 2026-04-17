"""会话管理模块"""
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.services.model_call.json_storage import json_storage

class SessionManager:
    """会话管理器"""

    @classmethod
    def create_session(cls, metadata: Optional[Dict[str, Any]] = None) -> str:
        """创建新会话，返回会话ID"""
        session_id = str(uuid.uuid4())
        session_data = {
            "session_id": session_id,
            "messages": [],
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        json_storage.save_session(session_id, session_data)
        return session_id

    @classmethod
    def get_session_messages(cls, session_id: str) -> List[Dict[str, Any]]:
        """获取会话的历史消息列表"""
        session_data = json_storage.load_session(session_id)
        if not session_data:
            return []
        return session_data.get("messages", [])

    @classmethod
    def append_message(cls, session_id: str, role: str, content: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        """追加消息到会话"""
        session_data = json_storage.load_session(session_id)
        if not session_data:
            # 会话不存在时自动创建
            session_data = {
                "session_id": session_id,
                "messages": [],
                "metadata": metadata or {},
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }

        session_data["messages"].append(message)
        json_storage.save_session(session_id, session_data)

    @classmethod
    def build_context_messages(cls, session_id: Optional[str], current_messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """构建带上下文的消息列表"""
        if not session_id:
            return current_messages

        # 获取历史消息
        history_messages = cls.get_session_messages(session_id)
        # 合并历史消息和当前消息
        return history_messages + current_messages

    @classmethod
    def save_interaction(cls, session_id: str, user_messages: List[Dict[str, Any]], assistant_response: Dict[str, Any]) -> None:
        """保存完整的交互记录到会话"""
        if not session_id:
            return

        # 保存用户消息
        for msg in user_messages:
            cls.append_message(session_id, msg["role"], msg["content"])

        # 保存助理回复
        if "choices" in assistant_response and len(assistant_response["choices"]) > 0:
            choice = assistant_response["choices"][0]
            if "message" in choice:
                message = choice["message"]
                cls.append_message(session_id, message["role"], message["content"])
