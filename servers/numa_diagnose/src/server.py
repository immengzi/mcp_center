import re
import subprocess
from typing import Any, Dict, Optional

import paramiko
from mcp.server import FastMCP

from config.private.numa_diagnose.config_loader import NumaDiagnoseConfig
from config.public.base_config_loader import LanguageEnum

# 初始化配置
config = NumaDiagnoseConfig()

mcp = FastMCP(
    "NUMA Hardware Monitoring Server",
    host="0.0.0.0",
    port=config.get_config().private_config.port
)


@mcp.tool(
    name="numa_diagnose"
    if config.get_config().public_config.language == LanguageEnum.ZH
    else "numa_diagnose",
    description="""
    获取NUMA架构硬件监控信息。
    参数：
        host: 可选，远程主机名称（使用public_config.toml中配置的name字段）；留空则获取本机信息。
    返回：
        dict {
            "real_time_frequencies": dict,  # 各CPU核心实时频率(MHz)
            "specifications": dict,          # CPU规格信息（型号/频率范围/NUMA节点）
            "numa_topology": dict,           # NUMA拓扑结构
            "host": str                      # 主机标识（本机为"localhost"）
        }
    """
    if config.get_config().public_config.language == LanguageEnum.ZH
    else """
    Get NUMA hardware monitoring information.
    Args:
        host: Optional remote host name (configured in public_config.toml); retrieves local info if omitted.
    Returns:
        dict {
            "real_time_frequencies": dict,  # Real-time frequency of each CPU core (MHz)
            "specifications": dict,          # CPU specifications (model/frequency range/NUMA nodes)
            "numa_topology": dict,           # NUMA topology
            "host": str                      # Host identifier ("localhost" for local)
        }
    """
)
def numa_diagnose(host: Optional[str] = None) -> Dict[str, Any]:
    """
    获取NUMA硬件监控信息
    
    Args:
        host: 远程主机名称（public_config.toml 中的 name），None 表示本机
        
    Returns:
        包含硬件监控信息的字典
    """
    cfg = config.get_config()
    is_zh = cfg.public_config.language == LanguageEnum.ZH
    
    # 本地执行
    if not host or host.strip().lower() in ("", "localhost"):
        return _execute_local_diagnose(is_zh)
    
    # 远程执行
    return _execute_remote_diagnose_workflow(host.strip(), cfg, is_zh)


def _execute_local_diagnose(is_zh: bool) -> Dict[str, Any]:
    """执行本地诊断"""
    try:
        # 获取实时频率
        real_time_frequencies = _get_local_cpu_frequencies(is_zh)
        
        # 获取规格和NUMA信息
        specifications = _get_local_cpu_specifications(is_zh)
        
        return {
            "real_time_frequencies": real_time_frequencies,
            "specifications": specifications,
            "numa_topology": specifications.get("numa_nodes", {}),
            "host": "localhost"
        }
    except Exception as e:
        msg = f"本地诊断失败: {str(e)}" if is_zh else f"Local diagnosis failed: {str(e)}"
        raise RuntimeError(msg) from e


def _execute_remote_diagnose_workflow(
    host_name: str, cfg, is_zh: bool
) -> Dict[str, Any]:
    """远程执行工作流"""
    target_host = _find_remote_host(host_name, cfg.public_config.remote_hosts, is_zh)
    
    try:
        # 获取实时频率
        real_time_frequencies = _get_remote_cpu_frequencies(target_host, is_zh)
        
        # 获取规格和NUMA信息
        specifications = _get_remote_cpu_specifications(target_host, is_zh)
        
        return {
            "real_time_frequencies": real_time_frequencies,
            "specifications": specifications,
            "numa_topology": specifications.get("numa_nodes", {}),
            "host": target_host.name
        }
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


def _get_local_cpu_frequencies(is_zh: bool) -> Dict[str, float]:
    """获取本地CPU实时频率"""
    cmd = 'for i in /sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_cur_freq; do [ -f $i ] && echo "$i: $(($(cat $i)/1000)) MHz"; done'
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        return _parse_cpu_frequencies(result.stdout)
    except subprocess.CalledProcessError as e:
        msg = f"获取CPU频率失败: {e.stderr}" if is_zh else f"Failed to get CPU frequencies: {e.stderr}"
        # Don't raise, return empty dict as this might not be available
        return {}


def _get_remote_cpu_frequencies(host_config, is_zh: bool) -> Dict[str, float]:
    """获取远程CPU实时频率"""
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
        
        cmd = 'for i in /sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_cur_freq; do [ -f $i ] && echo "$i: $(($(cat $i)/1000)) MHz"; done'
        stdin, stdout, stderr = client.exec_command(cmd)
        stdin.close()
        
        output = stdout.read().decode('utf-8')
        return _parse_cpu_frequencies(output)
    except paramiko.AuthenticationException as e:
        msg = "SSH认证失败" if is_zh else "SSH auth failed"
        raise ConnectionError(msg) from e
    finally:
        client.close()


def _get_local_cpu_specifications(is_zh: bool) -> Dict[str, Any]:
    """获取本地CPU规格信息"""
    try:
        result = subprocess.run(
            ['lscpu'],
            capture_output=True,
            text=True,
            check=True
        )
        return _parse_cpu_specifications(result.stdout)
    except subprocess.CalledProcessError as e:
        msg = f"获取CPU规格失败: {e.stderr}" if is_zh else f"Failed to get CPU specs: {e.stderr}"
        raise RuntimeError(msg) from e


def _get_remote_cpu_specifications(host_config, is_zh: bool) -> Dict[str, Any]:
    """获取远程CPU规格信息"""
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
        
        stdin, stdout, stderr = client.exec_command('lscpu')
        stdin.close()
        
        output = stdout.read().decode('utf-8')
        return _parse_cpu_specifications(output)
    except paramiko.AuthenticationException as e:
        msg = "SSH认证失败" if is_zh else "SSH auth failed"
        raise ConnectionError(msg) from e
    finally:
        client.close()


def _parse_cpu_frequencies(output: str) -> Dict[str, float]:
    """解析CPU实时频率信息"""
    frequencies = {}
    for line in output.split('\n'):
        if ': ' in line and "MHz" in line:
            try:
                path, freq = line.split(': ')
                cpu_id = path.split('/')[-3].replace('cpu', '')
                frequencies[f"cpu{cpu_id}"] = float(freq.replace(' MHz', '').strip())
            except Exception:
                continue
    return frequencies


def _parse_cpu_specifications(output: str) -> Dict[str, Any]:
    """解析CPU规格信息"""
    result = {}
    numa_nodes = {}
    
    for line in output.split('\n'):
        if line.startswith("Model name:"):
            result["model_name"] = line.split(":")[1].strip()
        elif line.startswith("CPU max MHz:"):
            try:
                result["max_mhz"] = float(line.split(":")[1].strip())
            except (ValueError, IndexError):
                result["max_mhz"] = 0.0
        elif line.startswith("CPU min MHz:"):
            try:
                result["min_mhz"] = float(line.split(":")[1].strip())
            except (ValueError, IndexError):
                result["min_mhz"] = 0.0
        elif line.startswith("NUMA node"):
            parts = line.split(':')
            if len(parts) < 2:
                continue
            match = re.search(r'node(\d+)', parts[0])
            if match:
                node_id = match.group(1)
                cpus_str = parts[1].strip()
                cpu_list = []
                for part in cpus_str.split(','):
                    part = part.strip()
                    if '-' in part:
                        try:
                            start, end = map(int, part.split('-'))
                            cpu_list.extend(range(start, end + 1))
                        except ValueError:
                            continue
                    elif part.isdigit():
                        cpu_list.append(int(part))
                numa_nodes[node_id] = {"cpus": cpu_list}
    
    result["numa_nodes"] = numa_nodes
    return result


if __name__ == "__main__":
    mcp.run(transport='sse')
