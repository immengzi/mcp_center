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
    name="free_collect_tool"
    if TopConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "free_collect_tool",
    description='''
    使用free命令获取远端机器或者本机内存使用情况
    1. 输入值如下：
        - host: 远程主机名称或IP地址
    2. 返回值为包含进程信息的字典列表，每个字典包含以下键
        - total: 系统内存总量（单位MB）
        - used: 系统已使用内存量（单位MB）
        - free: 空闲的物理内存（单位MB）
        - available: 系统可分配给新应用程序的内存量（单位MB）
    '''
    if TopConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    '''
    Using the free command to obtain memory usage information from a remote machine or the local machine.
    1. Input values are as follows:
        - host: Remote host name or IP address. If not provided, it means to get
            the memory usage information of the local machine.
    2. The return value is a dictionary containing memory information, with the following keys:
        the following keys:
        - total: Total system memory (in MB).
        - used: Memory already used by the system (in MB).
        - available: The amount of memory that can be allocated to new applications by the system (in MB).
    '''

)
def free_collect_tool(host: Union[str, None] = None) -> List[Dict[str, Any]]:
    """使用free命令获取服务器内存整体状态"""
    if host is None:
        memory_info = []
        result = subprocess.run(['free', '-m'], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        parts = lines[1].split()
        total = int(parts[1])
        used = int(parts[2])
        free = int(parts[3])
        available = int(parts[6])
        memory_info = [{'total': total, 'used': used, 'free': free, 'available': available}]
        return memory_info
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
                stdin, stdout, stderr = ssh.exec_command("free -m")
                output = stdout.read().decode()
                ssh.close()

                lines = output.strip().split('\n')
                memory_info = []
                parts = lines[1].split()
                total = int(parts[1])
                used = int(parts[2])
                free = int(parts[3])
                available = int(parts[6])
                memory_info = [{'total': total, 'used': used, 'free': free, 'available': available}]
                return memory_info
        if TopConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise ValueError(f"未找到远程主机: {host}")
        else:
            raise ValueError(f"Remote host not found: {host}")


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='sse')
