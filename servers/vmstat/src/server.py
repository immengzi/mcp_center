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
    name="vmstat_collect_tool"
    if TopConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "vmstat_collect_tool",
    description='''
    使用vmstat命令获取远端机器或者本机内存使用情况
    1. 输入值如下：
        - host: 远程主机名称或IP地址
    2. 返回值为包含进程信息的字典列表，每个字典包含以下键
        - r: 运行队列中的进程数。如果这个数字长期大于CPU核心数，可能表明 CPU 资源紧张。
        - b: 等待 I/O 的进程数。如果这个数字较高，可能表明 I/O 瓶颈。
        - si: 每秒从磁盘加载到内存的数据量。（单位KB/s）
        - so: 每秒从内存换出到磁盘的数据量。如果si/so持续大于0，说明物理内存不足，导致频繁的页面交换。（单位KB/s）
        - bi: 从磁盘读取的块数，块大小通常512B或1KB。
        - bo: 写入磁盘的块数。bi/bo高值可能表示磁盘I/O繁忙。
        - in: 每秒发生的中断次数，包括时钟中断。
        - cs: 每秒上下文切换次数，频繁切换可能因进程过多或锁竞争。
        - us: 用户进程消耗 CPU 时间。
        - sy: 内核进程消耗 CPU 时间。
        - id: CPU 空闲时间。
        - wa: CPU 等待 I/O 完成的时间百分比。如果这个值较高，可能表明 I/O 瓶颈。
        - st: 被虚拟机偷走的 CPU 时间百分比（仅在虚拟环境中相关）。
    '''
    if TopConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    '''
    Using the vmstat command to obtain memory usage information from a remote machine or the local machine.
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
def vmstat_collect_tool(host: str = None):
    """使用vmstat命令获取服务器内存整体状态"""
    if host is None:
        result = subprocess.run(['vmstat'], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        vmstat_output = {}
        parts = lines[2].split()
        r = int(parts[0])
        b = int(parts[1])
        si = int(parts[6])
        so = int(parts[7])
        bi = int(parts[8])
        bo = int(parts[9])
        interrupts = int(parts[10])
        cs = int(parts[11])
        us = int(parts[12])
        sy = int(parts[13])
        id = int(parts[14])
        wa = int(parts[15])
        st = int(parts[16])
        vmstat_output = {
            'r': r,
            'b': b,
            'si': si,
            'so': so,
            'bi': bi,
            'bo': bo,
            'in': interrupts,
            'cs': cs,
            'us': us,
            'sy': sy,
            'id': id,
            'wa': wa,
            'st': st
        }
        return vmstat_output
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
                stdin, stdout, stderr = ssh.exec_command("vmstat")
                output = stdout.read().decode()
                ssh.close()

                lines = output.strip().split('\n')
                vmstat_output = {}
                parts = lines[2].split()
                r = int(parts[0])
                b = int(parts[1])
                si = int(parts[6])
                so = int(parts[7])
                bi = int(parts[8])
                bo = int(parts[9])
                interrupts = int(parts[10])
                cs = int(parts[11])
                us = int(parts[12])
                sy = int(parts[13])
                id = int(parts[14])
                wa = int(parts[15])
                st = int(parts[16])
                vmstat_output = {
                    'r': r,
                    'b': b,
                    'si': si,
                    'so': so,
                    'bi': bi,
                    'bo': bo,
                    'in': interrupts,
                    'cs': cs,
                    'us': us,
                    'sy': sy,
                    'id': id,
                    'wa': wa,
                    'st': st
                }
                return vmstat_output
        if TopConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise ValueError(f"未找到远程主机: {host}")
        else:
            raise ValueError(f"Remote host not found: {host}")


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='sse')
