"""多模型调用工具配置模块"""
import json
from typing import List, Dict, Optional
from pydantic import BaseModel, Field

class ModelConfig(BaseModel):
    """单个模型配置"""
    name: str = Field(description="模型名称，用于agent选择调用")
    base_url: str = Field(description="模型服务的base url，兼容OpenAI API格式")
    api_key: str = Field(description="API访问密钥")
    description: str = Field(default="", description="模型描述，供agent了解模型能力")
    is_multimodal: bool = Field(default=False, description="是否支持多模态（图片识别）")
    is_network_enabled: bool = Field(default=False, description="是否支持联网搜索")

class ModelCallConfig:
    """多模型调用配置管理器"""

    def __init__(self, tool_config: dict):
        self._configs: Dict[str, ModelConfig] = {}
        self._load_configs(tool_config)

    def _load_configs(self, tool_config: dict) -> None:
        """从工具配置加载模型列表"""
        # 配置格式: {"models": [{"name":"xxx", "base_url":"xxx", "api_key":"xxx", ...}]}
        if not tool_config or "models" not in tool_config:
            return

        try:
            config_list = tool_config["models"]
            for config in config_list:
                model_config = ModelConfig(**config)
                self._configs[model_config.name] = model_config
        except Exception:
            pass

    def get_model_config(self, model_name: str) -> Optional[ModelConfig]:
        """根据模型名称获取配置"""
        return self._configs.get(model_name)
