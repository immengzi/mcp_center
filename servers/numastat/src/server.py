import re
import subprocess
from typing import Any, Dict, Optional

import paramiko
from mcp.server import FastMCP

from config.private.numastat.config_loader import NumastatConfig
from config.public.base_config_loader import LanguageEnum

# 初始化配置
config = NumastatConfig()

mcp = FastMCP(
    "NUMAStat Info MCP Server",
    host="0.0.0.0",
    port=config.get_config().private_config.port
)


@mcp.tool(
    name="numastat_info_tool"
    if config.get_config().public_config.language == LanguageEnum.ZH
    else "numastat_info_tool",
    description="""
    使用 numastat 命令获取远端机器或本机 NUMA 统计信息。
    参数：
        host: 可选，远程主机名称（使用public_config.toml中配置的name字段）；留空则获取本机信息。
    返回：
        dict {
            "numa_hit": int,          # NUMA命中次数
            "numa_miss": int,         # NUMA未命中次数
            "numa_foreign": int,      # 外部访问次数
            "interleave_hit": int,    # 交错命中次数
            "local_node": int,        # 本地节点访问次数
            "other_node": int,        # 其他节点访问次数
            "host": str               # 主机标识（本机为"localhost"）
        }
    """
    if config.get_config().public_config.language == LanguageEnum.ZH
    else """
    Use the numastat command to obtain NUMA statistics from a remote machine or local machine.
    Args:
        host: Optional remote host name (configured in public_config.toml); retrieves local info if omitted.
    Returns:
        dict {
            "numa_hit": int,          # NUMA hit count
            "numa_miss": int,         # NUMA miss count
            "numa_foreign": int,      # Foreign access count
            "interleave_hit": int,    # Interleave hit count
            "local_node": int,        # Local node access count
            "other_node": int,        # Other node access count
            "host": str               # Host identifier ("localhost" for local)
        }
    """
)
def numastat_info_tool(host: Optional[str] = None) -> Dict[str, Any]:
    """
    获取本地或远程主机的 NUMA 统计信息
    
    Args:
        host: 远程主机名称（public_config.toml 中的 name），None 表示本机
        
    Returns:
        包含 NUMA 统计信息的字典
    """
    cfg = config.get_config()
    is_zh = cfg.public_config.language == LanguageEnum.ZH
    
    # 本地执行
    if not host or host.strip().lower() in ("", "localhost"):
        return _execute_local_numastat(is_zh)
    
    # 远程执行
    return _execute_remote_numastat_workflow(host.strip(), cfg, is_zh)


def _execute_local_numastat(is_zh: bool) -> Dict[str, Any]:
    """执行本地 numastat 命令"""
    try:
        result = subprocess.run(
            ['numastat'],
            capture_output=True,
            text=True,
            check=True
        )
        stats = _parse_numastat_output(result.stdout)
        stats["host"] = "localhost"
        return stats
    except subprocess.CalledProcessError as e:
        msg = f"本地 numastat 执行失败: {e.stderr}" if is_zh else f"Local numastat execution failed: {e.stderr}"
        raise RuntimeError(msg) from e


def _execute_remote_numastat_workflow(
    host_name: str, cfg, is_zh: bool
) -> Dict[str, Any]:
    """远程执行工作流"""
    target_host = _find_remote_host(host_name, cfg.public_config.remote_hosts, is_zh)
    
    try:
        stats = _execute_remote_numastat(target_host, is_zh)
        stats["host"] = target_host.name
        return stats
    except Exception as e:
        msg = (
            f"远程执行失败 [{target_host.name}]: {str(e)}" if is_zh
            else f"Remote execution failed [{target_host.name}]: {str(e)}"
        )
        raise RuntimeError(msg) from e


def _find_remote_host(host_name: str, remote_hosts: list, is_zh: bool):
    """查找远程主机配置"""
    for host in remote_hosts:
        if host.name == host_name or host.host == host_name:
            return host
    
    available = ", ".join([h.name for h in remote_hosts])
    msg = (
        f"未找到远程主机: {host_name}，可用: {available}" if is_zh
        else f"Host not found: {host_name}, available: {available}"
    )
    raise ValueError(msg)


def _execute_remote_numastat(host_config, is_zh: bool) -> Dict[str, Any]:
    """在远程主机执行 numastat"""
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
        
        stdin, stdout, stderr = client.exec_command('numastat')
        stdin.close()
        
        output = stdout.read().decode('utf-8')
        err = stderr.read().decode('utf-8').strip()
        
        if err:
            raise RuntimeError(f"numastat failed: {err}")
        
        return _parse_numastat_output(output)
    except paramiko.AuthenticationException as e:
        msg = "SSH认证失败" if is_zh else "SSH auth failed"
        raise ConnectionError(msg) from e
    finally:
        client.close()


def _parse_numastat_output(output: str) -> Dict[str, int]:
    """解析 numastat 输出"""
    stats = {
        'numa_hit': 0,
        'numa_miss': 0,
        'numa_foreign': 0,
        'interleave_hit': 0,
        'local_node': 0,
        'other_node': 0
    }
    pattern = re.compile(r'^\s*(\w+)\s+(\d+)\s*', re.MULTILINE)
    matches = pattern.findall(output)
    for metric, value in matches:
        metric_key = metric.lower()
        if metric_key in stats:
            stats[metric_key] = int(value)
    return stats


if __name__ == "__main__":
    mcp.run(transport='sse')
