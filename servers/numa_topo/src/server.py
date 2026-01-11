from typing import Union, Dict, Any
import paramiko
import subprocess
import re
from mcp.server import FastMCP
from config.public.base_config_loader import LanguageEnum
from config.private.numa_topo.config_loader import NumaTopoConfig

mcp = FastMCP("NUMA Topology MCP Server", host="0.0.0.0", port=NumaTopoConfig().get_config().private_config.port)

@mcp.tool(
    name="numa_topo_tool"
    if NumaTopoConfig().get_config().public_config.language == LanguageEnum.ZH
    else "numa_topo_tool",
    description='''
    使用 numactl 命令获取远端机器或本机的 NUMA 拓扑信息
    1. 输入值如下：
        - host: 远程主机名称或 IP 地址，若不提供则表示获取本机信息
    2. 返回值为包含 NUMA 拓扑信息的字典，包含以下键：
        - nodes_total: 总节点数
        - nodes: 节点信息列表，每个节点包含：
            - node_id: 节点 ID
            - cpus: 该节点上的 CPU 列表
            - size_mb: 内存大小（MB）
            - free_mb: 空闲内存（MB）
    '''
    if NumaTopoConfig().get_config().public_config.language == LanguageEnum.ZH
    else 
    '''
    Use the numactl command to obtain NUMA topology information from a remote machine or the local machine.
    1. Input values are as follows:
        - host: Remote host name or IP address. If not provided, retrieves local machine info.
    2. The return value is a dictionary containing NUMA topology information, with each dictionary including the following keys:
        - nodes_total: Total number of nodes
        - nodes: List of node information, each node contains:
            - node_id: Node ID
            - cpus: List of CPUs on this node
            - size_mb: Memory size in MB
            - free_mb: Free memory in MB
    '''
)

def numa_topo_tool(host: Union[str, None] = None) -> Dict[str, Any]:
    """
    使用 numactl 命令获取本地或远程主机的 NUMA 拓扑信息
    """
    def parse_numactl_output(output: str) -> Dict[str, Any]:
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

    try:
        if host is None:
            result = subprocess.run(['numactl', '-H'], capture_output=True, text=True, check=True)
            output = result.stdout
        else:
            config = NumaTopoConfig().get_config()
            target_host = None
            for host_config in config.public_config.remote_hosts:
                if host.strip() == host_config.name or host.strip() == host_config.host:
                    target_host = host_config
                    break

            if not target_host:
                if config.public_config.language == LanguageEnum.ZH:
                    raise ValueError(f"未找到远程主机: {host}")
                else:
                    raise ValueError(f"Remote host not found: {host}")

            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                hostname=target_host.host,
                port=target_host.port,
                username=target_host.username,
                password=getattr(target_host, "password", None),
                key_filename=getattr(target_host, "ssh_key_path", None),
                timeout=10
            )
            stdin, stdout, stderr = client.exec_command('numactl -H')
            output = stdout.read().decode('utf-8')
            err = stderr.read().decode('utf-8').strip()
            client.close()

            if err:
                raise RuntimeError(err)

        return parse_numactl_output(output)

    except subprocess.CalledProcessError as e:
        if NumaTopoConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise RuntimeError(f"本地 numactl 执行失败: {e.stderr}")
        else:
            raise RuntimeError(f"Local numactl execution failed: {e.stderr}")
    except paramiko.AuthenticationException:
        if NumaTopoConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise RuntimeError("SSH 认证失败，请检查用户名或密钥")
        else:
            raise RuntimeError("SSH authentication failed, please check the username or key")
    except paramiko.SSHException as e:
        if NumaTopoConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise RuntimeError(f"SSH 连接错误: {e}")
        else:
            raise RuntimeError(f"SSH connection error: {e}")
    except Exception as e:
        if NumaTopoConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise RuntimeError(f"获取 NUMA 拓扑信息失败: {str(e)}")
        else:
            raise RuntimeError(f"Failed to retrieve NUMA topology information: {str(e)}")


if __name__ == "__main__":
    mcp.run(transport='sse')