from typing import Union, List, Dict
import platform
import os
import paramiko
import yaml
import datetime
import subprocess
from typing import Any, Dict
import psutil
import tempfile
from datetime import datetime
from mcp.server import FastMCP
from config.public.base_config_loader import LanguageEnum
from config.private.top.config_loader import TopConfig
mcp = FastMCP("Perf_Svg MCP Server", host="0.0.0.0", port=TopConfig().get_config().private_config.port)


@mcp.tool(
    name="top_collect_tool"
    if TopConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "top_collect_tool",
    description='''
    使用top命令获取远端机器或者本机内存占用最多的k个进程
    1. 输入值如下：
        - host: 远程主机名称或IP地址，若不提供则表示获取本机的top k进程
        - k: 需要获取的进程数量，默认为5，可根据实际需求调整
    2. 返回值为包含进程信息的字典列表，每个字典包含以下键
        - pid: 进程ID
        - name: 进程名称
        - memory: 内存使用量（单位MB）
    '''
    if TopConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    '''
    Use the top command to get the top k memory-consuming processes on a remote machine or the local machine.
    1. Input values are as follows:
        - host: Remote host name or IP address. If not provided, it means to get
            the top k processes of the local machine.
        - k: The number of processes to be obtained, the default is 5, which can be adjusted according to actual needs.
    2. The return value is a list of dictionaries containing process information, each dictionary contains
        the following keys:
        - pid: Process ID
        - name: Process name
        - memory: Memory usage (in MB)
    '''

)
def top_collect_tool(host: Union[str, None] = None, k: int = 5) -> List[Dict[str, Any]]:
    """使用top命令获取内存占用最多的k个进程"""
    if host is None:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
            try:
                memory_usage = proc.info['memory_info'].rss / (1024 * 1024)  # 转换为MB
                processes.append({
                    'pid': proc.info['pid'],
                    'name': proc.info['name'],
                    'memory': memory_usage
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # 按内存使用量排序并取前k个
        processes.sort(key=lambda x: x['memory'], reverse=True)
        return processes[:k]
    else:
        for host_config in TopConfig().get_config().public_config.remote_hosts:
            if host == host_config.name or host == host_config.host:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(
                    hostname=host_config.host,
                    port=host_config.port,
                    username=host_config.username,
                    password=host_config.password
                )
                stdin, stdout, stderr = ssh.exec_command(f"ps aux --sort=-%mem | head -n {k + 1}")
                output = stdout.read().decode()
                ssh.close()

                lines = output.strip().split('\n')[1:]
                processes = []
                for line in lines:
                    parts = line.split()
                    pid = int(parts[1])
                    name = parts[10]
                    memory = float(parts[3]) * psutil.virtual_memory().total / (1024 * 1024)  # 转换为MB
                    processes.append({
                        'pid': pid,
                        'name': name,
                        'memory': memory
                    })
                return processes
        if TopConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise ValueError(f"未找到远程主机: {host}")
        else:
            raise ValueError(f"Remote host not found: {host}")


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='sse')
