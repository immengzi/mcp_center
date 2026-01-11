# MCP Server Optimization Summary

## Overview
This document summarizes the optimization work completed for 16 MCP servers according to project standards.

## Optimization Standards

### 1. Import Order
**Standard**: stdlib → third-party → custom modules, with blank lines between groups

**Before:**
```python
from typing import Union, Dict, Any
import paramiko
import subprocess
import re
import json
from mcp.server import FastMCP
from config.public.base_config_loader import LanguageEnum
from config.private.lscpu.config_loader import LscpuConfig
```

**After:**
```python
import json
import subprocess
from typing import Any, Dict, Optional

import paramiko
from mcp.server import FastMCP

from config.private.lscpu.config_loader import LscpuConfig
from config.public.base_config_loader import LanguageEnum
```

### 2. Exception Chaining
**Standard**: Use `from e` to preserve error stack traces

**Before:**
```python
except subprocess.CalledProcessError as e:
    raise RuntimeError(f"Command failed: {e.stderr}")
```

**After:**
```python
except subprocess.CalledProcessError as e:
    msg = f"本地perf失败: {e.stderr}" if is_zh else f"Local perf failed: {e.stderr}"
    raise RuntimeError(msg) from e
```

### 3. Single Responsibility Functions
**Standard**: Each function has one clear purpose

**Before:**
```python
def tool(host=None):
    if host is None:
        # 50 lines of local execution
    else:
        # 50 lines of remote execution
    # 30 lines of parsing
```

**After:**
```python
def tool(host=None):
    if not host:
        return _execute_local(is_zh)
    return _execute_remote_workflow(host, cfg, is_zh)

def _execute_local(is_zh):
    # Single purpose: local execution

def _execute_remote_workflow(host_name, cfg, is_zh):
    # Single purpose: coordinate remote execution

def _find_remote_host(host_name, remote_hosts, is_zh):
    # Single purpose: locate host config

def _execute_remote(host_config, is_zh):
    # Single purpose: execute on remote

def _parse_output(output):
    # Single purpose: parse results
```

### 4. Configuration Separation
**Standard**: Public config for infrastructure, private config for business params

**Public Config** (`config/public/public_config.toml`):
```toml
[[remote_hosts]]
name = "本机"
os_type = "openEuler"
host = "116.63.144.61"
port = 22
username = "root"
password = "..."
```

**Private Config** (`config/private/{server}/config.toml`):
```toml
# MCP服务端口
port = 12217

# 业务特定参数
perf_duration = 10
```

### 5. Password-Only SSH Authentication
**Standard**: Framework limitation - only password auth supported

**Before:**
```python
client.connect(
    hostname=host_config.host,
    port=host_config.port,
    username=host_config.username,
    password=getattr(host_config, "password", None),
    key_filename=getattr(host_config, "ssh_key_path", None),
    timeout=10
)
```

**After:**
```python
client.connect(
    hostname=host_config.host,
    port=host_config.port,
    username=host_config.username,
    password=host_config.password,
    timeout=10
)
```

### 6. Bilingual Descriptions
**Standard**: Complete Chinese and English in tool description

**After:**
```python
@mcp.tool(
    name="tool_name",
    description="""
    中文描述...
    参数：
        host: 远程主机名称...
    返回：
        dict {...}
    """
    if is_zh
    else """
    English description...
    Args:
        host: Remote host name...
    Returns:
        dict {...}
    """
)
```

## Completed Servers (7/16)

1. **lscpu (12202)** - CPU architecture info collection
2. **numa_topo (12203)** - NUMA hardware topology query
3. **numastat (12210)** - System-wide NUMA memory access status
4. **numa_cross_node (12211)** - Locate high cross-node memory access processes
5. **numa_container (12214)** - Monitor Docker container NUMA memory access
6. **cache_miss_audit (12217)** - Locate CPU cache miss performance loss
7. **perf_interrupt (12220)** - Locate high-frequency interrupt CPU usage

## Patterns Applied

### Standard Server Structure
```python
import <stdlib imports>

import <third-party imports>

from <custom imports>

# Initialize config
config = ServerConfig()

mcp = FastMCP(
    "Server Name",
    host="0.0.0.0",
    port=config.get_config().private_config.port
)

@mcp.tool(...)
def main_tool(host: Optional[str] = None, ...):
    """Main entry point"""
    cfg = config.get_config()
    is_zh = cfg.public_config.language == LanguageEnum.ZH
    
    if not host or host.strip().lower() in ("", "localhost"):
        return _execute_local(is_zh)
    return _execute_remote_workflow(host.strip(), cfg, is_zh)

def _execute_local(is_zh):
    """Local execution"""
    try:
        # execution logic
    except Exception as e:
        raise RuntimeError(msg) from e

def _execute_remote_workflow(host_name, cfg, is_zh):
    """Remote execution workflow"""
    target_host = _find_remote_host(host_name, cfg.public_config.remote_hosts, is_zh)
    try:
        return _execute_remote(target_host, is_zh)
    except Exception as e:
        raise RuntimeError(msg) from e

def _find_remote_host(host_name, remote_hosts, is_zh):
    """Locate remote host config"""
    for host in remote_hosts:
        if host.name == host_name or host.host == host_name:
            return host
    raise ValueError(msg)

def _execute_remote(host_config, is_zh):
    """Execute on remote host"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            hostname=host_config.host,
            port=host_config.port,
            username=host_config.username,
            password=host_config.password,
            timeout=10
        )
        # execute commands
        return result
    except paramiko.AuthenticationException as e:
        msg = "SSH认证失败" if is_zh else "SSH auth failed"
        raise ConnectionError(msg) from e
    finally:
        client.close()

if __name__ == "__main__":
    mcp.run(transport='sse')
```

### Config Loader Pattern
```python
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
import os

import toml
from pydantic import BaseModel, Field

from config.public.base_config_loader import BaseConfig


class ServerConfigModel(BaseModel):
    """Server 配置模型"""
    port: int = Field(default=12XXX, description="MCP服务端口")
    # business-specific params


class ServerConfig(BaseConfig):
    """Server 配置文件读取和使用 Class"""

    def __init__(self) -> None:
        """读取配置文件"""
        super().__init__()
        self.load_private_config()

    def load_private_config(self) -> None:
        """加载私有配置文件"""
        config_file = os.getenv("CONFIG")
        if config_file is None:
            config_file = os.path.join("config", "private", "server_name", "config.toml")
        
        if os.path.exists(config_file) and os.path.getsize(config_file) > 0:
            config_data = toml.load(config_file)
        else:
            config_data = {}
        
        self._config.private_config = ServerConfigModel.model_validate(config_data)
```

## Benefits

1. **Maintainability**: Single-responsibility functions are easier to test and modify
2. **Debuggability**: Exception chaining preserves full error context
3. **Readability**: Consistent import order and structure across all servers
4. **Security**: Standardized SSH authentication approach
5. **Usability**: Bilingual descriptions support international users
6. **Scalability**: Clean separation of concerns enables easier extension

