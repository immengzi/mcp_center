# Remaining Server Optimization Work

## Status: 7/16 Completed (43.75%)

### Completed Servers ✅
1. lscpu (12202) - CPU architecture info collection
2. numa_topo (12203) - NUMA hardware topology query  
3. numastat (12210) - System-wide NUMA memory access status
4. numa_cross_node (12211) - Locate high cross-node memory access processes
5. numa_container (12214) - Monitor Docker container NUMA memory access
6. cache_miss_audit (12217) - Locate CPU cache miss performance loss
7. perf_interrupt (12220) - Locate high-frequency interrupt CPU usage

### Remaining Servers (9 servers)
1. numa_bind_proc (12204) - Bind process to NUMA node at startup
2. numa_rebind_proc (12205) - Modify NUMA binding of running process
3. numa_bind_docker (12206) - Configure NUMA binding for Docker containers
4. numa_perf_compare (12208) - Use NUMA binding to control test variables
5. numa_diagnose (12209) - Use NUMA binding to locate hardware issues
6. hotspot_trace (12216) - Quickly locate system/process CPU performance bottlenecks
7. func_timing_trace (12218) - Precisely measure function execution time (with call stack)
8. strace_syscall (12219) - Troubleshoot unreasonable system calls (high frequency/time-consuming)
9. flame_graph (12222) - Flame graph generation: visualize performance bottlenecks

## Optimization Checklist for Each Server

For each remaining server, apply the following:

### 1. server.py
- [ ] Fix import order: stdlib → third-party → custom modules (with blank lines between groups)
- [ ] Initialize config at module level: `config = ServerConfig()`
- [ ] Use config instance in mcp initialization
- [ ] Refactor main tool function:
  - [ ] Extract `cfg = config.get_config()`
  - [ ] Extract `is_zh = cfg.public_config.language == LanguageEnum.ZH`
  - [ ] Split local/remote execution into separate functions
- [ ] Create helper functions with single responsibility:
  - [ ] `_execute_local()` - Local execution logic
  - [ ] `_execute_remote_workflow()` - Remote coordination
  - [ ] `_find_remote_host()` - Locate host config
  - [ ] `_execute_remote()` - Remote execution
  - [ ] `_parse_*()` - Parsing functions
- [ ] Add exception chaining (`from e`) to all exception handling
- [ ] Remove SSH key authentication, use password-only
- [ ] Ensure bilingual descriptions in @mcp.tool decorator

### 2. config_loader.py
- [ ] Fix import order
- [ ] Update class name to match pattern: `{ServerName}ConfigModel`
- [ ] Set correct port number in Field default
- [ ] Add empty file check in `load_private_config()`
- [ ] Use consistent error handling

### 3. config.toml
- [ ] Add header comment explaining this is private config
- [ ] Add comment directing to public_config.toml for remote hosts
- [ ] Set correct port number
- [ ] Add business-specific parameters if needed

## Key Patterns to Follow

### Import Order Template
```python
import os
import re
import subprocess
from typing import Any, Dict, Optional

import paramiko
from mcp.server import FastMCP

from config.private.{server_name}.config_loader import {ServerName}Config
from config.public.base_config_loader import LanguageEnum
```

### Exception Chaining Template
```python
try:
    # operation
except SpecificException as e:
    msg = "中文错误" if is_zh else "English error"
    raise RuntimeError(msg) from e
```

### SSH Connection Template
```python
client.connect(
    hostname=host_config.host,
    port=host_config.port,
    username=host_config.username,
    password=host_config.password,
    timeout=10
)
```

### Tool Description Template
```python
@mcp.tool(
    name="tool_name"
    if config.get_config().public_config.language == LanguageEnum.ZH
    else "tool_name",
    description="""
    中文功能描述。
    参数：
        param1: 参数描述
        host: 可选，远程主机名称（使用public_config.toml中配置的name字段）；留空则本机执行。
    返回：
        dict {
            "field1": type,  # 字段说明
            "host": str      # 主机标识（本机为"localhost"）
        }
    """
    if config.get_config().public_config.language == LanguageEnum.ZH
    else """
    English function description.
    Args:
        param1: Parameter description
        host: Optional remote host name (configured in public_config.toml); executes locally if omitted.
    Returns:
        dict {
            "field1": type,  # Field description
            "host": str      # Host identifier ("localhost" for local)
        }
    """
)
```

## Completion Strategy

### Phase 1: Simple Servers (Estimated 2-3 hours)
Start with simpler servers that follow standard patterns:
- numa_bind_proc
- numa_rebind_proc  
- numa_bind_docker
- numa_perf_compare
- numa_diagnose

### Phase 2: Complex Servers (Estimated 3-4 hours)
Handle servers with more complex logic:
- hotspot_trace (uses perf record/report)
- func_timing_trace (uses perf with call graphs)
- strace_syscall (system call tracing)
- flame_graph (SVG generation pipeline)

## Testing Strategy

After optimization, test each server:
1. Syntax check: `python3 -m py_compile servers/{name}/src/server.py`
2. Config loading: Verify config files load without errors
3. Local execution: Test with `host=None`
4. Remote execution: Test with configured remote host
5. Error handling: Verify exceptions are properly chained

## Quality Checklist

Before considering a server "complete":
- [ ] All imports properly ordered
- [ ] No SSH key authentication code remaining
- [ ] All exceptions use `from e` chaining
- [ ] Functions have single clear responsibility
- [ ] Bilingual descriptions are complete
- [ ] Config files use correct port numbers
- [ ] Code follows existing pattern from completed servers

