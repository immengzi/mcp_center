import re
import subprocess
from typing import Any, Dict, Optional

import paramiko
from mcp.server import FastMCP

from config.private.cache_miss_audit.config_loader import CacheMissAuditConfig
from config.public.base_config_loader import LanguageEnum

# 初始化配置
config = CacheMissAuditConfig()

mcp = FastMCP(
    "Cache Miss Audit Tool MCP Server",
    host="0.0.0.0",
    port=config.get_config().private_config.port
)


@mcp.tool(
    name="cache_miss_audit_tool"
    if config.get_config().public_config.language == LanguageEnum.ZH
    else "cache_miss_audit_tool",
    description="""
    通过 `perf stat -a -e cache-misses,cycles,instructions sleep N` 采集整机的微架构指标。
    参数:
        host: 可选，远程主机名称（使用public_config.toml中配置的name字段）；留空则采集本机。
    返回：
        dict {
            "cache_misses": int,      # 缓存未命中次数
            "cycles": int,             # CPU周期数
            "instructions": int,       # 指令数
            "ipc": float,              # 每周期指令数
            "seconds": float,          # 采集时长
            "host": str                # 主机标识（本机为"localhost"）
        }
    """
    if config.get_config().public_config.language == LanguageEnum.ZH
    else """
    Collect whole-system micro-arch metrics via
    `perf stat -a -e cache-misses,cycles,instructions sleep N`.
    Args:
        host: Optional remote host name (configured in public_config.toml); 
              analyse local if omitted.
    Returns:
        dict {
            "cache_misses": int,      # Cache miss count
            "cycles": int,             # CPU cycles
            "instructions": int,       # Instruction count
            "ipc": float,              # Instructions per cycle
            "seconds": float,          # Collection duration
            "host": str                # Host identifier ("localhost" for local)
        }
    """
)
def cache_miss_audit_tool(host: Optional[str] = None) -> Dict[str, Any]:
    """
    采集并解析 perf stat 结果
    
    Args:
        host: 远程主机名称（public_config.toml 中的 name），None 表示本机
        
    Returns:
        包含性能指标的字典
    """
    cfg = config.get_config()
    duration = cfg.private_config.perf_duration
    is_zh = cfg.public_config.language == LanguageEnum.ZH
    
    cmd = [
        "perf", "stat", "-a", "-e", 
        "cache-misses,cycles,instructions", 
        "sleep", str(duration)
    ]
    
    # 本地执行
    if not host or host.strip().lower() in ("", "localhost"):
        return _execute_local_perf(cmd, duration, is_zh)
    
    # 远程执行
    return _execute_remote_perf_workflow(host.strip(), cmd, duration, cfg, is_zh)


def _execute_local_perf(cmd: list, duration: int, is_zh: bool) -> Dict[str, Any]:
    """执行本地 perf 命令"""
    try:
        completed = subprocess.run(
            cmd,
            stderr=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            text=True,
            check=True,
            timeout=duration + 5
        )
        result = _parse_perf_stat(completed.stderr, duration)
        result["host"] = "localhost"
        return result
    except subprocess.TimeoutExpired as e:
        msg = "本地perf命令执行超时" if is_zh else "Local perf timeout"
        raise RuntimeError(msg) from e
    except subprocess.CalledProcessError as e:
        msg = f"本地perf失败: {e.stderr}" if is_zh else f"Local perf failed: {e.stderr}"
        raise RuntimeError(msg) from e


def _execute_remote_perf_workflow(
    host_name: str, cmd: list, duration: int, cfg, is_zh: bool
) -> Dict[str, Any]:
    """远程执行工作流"""
    target_host = _find_remote_host(host_name, cfg.public_config.remote_hosts, is_zh)
    
    try:
        result = _execute_remote_perf(target_host, cmd, duration, is_zh)
        result["host"] = target_host.name
        return result
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


def _execute_remote_perf(host_config, cmd: list, duration: int, is_zh: bool) -> Dict[str, Any]:
    """在远程主机执行 perf"""
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
        
        perf_cmd_str = " ".join(f"'{c}'" if " " in c else c for c in cmd)
        stdin, stdout, stderr = client.exec_command(perf_cmd_str, timeout=duration + 5)
        stdin.close()
        
        exit_code = stdout.channel.recv_exit_status()
        stat_output = stderr.read().decode("utf-8", errors="ignore")
        
        if exit_code != 0:
            raise RuntimeError(f"perf failed with exit code {exit_code}")
        
        return _parse_perf_stat(stat_output, duration)
    except paramiko.AuthenticationException as e:
        msg = "SSH认证失败" if is_zh else "SSH auth failed"
        raise ConnectionError(msg) from e
    finally:
        client.close()


def _parse_perf_stat(raw: str, expected_duration: int) -> Dict[str, Any]:
    """解析 perf stat 输出"""
    pat = re.compile(r"^\s*([\d,]+)\s+(cache-misses|cycles|instructions)", re.M)
    metrics = {k: 0 for k in ("cache-misses", "cycles", "instructions")}
    
    for num, key in pat.findall(raw):
        metrics[key] = int(num.replace(",", ""))
    
    ipc_match = re.search(r"#\s*([\d.]+)\s*insn per cycle", raw)
    ipc = float(ipc_match.group(1)) if ipc_match else 0.0
    
    if ipc == 0.0 and metrics["cycles"] > 0:
        ipc = metrics["instructions"] / metrics["cycles"]
    
    sec_match = re.search(r"(\d+\.\d+)\s+seconds time elapsed", raw)
    seconds = float(sec_match.group(1)) if sec_match else float(expected_duration)
    
    return {
        "cache_misses": metrics["cache-misses"],
        "cycles": metrics["cycles"],
        "instructions": metrics["instructions"],
        "ipc": round(ipc, 4),
        "seconds": round(seconds, 3)
    }


if __name__ == "__main__":
    mcp.run(transport="sse")
