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
    name="sar_collect_tool"
    if TopConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "sar_collect_tool",
    description='''
    使用sar命令分析资源使用的周期性规律
    1. 输入值如下：
        - host: 远程主机名称或IP地址
        - option_param1: sar后跟的可选选项
        - option_param2: 例如 -n 选项后,还需进一步跟相应参数
        - option_param3: 时间间隔
        - option_param4: 次数
    2. 返回值为包含相应信息的字典列表，每个字典包含以下键
        - timestamp: 采集指标的时间
        当options设置为-u时,采集的是cpu相关信息:
            - user: 用户模式下消耗的CPU时间的比例
            - nice: 通过nice改变了进程调度优先级的进程，在用户模式下消耗的CPU时间的比例
            - system: 系统模式下消耗的CPU时间的比例
            - iowait: CPU等待磁盘I/O导致空闲状态消耗的时间比例
            - steal:利用Xen等操作系统虚拟化技术，等待其它虚拟CPU计算占用的时间比例
            - idle:CPU空闲时间比例
        当options设置为-r时,采集的是内存相关信息:
            - kbmemfree:这个值和free命令中的free值基本一致,所以它不包括buffer和cache的空间
            - kbmemused: 这个值和free命令中的used值基本一致,所以它包括buffer和cache的空间
            - memused: 这个值是kbmemused和内存总量(不包括swap)的一个百分比(单位 % )
            - kbbuffers: free命令中的buffer 
            - kbcached: free命令中的cache
            - kbcommit: 保证当前系统所需要的内存,即为了确保不溢出而需要的内存(RAM+swap)
            - commit:这个值是kbcommit与内存总量(包括swap)的一个百分比(单位 % )
        当options设置为-d时,采集的是磁盘I/O相关信息:
            - name: 磁盘设备名称
            - tps: 每秒传输次数（IOPS）。
            - rkBpers: 每秒读取的数据量（KB/s）。
            - wkBpers: 每秒写入的数据量（KB/s）。
            - dkBpers: 每秒写入的数据量（KB/s）。
            - areqsz: 
            - aqusz: 
            - await: 平均等待时间（毫秒）。
            - util: 磁盘利用率（百分比）。

    '''
    if TopConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    '''
    Using the sar command to obtain memory usage information from a remote machine or the local machine.
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
def sar_collect_tool(host: Union[str, None] = None, options: str = None, interval: int = None, count: int = None) -> List[Dict[str, Any]]:
    """使用sar命令获取服务器内存整体状态"""
    if host is None:
        command = ['sar']
        if options is not None:
            command.append(options)
        if interval is not None:
            command.append(str(interval))
        if count is not None:
            command.append(str(count))
        # print(f"Running command: {' '.join(command)}")
        result = subprocess.run(command, capture_output=True, text=True)
        statistics = []
        if options == '-u' or options == None:
            lines = result.stdout.split('\n')
            # 从第4行开始进行信息提取,到倒数第二行,最后一行的average还没统计
            for line in lines[3:-2]:
                parts = line.split()
                timestamp = parts[0]
                user = float(parts[3])
                nice = float(parts[4])
                system = float(parts[5])
                iowait = float(parts[6])
                steal = float(parts[7])
                idle = float(parts[8])
                statistics.append({
                    'timestamp': timestamp,
                    'user': user,
                    'nice': nice,
                    'system': system,
                    'iowait': iowait,
                    'steal': steal, 
                    'idle': idle
                })
        elif options == '-r':
            lines = result.stdout.split('\n')
            # 从第4行开始进行信息提取,到倒数第二行,最后一行的average还没统计
            for line in lines[3:-2]:
                parts = line.split()
                timestamp = parts[0]
                kbmemfree = int(parts[2])
                kbmemused = int(parts[4])
                memused = float(parts[5])
                kbbuffers = int(parts[6])
                kbcached = int(parts[7])
                kbcommit = int(parts[8])
                commit = float(parts[9])
                statistics.append({
                    'timestamp': timestamp,
                    'kbmemfree': kbmemfree,
                    'kbmemused': kbmemused,
                    'memused': memused,
                    'kbbuffers': kbbuffers,
                    'kbcached': kbcached, 
                    'kbcommit': kbcommit,
                    'commit': commit
                })
        elif options == '-d':
            lines = result.stdout.split('\n')
            for line in lines[3:-2]:
                parts = line.split()
                timestamp = parts[0] + parts[1]
                name = parts[2]
                tps = float(parts[3])
                rkBpers = float(parts[4])
                wkBpers = float(parts[5])
                dkBpers = float(parts[6])
                areqsz = float(parts[7])
                aqusz = float(parts[8])
                avgwait = float(parts[9])
                util = float(parts[10])
                statistics.append({
                    'timestamp': timestamp,
                    'name': name,
                    'tps': tps,
                    'rkBpers': rkBpers,
                    'wkBpers': wkBpers,
                    'dkBpers': dkBpers,
                    'areqsz': areqsz,
                    'aqusz': aqusz,
                    'await': avgwait,
                    'util': util
                })
        return statistics   
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
                command = ['sar']
                if options is not None:
                    command.append(options)
                if interval is not None:
                    command.append(str(interval))
                if count is not None:
                    command.append(str(count))
                stdin, stdout, stderr = ssh.exec_command(command)
                output = stdout.read().decode()
                ssh.close()

                lines = output.strip().split('\n')
                statistics = []
                if options == '-u' or options == None:
                    # 从第4行开始进行信息提取,到倒数第二行,最后一行的average还没统计
                    for line in lines[3:-2]:
                        parts = line.split()
                        timestamp = parts[0]
                        user = float(parts[3])
                        nice = float(parts[4])
                        system = float(parts[5])
                        iowait = float(parts[6])
                        steal = float(parts[7])
                        idle = float(parts[8])
                        statistics.append({
                            'timestamp': timestamp,
                            'user': user,
                            'nice': nice,
                            'system': system,
                            'iowait': iowait,
                            'steal': steal, 
                            'idle': idle
                        })
                elif options == '-r':
                    lines = result.stdout.split('\n')
                    # 从第4行开始进行信息提取,到倒数第二行,最后一行的average还没统计
                    for line in lines[3:-2]:
                        parts = line.split()
                        timestamp = parts[0]
                        kbmemfree = int(parts[2])
                        kbmemused = int(parts[4])
                        memused = float(parts[5])
                        kbbuffers = int(parts[6])
                        kbcached = int(parts[7])
                        kbcommit = int(parts[8])
                        commit = float(parts[9])
                        statistics.append({
                            'timestamp': timestamp,
                            'kbmemfree': kbmemfree,
                            'kbmemused': kbmemused,
                            'memused': memused,
                            'kbbuffers': kbbuffers,
                            'kbcached': kbcached, 
                            'kbcommit': kbcommit,
                            'commit': commit
                        })
                return statistics
        if TopConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise ValueError(f"未找到远程主机: {host}")
        else:
            raise ValueError(f"Remote host not found: {host}")


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='sse')
