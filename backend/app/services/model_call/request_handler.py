"""OpenAI API请求处理模块"""
import httpx
from typing import Dict, Any, Optional
import json

from app.services.model_call.config import ModelConfig
from app.services.model_call.multimodal_handler import MultimodalHandler
from app.services.model_call.error_handler import with_retry, CallTimeoutError, CallFailedError

class RequestHandler:
    """OpenAI API请求处理器"""

    def __init__(self, model_config: ModelConfig):
        self.model_config = model_config
        self.client = httpx.AsyncClient(
            base_url=self.model_config.base_url,
            headers={
                "Authorization": f"Bearer {self.model_config.api_key}",
                "Content-Type": "application/json"
            }
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    @with_retry(max_retries=1, retry_delay=1.0)
    async def chat_completions(self, request_body: Dict[str, Any], timeout: int = 180, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """调用chat/completions接口"""
        # 处理多模态内容
        if "messages" in request_body:
            request_body["messages"] = MultimodalHandler.process_request_messages(request_body["messages"], agent_id)

        # 确保模型名称正确
        request_body["model"] = self.model_config.name

        try:
            response = await self.client.post(
                "/chat/completions",
                json=request_body,
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text
            try:
                error_json = e.response.json()
                if "error" in error_json:
                    error_detail = error_json["error"].get("message", error_detail)
            except:
                pass
            raise CallFailedError(error_detail, {"status_code": e.response.status_code})
        except httpx.TimeoutException:
            raise CallTimeoutError(timeout)
        except Exception as e:
            raise CallFailedError(str(e))

    async def call_model(self, endpoint: str, request_body: Dict[str, Any], timeout: int = 180) -> Dict[str, Any]:
        """通用模型调用接口"""
        if endpoint == "chat/completions":
            return await self.chat_completions(request_body, timeout)
        else:
            # 其他OpenAI兼容接口直接透传
            if "messages" in request_body:
                request_body["messages"] = MultimodalHandler.process_request_messages(request_body["messages"])

            try:
                response = await self.client.post(
                    endpoint if endpoint.startswith("/") else f"/{endpoint}",
                    json=request_body,
                    timeout=timeout
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                raise RuntimeError(f"模型调用失败: {str(e)}")
