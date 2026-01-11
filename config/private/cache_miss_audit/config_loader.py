# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
import os

import toml
from pydantic import BaseModel, Field

from config.public.base_config_loader import BaseConfig


class CacheMissAuditConfigModel(BaseModel):
    """Cache Miss Audit 配置模型"""
    port: int = Field(default=12217, description="MCP服务端口")
    perf_duration: int = Field(default=10, description="perf采集时长（秒）")


class CacheMissAuditConfig(BaseConfig):
    """Cache Miss Audit 配置文件读取和使用 Class"""

    def __init__(self) -> None:
        """读取配置文件"""
        super().__init__()
        self.load_private_config()

    def load_private_config(self) -> None:
        """加载私有配置文件"""
        config_file = os.getenv("CONFIG")
        if config_file is None:
            config_file = os.path.join(
                "config", "private", "cache_miss_audit", "config.toml"
            )
        
        if os.path.exists(config_file) and os.path.getsize(config_file) > 0:
            config_data = toml.load(config_file)
        else:
            config_data = {}
        
        self._config.private_config = CacheMissAuditConfigModel.model_validate(
            config_data
        )
