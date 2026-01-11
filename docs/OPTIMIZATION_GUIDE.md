# MCP Server Code Optimization Guide

## Overview

This comprehensive guide provides everything needed to optimize MCP servers according to project standards. It includes patterns, examples, checklists, and best practices.

## Table of Contents

1. [Optimization Standards](#optimization-standards)
2. [Common Patterns](#common-patterns)
3. [Step-by-Step Guide](#step-by-step-guide)
4. [Examples](#examples)
5. [Testing](#testing)
6. [Checklist](#checklist)

## Optimization Standards

### 1. Import Order

**Standard**: stdlib → third-party → custom, with blank lines between groups

```python
# Standard library
import os
import re
import subprocess
from typing import Any, Dict, Optional

# Third-party
import paramiko
from mcp.server import FastMCP

# Custom
from config.private.server_name.config_loader import ServerNameConfig
from config.public.base_config_loader import LanguageEnum
```

### 2. Exception Chaining

**Standard**: Always use `from e` to preserve stack traces

```python
try:
    result = subprocess.run(cmd, check=True)
except subprocess.CalledProcessError as e:
    msg = "执行失败" if is_zh else "Execution failed"
    raise RuntimeError(msg) from e
```

### 3. Single Responsibility

**Standard**: Each function has one clear purpose

```python
def tool(host: Optional[str] = None):
    """Main entry - delegates to helpers"""
    cfg = config.get_config()
    is_zh = cfg.public_config.language == LanguageEnum.ZH
    
    if not host:
        return _execute_local(is_zh)
    return _execute_remote_workflow(host.strip(), cfg, is_zh)

def _execute_local(is_zh: bool):
    """Single purpose: local execution"""

def _execute_remote_workflow(host_name: str, cfg, is_zh: bool):
    """Single purpose: coordinate remote execution"""

def _find_remote_host(host_name: str, remote_hosts: list, is_zh: bool):
    """Single purpose: locate host config"""

def _execute_remote(host_config, is_zh: bool):
    """Single purpose: remote execution"""

def _parse_output(output: str):
    """Single purpose: parse results"""
```

### 4. Config Separation

**Public** (`config/public/public_config.toml`): Infrastructure
```toml
[[remote_hosts]]
name = "本机"
host = "116.63.144.61"
port = 22
username = "root"
password = "..."
```

**Private** (`config/private/server/config.toml`): Business params
```toml
port = 12XXX
business_param = value
```

### 5. SSH Authentication

**Standard**: Password only (no key files)

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

## Common Patterns

### Pattern 1: Main Tool Function

```python
@mcp.tool(...)
def tool_name(host: Optional[str] = None, ...):
    cfg = config.get_config()
    is_zh = cfg.public_config.language == LanguageEnum.ZH
    
    # Local execution
    if not host or host.strip().lower() in ("", "localhost"):
        return _execute_local(..., is_zh)
    
    # Remote execution
    return _execute_remote_workflow(host.strip(), ..., cfg, is_zh)
```

### Pattern 2: Find Remote Host

```python
def _find_remote_host(host_name: str, remote_hosts: list, is_zh: bool):
    for host in remote_hosts:
        if host.name == host_name or host.host == host_name:
            return host
    
    available = ", ".join([h.name for h in remote_hosts])
    msg = (
        f"未找到远程主机: {host_name}，可用: {available}" if is_zh
        else f"Host not found: {host_name}, available: {available}"
    )
    raise ValueError(msg)
```

### Pattern 3: Remote Execution

```python
def _execute_remote(host_config, is_zh: bool):
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
        
        stdin, stdout, stderr = client.exec_command(cmd)
        stdin.close()
        
        output = stdout.read().decode('utf-8')
        err = stderr.read().decode('utf-8').strip()
        
        if err:
            raise RuntimeError(f"Command failed: {err}")
        
        return output
    except paramiko.AuthenticationException as e:
        msg = "SSH认证失败" if is_zh else "SSH auth failed"
        raise ConnectionError(msg) from e
    finally:
        client.close()
```

### Pattern 4: Config Loader

```python
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
import os

import toml
from pydantic import BaseModel, Field

from config.public.base_config_loader import BaseConfig


class ServerConfigModel(BaseModel):
    """Server 配置模型"""
    port: int = Field(default=12XXX, description="MCP服务端口")


class ServerConfig(BaseConfig):
    """Server 配置文件读取和使用 Class"""

    def __init__(self) -> None:
        super().__init__()
        self.load_private_config()

    def load_private_config(self) -> None:
        config_file = os.getenv("CONFIG")
        if config_file is None:
            config_file = os.path.join("config", "private", "server", "config.toml")
        
        if os.path.exists(config_file) and os.path.getsize(config_file) > 0:
            config_data = toml.load(config_file)
        else:
            config_data = {}
        
        self._config.private_config = ServerConfigModel.model_validate(config_data)
```

## Step-by-Step Guide

### Step 1: Analyze Current Implementation
1. Read existing code
2. Identify main functionality
3. Note special parameters
4. Check port number

### Step 2: Fix Import Order
1. Group imports (stdlib, third-party, custom)
2. Sort alphabetically within groups
3. Add blank lines between groups

### Step 3: Decompose Functions
1. Extract local execution
2. Extract remote workflow coordination
3. Extract host lookup
4. Extract remote execution
5. Extract parsing

### Step 4: Add Exception Chaining
1. Find all `except` blocks
2. Add `from e` to `raise` statements
3. Add bilingual messages

### Step 5: Update Tool Description
1. Add Chinese description
2. Add English description
3. Include all parameters and return values

### Step 6: Fix SSH Authentication
1. Remove `key_filename` references
2. Remove `getattr()` for password
3. Use direct `password=host_config.password`

### Step 7: Update Configs
1. Update config_loader.py
2. Update config.toml
3. Set correct port numbers

### Step 8: Test
1. Syntax check
2. Import check
3. Manual testing

## Examples

### Simple Server: numastat

See `servers/numastat/src/server.py` for a straightforward example.

**Key Points**:
- Simple command execution
- Standard parsing
- All optimization standards applied

### Server with Config Params: cache_miss_audit

See `servers/cache_miss_audit/src/server.py` for a server with business parameters.

**Key Points**:
- Private config includes `perf_duration`
- Configurable behavior
- Same standards applied

### Complex Server: numa_cross_node

See `servers/numa_cross_node/src/server.py` for a more complex example.

**Key Points**:
- Multiple parsing stages
- Complex remote execution
- Many helper functions

## Testing

### Syntax Validation
```bash
python3 -m py_compile servers/server_name/src/server.py
```

### Import Validation
```bash
python3 -c "from servers.server_name.src import server"
```

### Config Loading
```bash
python3 -c "from config.private.server_name.config_loader import ServerConfig; ServerConfig()"
```

## Checklist

Before considering a server complete:

- [ ] Import order correct (stdlib → third-party → custom)
- [ ] Config initialized at module level
- [ ] Main function extracts cfg and is_zh
- [ ] Local/remote execution separated
- [ ] Helper functions created
- [ ] All exceptions use `from e`
- [ ] SSH uses password only
- [ ] Bilingual descriptions complete
- [ ] Config loader correct
- [ ] Config.toml correct
- [ ] Syntax validates
- [ ] Imports work

## Benefits

1. **Maintainability**: Easier to modify
2. **Debuggability**: Full error context
3. **Readability**: Consistent structure
4. **Testability**: Easier to test
5. **Security**: Standardized auth
6. **Usability**: Bilingual support
7. **Scalability**: Clear patterns

