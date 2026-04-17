"""流式HTTP请求处理器 - 严格按照OpenAI API stream格式"""
import asyncio
import httpx
import json
import time
import logging
from typing import Dict, Any, Optional, AsyncIterator
from app.services.model_call.config import ModelConfig

logger = logging.getLogger(__name__)

class StreamingRequestHandler:
    """流式请求处理器 - 支持OpenAI兼容API的streaming格式"""

    def __init__(self, model_config: ModelConfig):
        self.model_config = model_config
        self.base_url = model_config.base_url.rstrip('/')
        self.api_key = model_config.api_key

    async def stream_chat_completion(
        self,
        request_body: Dict[str, Any],
        timeout: int = 180,
        agent_id: Optional[str] = None,
        max_retries: int = 30
    ) -> Dict[str, Any]:
        """
        流式调用chat/completions接口，支持自动重试

        Args:
            request_body: 请求体，符合OpenAI格式
            timeout: 总超时时间（秒）
            agent_id: agent ID，用于多模态处理
            max_retries: 最大重试次数

        Returns:
            包含content、finish_reason、统计信息的字典
        """
        # 确保使用流式模式
        request_body["stream"] = True

        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # 处理多模态内容
        if "messages" in request_body and agent_id:
            from app.services.model_call.multimodal_handler import MultimodalHandler
            request_body["messages"] = MultimodalHandler.process_request_messages(
                request_body["messages"], agent_id
            )

        # 重试机制
        last_error = None
        for attempt in range(max_retries):
            try:
                return await self._attempt_stream_request(
                    endpoint, request_body, headers, timeout
                )
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    retry_delay = 30 * (2 ** attempt)  # 30s, 60s, 90s
                    logger.warning(f"[流式请求] 第{attempt + 1}次尝试失败，{retry_delay}秒后重试: {str(e)[:100]}")
                    await asyncio.sleep(retry_delay)
                else:
                    break

        # 所有重试都失败
        return self._format_error_response(last_error, max_retries)

    async def _attempt_stream_request(
        self,
        endpoint: str,
        request_body: Dict[str, Any],
        headers: Dict[str, str],
        timeout: int
    ) -> Dict[str, Any]:
        """单次流式请求尝试"""
        start_time = time.time()
        first_byte_time = None
        content_buffer = []
        finish_reason = None
        chunk_count = 0
        last_data_time = time.time()
        timeout_no_data = 30  # 30秒无数据则认为超时

        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                async with client.stream("POST", endpoint, json=request_body, headers=headers) as response:
                    response.raise_for_status()

                    # 处理SSE流式响应
                    async for line in response.aiter_lines():
                        current_time = time.time()

                        # 检查30秒无数据超时
                        if current_time - last_data_time > timeout_no_data:
                            raise TimeoutError(f"{timeout_no_data}秒内无数据返回")

                        # 跳过空行和注释
                        if not line.strip() or line.startswith(":"):
                            continue

                        # 记录首次数据到达时间
                        if first_byte_time is None:
                            first_byte_time = current_time - start_time

                        # 解析OpenAI SSE格式: data: {...}
                        if line.startswith("data: "):
                            last_data_time = current_time

                            # 检查结束标记
                            if line.strip() == "data: [DONE]":
                                continue

                            try:
                                # 提取JSON部分
                                json_str = line[6:].strip()  # 去掉 "data: " 前缀
                                chunk_data = json.loads(json_str)
                                chunk_count += 1

                                # 解析OpenAI格式
                                # 提取JSON部分
                                json_str = line[6:].strip()  # 去掉 "data: " 前缀
                                chunk_data = json.loads(json_str)
                                chunk_count += 1

                                # 解析OpenAI格式
                                content, finish_reason, complete = self._parse_openai_chunk(chunk_data)

                                if content:
                                    content_buffer.append(content)

                                if complete:
                                    finish_reason = finish_reason or "unknown"
                                    break

                            except json.JSONDecodeError as e:
                                logger.warning(f"[流式请求] JSON解析失败: {json_str[:100]}")
                                continue

                    # 正常完成
                    duration = time.time() - start_time
                    return {
                        "success": True,
                        "content": "".join(content_buffer),
                        "finish_reason": finish_reason or "complete",
                        "duration": duration,
                        "first_byte_time": first_byte_time,
                        "chunk_count": chunk_count,
                        "retry_count": 0
                    }

            except httpx.HTTPStatusError as e:
                error_detail = e.response.text
                try:
                    error_json = e.response.json()
                    if "error" in error_json:
                        error_detail = error_json["error"].get("message", error_detail)
                except:
                    pass
                raise httpx.HTTPStatusError(
                    f"HTTP {e.response.status_code}: {error_detail}",
                    request=e.request,
                    response=e.response
                )

            except httpx.TimeoutException:
                raise TimeoutError(f"请求超时({timeout}秒)")

            except Exception as e:
                raise e

    def _parse_openai_chunk(self, chunk_data: Dict[str, Any]) -> tuple[str, Optional[str], bool]:
        """
        解析OpenAI流式响应的chunk

        Args:
            chunk_data: 单个流式数据块

        Returns:
            (content, finish_reason, is_complete)
        """
        try:
            # OpenAI格式: {"choices":[{"delta":{"content":"..."},"finish_reason":"stop"}]}
            if "choices" in chunk_data and len(chunk_data["choices"]) > 0:
                choice = chunk_data["choices"][0]

                # 提取delta内容
                delta = choice.get("delta", {})
                content = delta.get("content", "")

                # 提取finish_reason
                finish_reason = choice.get("finish_reason")

                # 判断是否完成
                is_complete = finish_reason is not None

                return content, finish_reason, is_complete
            else:
                return "", None, False

        except Exception as e:
            logger.warning(f"[流式请求] Chunk解析失败: {str(e)[:100]}")
            return "", None, False

    def _format_error_response(self, error: Exception, retry_count: int) -> Dict[str, Any]:
        """格式化错误响应"""
        error_type = type(error).__name__
        error_msg = str(error)

        # 分类错误类型
        error_category = "unknown"
        if isinstance(error, httpx.ConnectTimeout):
            error_category = "connection_timeout"
            suggestion = "网络连接超时，请检查base_url配置或网络连接"
        elif isinstance(error, httpx.ReadTimeout):
            error_category = "read_timeout"
            suggestion = "读取超时，模型可能正在生成较长内容"
        elif isinstance(error, httpx.HTTPStatusError):
            error_category = "http_error"
            if "401" in error_msg:
                suggestion = "API密钥错误，请检查api_key配置"
            elif "429" in error_msg:
                suggestion = "请求频率限制，请稍后重试"
            elif "500" in error_msg:
                suggestion = "服务器错误，建议重试"
            else:
                suggestion = f"HTTP错误: {error_msg[:100]}"
        elif isinstance(error, TimeoutError):
            error_category = "stream_timeout"
            suggestion = "30秒内无数据返回，可能网络不稳定或服务端问题"
        else:
            suggestion = "未知错误，请检查配置和网络"

        return {
            "success": False,
            "content": "",
            "finish_reason": "error",
            "duration": 0,
            "first_byte_time": None,
            "chunk_count": 0,
            "retry_count": retry_count,
            "error": error_msg,
            "error_type": error_type,
            "error_category": error_category,
            "suggestion": suggestion
        }


# 便利函数
async def stream_model_request(
    model_name: str,
    base_url: str,
    api_key: str,
    messages: list,
    timeout: int = 180,
    agent_id: Optional[str] = None,
    max_retries: int = 30
) -> Dict[str, Any]:
    """
    便利函数：直接发起流式请求

    Args:
        model_name: 模型名称
        base_url: API基础URL
        api_key: API密钥
        messages: 消息列表
        timeout: 超时时间
        agent_id: agent ID
        max_retries: 最大重试次数

    Returns:
        包含content、finish_reason等的结果字典
    """
    from app.services.model_call.config import ModelConfig

    model_config = ModelConfig(
        name=model_name,
        base_url=base_url,
        api_key=api_key,
        description=""
    )

    handler = StreamingRequestHandler(model_config)
    request_body = {
        "messages": messages,
        "temperature": 0.7,
        "model": model_name
    }

    return await handler.stream_chat_completion(
        request_body=request_body,
        timeout=timeout,
        agent_id=agent_id,
        max_retries=max_retries
    )