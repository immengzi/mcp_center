from typing import Union, Dict
import paramiko
import subprocess
import re
from mcp.server import FastMCP
from config.public.base_config_loader import LanguageEnum
from config.private.numastat.config_loader import NumastatConfig

mcp = FastMCP("NUMAStat Info MCP Server", host="0.0.0.0", port=NumastatConfig().get_config().private_config.port)

@mcp.tool(
    name="numastat_info_tool"
    if NumastatConfig().get_config().public_config.language == LanguageEnum.ZH
    else "numastat_info_tool",
    description='''
    使用numastat命令获取远端机器或本机NUMA统计信息
    1. 输入值如下：
        - host: 远程主机名称或IP地址，若不提供则表示获取本机信息
    2. 返回值为包含NUMA统计信息的字典，包含以下键：
        - numa_hit: NUMA命中次数
        - numa_miss: NUMA未命中次数
        - numa_foreign: 外部访问次数
        - interleave_hit: 交错命中次数
        - local_node: 本地节点访问次数
        - other_node: 其他节点访问次数
    '''
    if NumastatConfig().get_config().public_config.language == LanguageEnum.ZH
    else 
    '''
    Use the numastat command to obtain NUMA statistics from a remote machine or local machine.
    1. Input values are as follows:
        - host: Remote host name or IP address. If not provided, retrieves local machine info.
    2. The return value is a dictionary containing NUMA statistics with the following keys:
        - numa_hit: NUMA hit count
        - numa_miss: NUMA miss count
        - numa_foreign: Foreign access count
        - interleave_hit: Interleave hit count
        - local_node: Local node access count
        - other_node: Other node access count
    '''
)
def numastat_info_tool(host: Union[str, None] = None) -> Dict[str, int]:
    """
    使用numastat命令获取本地或远程主机的NUMA统计信息
    """
    def parse_numastat_output(output: str) -> Dict[str, int]:
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

    try:
        if host is None:
            result = subprocess.run(['numastat'], capture_output=True, text=True, check=True)
            output = result.stdout
        else:
            config = NumastatConfig().get_config()
            target_host = None
            for host_cfg in config.public_config.remote_hosts:
                if host.strip() == host_cfg.name or host.strip() == host_cfg.host:
                    target_host = host_cfg
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
                port=getattr(target_host, 'port', 22),
                username=getattr(target_host, 'username', None),
                password=getattr(target_host, 'password', None),
                key_filename=getattr(target_host, 'ssh_key_path', None),
                timeout=10
            )

            stdin, stdout, stderr = client.exec_command('numastat')
            output = stdout.read().decode('utf-8')
            err = stderr.read().decode('utf-8').strip()
            client.close()

            if err:
                raise RuntimeError(err)

        return parse_numastat_output(output)

    except subprocess.CalledProcessError as e:
        msg = e.stderr or e.stdout or str(e)
        if NumastatConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise RuntimeError(f"本地 numastat 执行失败: {msg}")
        else:
            raise RuntimeError(f"Local numastat execution failed: {msg}")
    except paramiko.AuthenticationException:
        if NumastatConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise RuntimeError("SSH 认证失败，请检查用户名或密钥")
        else:
            raise RuntimeError("SSH authentication failed, please check the username or key")
    except paramiko.SSHException as e:
        if NumastatConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise RuntimeError(f"SSH 连接错误: {e}")
        else:
            raise RuntimeError(f"SSH connection error: {e}")
    except Exception as e:
        if NumastatConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise RuntimeError(f"获取 NUMA 统计信息失败: {str(e)}")
        else:
            raise RuntimeError(f"Failed to retrieve NUMA statistics: {str(e)}")


if __name__ == "__main__":
    mcp.run(transport='sse')
