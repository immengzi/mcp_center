# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""配置文件处理模块"""

import os
from copy import deepcopy
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Any
from enum import Enum
import toml
import os


class LanguageEnum(str, Enum):
    """语言枚举"""
    ZH = "zh"
    EN = "en"


class RemoteConfigModel(BaseModel):
    """远程配置模型"""
    name: str = Field(..., description="远程主机名称")
    os_type: str = Field(..., description="远程主机操作系统类型")
    host: str = Field(..., description="远程主机地址")
    port: int = Field(..., description="远程主机端口")
    username: str = Field(..., description="远程主机用户名")
    password: str = Field(..., description="远程主机密码")


class PublicConfigModel(BaseModel):
    """公共配置模型"""
    language: LanguageEnum = Field(default=LanguageEnum.ZH, description="语言")
    remote_hosts: list[RemoteConfigModel] = Field(default=[], description="远程主机列表")


class ConfigModel(BaseModel):
    """公共配置模型"""
    public_config: PublicConfigModel = Field(default=PublicConfigModel(), description="公共配置")
    private_config: Any = Field(default=None, description="私有配置")


class BaseConfig():
    """配置文件读取和使用Class"""

    def __init__(self) -> None:
        """读取配置文件；当PROD环境变量设置时，配置文件将在读取后删除"""
        config_file = os.getenv("CONFIG")
        if config_file is None:
            config_file = os.path.join("config", "public", "public_config.toml")
        self._config = ConfigModel()
        self._config.public_config = PublicConfigModel.model_validate(toml.load(config_file))

    def load_private_config(self) -> None:
        """加载私有配置文件"""
        pass

    def get_config(self) -> ConfigModel:
        """获取配置文件内容"""
        return deepcopy(self._config)
