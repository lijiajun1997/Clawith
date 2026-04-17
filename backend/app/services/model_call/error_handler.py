"""错误处理模块"""
from typing import Dict, Any
from functools import wraps
import asyncio
import httpx

class ModelCallError(Exception):
    """多模型调用通用异常"""
    def __init__(self, error_code: str, message: str, details: Dict[str, Any] = None):
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        super().__init__(message)

class ModelNotFoundError(ModelCallError):
    """模型不存在异常"""
    def __init__(self, model_name: str):
        super().__init__(
            error_code="MODEL_NOT_FOUND",
            message=f"模型不存在: {model_name}",
            details={"model_name": model_name}
        )

class InvalidParameterError(ModelCallError):
    """参数错误异常"""
    def __init__(self, message: str, param_name: str = None):
        super().__init__(
            error_code="INVALID_PARAMETER",
            message=message,
            details={"param_name": param_name} if param_name else {}
        )

class FileNotFoundError(ModelCallError):
    """文件不存在异常"""
    def __init__(self, file_path: str):
        super().__init__(
            error_code="FILE_NOT_FOUND",
            message=f"文件不存在: {file_path}",
            details={"file_path": file_path}
        )

class FileTypeNotSupportedError(ModelCallError):
    """文件类型不支持异常"""
    def __init__(self, file_type: str, allowed_types: list):
        super().__init__(
            error_code="FILE_TYPE_NOT_SUPPORTED",
            message=f"不支持的文件类型: {file_type}，允许的类型: {', '.join(allowed_types)}",
            details={"file_type": file_type, "allowed_types": allowed_types}
        )

class CallTimeoutError(ModelCallError):
    """调用超时异常"""
    def __init__(self, timeout: int):
        super().__init__(
            error_code="CALL_TIMEOUT",
            message=f"模型调用超时，超时时间: {timeout}秒",
            details={"timeout": timeout}
        )

class CallFailedError(ModelCallError):
    """调用失败异常"""
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(
            error_code="CALL_FAILED",
            message=f"模型调用失败: {message}",
            details=details or {}
        )

def with_retry(max_retries: int = 1, retry_delay: float = 1.0):
    """重试装饰器，默认重试1次"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except (httpx.TimeoutException, CallTimeoutError, httpx.NetworkError) as e:
                    last_exception = e
                    if attempt < max_retries:
                        await asyncio.sleep(retry_delay)
                        continue
                    raise
                except Exception as e:
                    # 其他异常不重试
                    raise
            raise last_exception
        return wrapper
    return decorator
