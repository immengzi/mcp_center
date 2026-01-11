import re
import subprocess
from typing import Any, Dict, Optional

import paramiko
from mcp.server import FastMCP

from config.private.numa_topo.config_loader import NumaTopoConfig
from config.public.base_config_loader import LanguageEnum

# 初始化配置
config = NumaTopoConfig()

mcp = FastMCP(
    "NUMA Topology MCP Server",
    host="0.0.0.0",
    port=config.get_config().private_config.port
)


@mcp.tool(
    name="numa_topo_tool"
    if config.get_config().public_config.language == LanguageEnum.ZH
    else "numa_topo_tool",
    description="""
    使用 numactl 命令获取远端机器或本机的 NUMA 拓扑信息。
    参数：
        host: 可选，远程主机名称（使用public_config.toml中配置的name字段）；留空则获取本机信息。
    返回：
        dict {
            "nodes_total": int,       # 总节点数
            "nodes": list,            # 节点信息列表，每个节点包含：
                                      #   - node_id: 节点 ID
                                      #   - cpus: 该节点上的 CPU 列表
                                      #   - size_mb: 内存大小（MB）
                                      #   - free_mb: 空闲内存（MB）
            "host": str               # 主机标识（本机为"localhost"）
        }
    """
    if config.get_config().public_config.language == LanguageEnum.ZH
    else """
    Use the numactl command to obtain NUMA topology information from a remote machine or local machine.
    Args:
        host: Optional remote host name (configured in public_config.toml); retrieves local info if omitted.
    Returns:
        dict {
            "nodes_total": int,       # Total number of nodes
            "nodes": list,            # List of node information, each node contains:
                                      #   - node_id: Node ID
                                      #   - cpus: List of CPUs on this node
                                      #   - size_mb: Memory size in MB
                                      #   - free_mb: Free memory in MB
            "host": str               # Host identifier ("localhost" for local)
        }
    """
)
def numa_topo_tool(host: Optional[str] = None) -> Dict[str, Any]:
    """
    获取本地或远程主机的 NUMA 拓扑信息
    
    Args:
        host: 远程主机名称（public_config.toml 中的 name），None 表示本机
        
    Returns:
        包含 NUMA 拓扑信息的字典
    """
    cfg = config.get_config()
    is_zh = cfg.public_config.language == LanguageEnum.ZH
    
    # 本地执行
    if not host or host.strip().lower() in ("", "localhost"):
        return _execute_local_numactl(is_zh)
    
    # 远程执行
    return _execute_remote_numactl_workflow(host.strip(), cfg, is_zh)


def _execute_local_numactl(is_zh: bool) -> Dict[str, Any]:
    """执行本地 numactl 命令"""
    try:
        result = subprocess.run(
            ['numactl', '-H'],
            capture_output=True,
            text=True,
            check=True
        )
        info = _parse_numactl_output(result.stdout)
        info["host"] = "localhost"
        return info
    except subprocess.CalledProcessError as e:
        msg = f"本地 numactl 执行失败: {e.stderr}" if is_zh else f"Local numactl execution failed: {e.stderr}"
        raise RuntimeError(msg) from e


def _execute_remote_numactl_workflow(
    host_name: str, cfg, is_zh: bool
) -> Dict[str, Any]:
    """远程执行工作流"""
    target_host = _find_remote_host(host_name, cfg.public_config.remote_hosts, is_zh)
    
    try:
        info = _execute_remote_numactl(target_host, is_zh)
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


def _execute_remote_numactl(host_config, is_zh: bool) -> Dict[str, Any]:
    """在远程主机执行 numactl"""
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
        
        stdin, stdout, stderr = client.exec_command('numactl -H')
        stdin.close()
        
        output = stdout.read().decode('utf-8')
        err = stderr.read().decode('utf-8').strip()
        
        if err:
            raise RuntimeError(f"numactl failed: {err}")
        
        return _parse_numactl_output(output)
    except paramiko.AuthenticationException as e:
        msg = "SSH认证失败" if is_zh else "SSH auth failed"
        raise ConnectionError(msg) from e
    finally:
        client.close()


def _parse_numactl_output(output: str) -> Dict[str, Any]:
    """解析 numactl -H 输出"""
    info = {
        'nodes_total': 0,
        'nodes': []
    }
    lines = output.strip().split('\n')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith('available:'):
            match = re.search(r'available:\s+(\d+)\s+nodes', line)
            if match:
                info['nodes_total'] = int(match.group(1))

        elif line.startswith('node '):
            parts = line.split()
            if len(parts) < 3:
                continue
            node_id = int(parts[1])
            key = parts[2]
            values = parts[3:]

            # 如果是新节点，创建条目
            node_exists = any(n['node_id'] == node_id for n in info['nodes'])
            if not node_exists:
                info['nodes'].append({
                    'node_id': node_id,
                    'cpus': [],
                    'size_mb': 0,
                    'free_mb': 0
                })

            # 获取当前节点条目
            current_node = next(n for n in info['nodes'] if n['node_id'] == node_id)

            if key == 'cpus:':
                current_node['cpus'] = list(map(int, values))
            elif key == 'size:':
                if values and values[0].isdigit():
                    current_node['size_mb'] = int(values[0])
            elif key == 'free:':
                if values and values[0].isdigit():
                    current_node['free_mb'] = int(values[0])

    return info


if __name__ == "__main__":
    mcp.run(transport='sse')
