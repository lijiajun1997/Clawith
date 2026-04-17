"""结果处理模块"""
import uuid
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

class ResultHandler:
    """结果处理器"""

    def __init__(self, output_dir: str = None, agent_id: str = None):
        self.agent_id = agent_id
        # 如果传入agent_id，保存到agent的workspace目录下
        if agent_id and output_dir is None:
            from app.config import get_settings
            settings = get_settings()
            workspace_root = Path(settings.AGENT_DATA_DIR) / str(agent_id) / "workspace"
            workspace_root.mkdir(parents=True, exist_ok=True)
            output_dir = workspace_root / "model_results"
            output_dir.mkdir(parents=True, exist_ok=True)
        elif not output_dir:
            from app.config import get_settings
            settings = get_settings()
            output_dir = Path.home() / ".clawith" / "model_call_results"

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_result_as_md(self, model_response: Dict[str, Any], model_name: str) -> str:
        """将模型返回结果保存为MD文件，返回文件相对路径（相对于workspace根目录）"""
        # 生成唯一文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_id = str(uuid.uuid4())[:8]
        file_name = f"{timestamp}_{model_name}_{file_id}.md"
        file_path = self.output_dir / file_name

        # 提取回答内容
        content = ""
        if "choices" in model_response and len(model_response["choices"]) > 0:
            choice = model_response["choices"][0]
            if "message" in choice and "content" in choice["message"]:
                content = choice["message"]["content"]
            elif "text" in choice:
                content = choice["text"]

        # 构建MD内容
        md_content = f"""# 模型调用结果
- 模型名称: {model_name}
- 调用时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- 响应ID: {model_response.get("id", "")}
- 模型版本: {model_response.get("model", "")}

## 回答内容
{content}

## 原始响应
```json
{model_response}
```
"""

        # 写入文件
        try:
            file_path.write_text(md_content, encoding="utf-8")
            # 返回相对路径：如果是agent workspace下，返回workspace/xxx.md格式
            if self.agent_id:
                try:
                    from app.config import get_settings
                    settings = get_settings()
                    # agent的workspace根目录
                    agent_workspace_root = Path(settings.AGENT_DATA_DIR) / str(self.agent_id) / "workspace"
                    abs_path = file_path.resolve()
                    # 计算相对于workspace根目录的相对路径，并加上workspace/前缀
                    rel_path = abs_path.relative_to(agent_workspace_root)
                    # 返回workspace/开头的相对路径，和agent的list_files/read_file保持一致
                    return "workspace/" + str(rel_path)
                except ValueError:
                    # 如果计算相对路径失败，返回绝对路径
                    return str(file_path.resolve())
            else:
                # 没有agent_id时返回绝对路径
                return str(file_path.resolve())
        except Exception as e:
            raise RuntimeError(f"保存结果文件失败: {str(e)}")

    def build_response(self, model_response: Dict[str, Any], model_name: str, session_id: str = None) -> Dict[str, Any]:
        """构建返回给agent的响应结构"""
        md_file_path = self.save_result_as_md(model_response, model_name)

        return {
            "success": True,
            "model": model_name,
            "session_id": session_id,
            "content": model_response.get("choices", [{}])[0].get("message", {}).get("content", ""),
            "md_file_path": md_file_path,
            "raw_response": model_response
        }

# 全局结果处理器实例
result_handler = ResultHandler()
