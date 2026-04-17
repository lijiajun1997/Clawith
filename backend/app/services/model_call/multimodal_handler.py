"""多模态内容处理模块"""
import base64
import mimetypes
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from app.config import get_settings

_settings = get_settings()
WORKSPACE_ROOT = Path(_settings.AGENT_DATA_DIR)

class MultimodalHandler:
    """多模态内容处理器"""

    ALLOWED_TEXT_EXTENSIONS = {".md", ".txt", ".markdown"}
    ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

    @classmethod
    def _resolve_path(cls, input_path: str, agent_id: Optional[str] = None, allowed_extensions: Optional[set] = None) -> Path:
        """路径容错匹配：自动尝试绝对路径、相对agent workspace路径、模糊搜索"""
        input_path = input_path.strip().strip('"\'')
        path = Path(input_path).expanduser()

        # 1. 首先尝试绝对路径
        if path.is_absolute() and path.exists():
            if allowed_extensions is None or path.suffix.lower() in allowed_extensions:
                return path

        # 2. 如果是相对路径且agent_id存在，尝试多个解析策略
        if agent_id:
            agent_workspace = WORKSPACE_ROOT / str(agent_id) / "workspace"
            if agent_workspace.exists():
                # 2a. 直接相对路径：workspace/image.png
                relative_path = agent_workspace / input_path
                if relative_path.exists() and (allowed_extensions is None or relative_path.suffix.lower() in allowed_extensions):
                    return relative_path

                # 2b. 去掉workspace前缀：image.png -> workspace/image.png
                if input_path.startswith("workspace/"):
                    # 去掉workspace前缀重新尝试
                    without_prefix = input_path[len("workspace/"):]
                    relative_path = agent_workspace / without_prefix
                    if relative_path.exists() and (allowed_extensions is None or relative_path.suffix.lower() in allowed_extensions):
                        return relative_path

                # 2c. 模糊搜索整个agent workspace下的同名文件
                filename = path.name
                matches = list(agent_workspace.rglob(f"*{filename}*"))
                if allowed_extensions:
                    matches = [p for p in matches if p.suffix.lower() in allowed_extensions]

                if len(matches) == 1:
                    return matches[0]
                elif len(matches) > 1:
                    # 优先选择完全匹配的文件
                    exact_matches = [p for p in matches if p.name == filename]
                    if len(exact_matches) == 1:
                        return exact_matches[0]

                    match_paths = "\n- ".join([str(p) for p in matches])
                    raise RuntimeError(f"找到多个匹配文件，请明确路径：\n- {match_paths}")

        # 3. 所有尝试都失败
        raise FileNotFoundError(f"文件不存在: {input_path}\n请确认路径是否正确，支持绝对路径或相对于agent workspace的相对路径")

    @classmethod
    def resolve_file_reference(cls, file_path: str, agent_id: Optional[str] = None) -> str:
        """解析文件引用，读取文本文件内容"""
        try:
            path = cls._resolve_path(file_path, agent_id, cls.ALLOWED_TEXT_EXTENSIONS)
            return path.read_text(encoding="utf-8")
        except Exception as e:
            raise RuntimeError(f"读取文件失败: {str(e)}")

    @classmethod
    def resolve_image_reference(cls, image_source: str, agent_id: Optional[str] = None) -> Dict[str, str]:
        """解析图片引用，支持本地文件路径、URL、base64格式"""
        # 去除路径周围的引号和空格
        image_source = image_source.strip().strip('"\'').strip()

        # 检查是否是base64格式
        if image_source.startswith("data:image/"):
            return {
                "type": "image_url",
                "image_url": {
                    "url": image_source
                }
            }

        # 检查是否是URL
        parsed_url = urlparse(image_source)
        if parsed_url.scheme in ("http", "https"):
            return {
                "type": "image_url",
                "image_url": {
                    "url": image_source
                }
            }

        # 本地文件路径，容错匹配
        try:
            path = cls._resolve_path(image_source, agent_id, cls.ALLOWED_IMAGE_EXTENSIONS)

            # 读取图片并转换为base64
            mime_type, _ = mimetypes.guess_type(path)
            if not mime_type:
                mime_type = f"image/{path.suffix[1:].lower()}"

            image_data = path.read_bytes()
            base64_data = base64.b64encode(image_data).decode("utf-8")
            return {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime_type};base64,{base64_data}"
                }
            }
        except FileNotFoundError:
            # 提供更友好的错误提示
            raise RuntimeError(
                f"图片文件不存在: {image_source}\n"
                f"支持的路径格式：\n"
                f"1. 绝对路径: /data/agents/xxx/workspace/image.png\n"
                f"2. 相对路径: workspace/image.png\n"
                f"3. 文件名模糊匹配: image.png\n"
                f"4. URL: http://example.com/image.png\n"
                f"5. base64: data:image/png;base64,..."
            )
        except Exception as e:
            raise RuntimeError(f"处理图片失败 [{image_source}]: {str(e)}")

    @classmethod
    def process_message_content(cls, content: Any, agent_id: Optional[str] = None) -> Any:
        """处理消息内容，自动解析文件引用和图片引用"""
        if isinstance(content, str):
            # 检查是否包含文件引用标记（格式：{{file:/path/to/file.md}}）
            if "{{file:" in content:
                import re
                file_pattern = r"{{file:([^}]+)}}"
                matches = re.findall(file_pattern, content)
                for file_path in matches:
                    file_content = cls.resolve_file_reference(file_path.strip(), agent_id)
                    content = content.replace(f"{{{{file:{file_path}}}}}", f"\n{file_content}\n")
            return content

        if isinstance(content, list):
            # 处理多模态内容数组
            processed_content = []
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "file":
                        # 文件引用类型
                        file_path = item.get("file_path", "")
                        file_content = cls.resolve_file_reference(file_path, agent_id)
                        processed_content.append({
                            "type": "text",
                            "text": file_content
                        })
                    elif item.get("type") == "image_url" or item.get("type") == "image":
                        # 图片类型
                        image_url = item.get("image_url", {}).get("url", "") or item.get("url", "")
                        processed_image = cls.resolve_image_reference(image_url, agent_id)
                        processed_content.append(processed_image)
                    else:
                        processed_content.append(item)
                else:
                    processed_content.append(item)
            return processed_content

        return content

    @classmethod
    def process_request_messages(cls, messages: List[Dict[str, Any]], agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """处理所有请求消息，解析文件和图片引用"""
        processed_messages = []
        for message in messages:
            processed_message = message.copy()
            if "content" in processed_message:
                processed_message["content"] = cls.process_message_content(processed_message["content"], agent_id)
            processed_messages.append(processed_message)
        return processed_messages
