import json
import subprocess
from typing import Any, Dict, Optional

import paramiko
from mcp.server import FastMCP

from config.private.lscpu.config_loader import LscpuConfig
from config.public.base_config_loader import LanguageEnum

# 初始化配置
config = LscpuConfig()

mcp = FastMCP(
    "Lscpu Info MCP Server",
    host="0.0.0.0",
    port=config.get_config().private_config.port
)

@mcp.tool(
    name="lscpu_info_tool"
    if config.get_config().public_config.language == LanguageEnum.ZH
    else "lscpu_info_tool",
    description="""
    使用 lscpu 命令获取远端机器或本机 CPU 架构等核心静态信息。
    参数：
        host: 可选，远程主机名称（使用public_config.toml中配置的name字段）；留空则获取本机信息。
    返回：
        dict {
            "architecture": str,      # 架构（如 x86_64）
            "cpus_total": int,        # 总CPU数量
            "model_name": str,        # CPU型号名称
            "cpu_max_mhz": float,     # CPU最大频率（MHz）
            "vulnerabilities": dict,  # 常见安全漏洞的缓解状态字典
            "host": str               # 主机标识（本机为"localhost"）
        }
    """
    if config.get_config().public_config.language == LanguageEnum.ZH
    else """
    Use the lscpu command to obtain static CPU architecture information from a remote machine or local machine.
    Args:
        host: Optional remote host name (configured in public_config.toml); retrieves local info if omitted.
    Returns:
        dict {
            "architecture": str,      # CPU architecture (e.g., x86_64)
            "cpus_total": int,        # Total number of CPUs
            "model_name": str,        # CPU model name
            "cpu_max_mhz": float,     # Maximum CPU frequency in MHz
            "vulnerabilities": dict,  # Vulnerability mitigation statuses
            "host": str               # Host identifier ("localhost" for local)
        }
    """
)
def lscpu_info_tool(host: Optional[str] = None) -> Dict[str, Any]:
    """
    获取本地或远程主机的 CPU 核心静态信息
    
    Args:
        host: 远程主机名称（public_config.toml 中的 name），None 表示本机
        
    Returns:
        包含 CPU 信息的字典
    """
    cfg = config.get_config()
    is_zh = cfg.public_config.language == LanguageEnum.ZH
    
    # 本地执行
    if not host or host.strip().lower() in ("", "localhost"):
        return _execute_local_lscpu(is_zh)
    
    # 远程执行
    return _execute_remote_lscpu_workflow(host.strip(), cfg, is_zh)


def _execute_local_lscpu(is_zh: bool) -> Dict[str, Any]:
    """执行本地 lscpu 命令"""
    try:
        result = subprocess.run(
            ['lscpu', '-J'],
            capture_output=True,
            text=True,
            check=True
        )
        data = json.loads(result.stdout.strip())
        info = _parse_lscpu_json(data)
        info["host"] = "localhost"
        return info
    except subprocess.CalledProcessError as e:
        msg = f"本地 lscpu 执行失败: {e.stderr}" if is_zh else f"Local lscpu execution failed: {e.stderr}"
        raise RuntimeError(msg) from e
    except json.JSONDecodeError as e:
        msg = "lscpu 输出解析失败" if is_zh else "Failed to parse lscpu output"
        raise RuntimeError(msg) from e


def _execute_remote_lscpu_workflow(
    host_name: str, cfg, is_zh: bool
) -> Dict[str, Any]:
    """远程执行工作流"""
    target_host = _find_remote_host(host_name, cfg.public_config.remote_hosts, is_zh)
    
    try:
        info = _execute_remote_lscpu(target_host, is_zh)
        info["host"] = target_host.name
        return info
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


def _execute_remote_lscpu(host_config, is_zh: bool) -> Dict[str, Any]:
    """在远程主机执行 lscpu"""
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
        
        stdin, stdout, stderr = client.exec_command('lscpu -J')
        stdin.close()
        
        output = stdout.read().decode('utf-8')
        err = stderr.read().decode('utf-8').strip()
        
        if err:
            raise RuntimeError(f"lscpu failed: {err}")
        
        data = json.loads(output.strip())
        return _parse_lscpu_json(data)
    except paramiko.AuthenticationException as e:
        msg = "SSH认证失败" if is_zh else "SSH auth failed"
        raise ConnectionError(msg) from e
    except json.JSONDecodeError as e:
        msg = "lscpu 输出解析失败" if is_zh else "Failed to parse lscpu output"
        raise RuntimeError(msg) from e
    finally:
        client.close()


def _parse_lscpu_json(data: Dict[str, Any]) -> Dict[str, Any]:
    """解析 lscpu JSON 输出"""
    info = {
        'architecture': '',
        'cpus_total': 0,
        'model_name': '',
        'cpu_max_mhz': 0.0,
        'vulnerabilities': {}
    }

    def traverse(entries):
        for item in entries:
            field_raw = item["field"].strip()
            value = item.get("data", "").strip()

            if field_raw == "Architecture:":
                info['architecture'] = value
            elif field_raw == "CPU(s):":
                try:
                    info['cpus_total'] = int(value.split()[0])
                except (ValueError, IndexError):
                    info['cpus_total'] = 0
            elif field_raw == "Model name:":
                info['model_name'] = value
            elif field_raw == "CPU max MHz:":
                try:
                    info['cpu_max_mhz'] = float(value.split()[0])
                except (ValueError, IndexError):
                    info['cpu_max_mhz'] = 0.0
            elif field_raw.startswith("Vulnerability "):
                vuln_name = field_raw[len("Vulnerability "):].strip(": ")
                normalized_key = vuln_name.lower().replace(' ', '_').replace('-', '_')
                info['vulnerabilities'][normalized_key] = value

            if "children" in item:
                traverse(item["children"])

    traverse(data.get("lscpu", []))
    return info


if __name__ == "__main__":
    mcp.run(transport='sse')