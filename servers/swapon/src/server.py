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
    name="swapon_collect_tool"
    if TopConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "swapon_collect_tool",
    description='''
    使用swapon命令查看当前swap设备状态
    1. 输入值如下：
        - host: 远程主机名称或IP地址，若不提供则表示获取本机的swap设备状态
    2. 返回值为包含进程信息的字典列表，每个字典包含以下键
        - name: 设备名称
        - type: 类型
        - size: 大小
        - used: 当前已使用的swap空间
        - prio: swap分区优先级
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
def swapon_collect_tool(host: Union[str, None] = None) -> List[Dict[str, Any]]:
    """使用swapon获取当前swap设备状态"""
    if host is None:
        swap_devices = []
        result = subprocess.run(['swapon'], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        for line in lines[1:-1]:
            parts = line.split()
            name = parts[0]
            device_type = parts[1]
            size = parts[2]
            used = parts[3]
            prio = parts[4]
            swap_devices.append({
                "name": name,
                "type": device_type,
                "size": size,
                "used": used,
                "prio": prio
            })
        return swap_devices
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
                stdin, stdout, stderr = ssh.exec_command(f"swapon")
                output = stdout.read().decode()
                ssh.close()
                
                lines = output.stdout.split('\n')
                swap_devices = []
                for line in lines[1:-1]:
                    parts = line.split()
                    name = parts[0]
                    device_type = parts[1]
                    size = parts[2]
                    used = parts[3]
                    prio = parts[4]
                    swap_devices.append({
                        "name": name,
                        "type": device_type,
                        "size": size,
                        "used": used,
                        "prio": prio
                    })
                return swap_devices
        if TopConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise ValueError(f"未找到远程主机: {host}")
        else:
            raise ValueError(f"Remote host not found: {host}")


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='sse')
