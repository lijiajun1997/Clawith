"""JSON文件存储模块"""
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

class JsonStorage:
    """JSON文件存储管理器"""

    def __init__(self, storage_dir: Optional[str] = None):
        if not storage_dir:
            storage_dir = Path.home() / ".clawith" / "model_call_sessions"
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_session_file_path(self, session_id: str) -> Path:
        """获取会话文件路径"""
        return self.storage_dir / f"{session_id}.json"

    def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """加载会话数据"""
        file_path = self._get_session_file_path(session_id)
        if not file_path.exists():
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            # 文件损坏时返回None
            return None

    def save_session(self, session_id: str, data: Dict[str, Any]) -> None:
        """保存会话数据"""
        file_path = self._get_session_file_path(session_id)
        data["updated_at"] = datetime.now().isoformat()
        if "created_at" not in data:
            data["created_at"] = data["updated_at"]

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise RuntimeError(f"保存会话失败: {str(e)}")

    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        file_path = self._get_session_file_path(session_id)
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def list_sessions(self) -> list[str]:
        """列出所有会话ID"""
        sessions = []
        for file in self.storage_dir.glob("*.json"):
            sessions.append(file.stem)
        return sessions

# 全局存储实例
json_storage = JsonStorage()
