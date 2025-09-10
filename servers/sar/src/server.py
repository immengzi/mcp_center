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
    使用sar命令分析资源使用的周期性规律或进行历史状态分析
    1. 输入值如下：
        - host: 远程主机名称或IP地址，若不提供则对本机进行分析
        - args: sar后跟的参数列表
    2. 返回值为包含相应信息的字典列表，每个字典包含以下键
        - timestamp: 采集指标的时间
        当args[0]设置为-u时,采集的是cpu相关信息:
            - user: 用户空间程序占用CPU的百分比
            - nice: 低优先级用户进程占用的CPU百分比
            - system: 内核空间程序占用CPU的百分比
            - iowait: CPU等待磁盘I/O操作的时间百分比
            - steal: 虚拟化环境中，其他虚拟机占用的CPU时间百分比
            - idle:CPU空闲时间百分比
        当args[0]设置为-r时,采集的是内存相关信息:
            - kbmemfree:​ 物理空闲内存量（未被使用的内存）
            - kbavail: 实际可用内存（包括缓存和缓冲区的可回收部分）
            - kbmemused: 已使用的物理内存（不包括内核缓存和缓冲区）
            - memused: 已用内存占总物理内存的百分比（百分比）
            - kbbuffers: 内核缓冲区（Buffer）占用的内存（用于块设备读写缓存） 
            - kbcached: ​内核缓存（Cache）占用的内存（用于文件系统缓存）
            - kbcommit: 当前工作负载所需的总内存量（包括已用和预估的）
            - commit: kbcommit占系统总可用内存（物理内存 + Swap）的百分比（百分比）
            - kbactive: 活跃内存（最近被访问过的内存，不易被回收）
            - kbinact: 非活跃内存（较久未访问的内存，可被回收用于新进程）
            - kbdirty: 等待写入磁盘的脏数据量（单位 KB）
        当args[0]设置为-d时,采集的是磁盘I/O相关信息:
            - name: 磁盘设备名称
            - tps: 每秒传输次数（IOPS）
            - rkB_s: 每秒读取的数据量（单位 KB/s）
            - wkB_s: 每秒写入的数据量（单位 KB/s）
            - dkB_s: 每秒丢弃的数据量（单位 KB/s）
            - areq-sz: 平均每次 I/O 请求的数据大小（单位 KB）
            - aqu-sz: 平均 I/O 请求队列长度
            - await: 平均每次 I/O 请求的等待时间（单位 毫秒）
            - util: 设备带宽利用率（百分比）
        当args[0]设置为-n 且后续跟的是DEV时,采集的是网络接口活动信息:
            - iface: 网络接口名称
            - rxpck_s: 每秒接收的数据包数量
            - txpck_s: 每秒发送的数据包数量
            - rxkB_s: 每秒接收的数据量（单位 KB/s）
            - txkB_s: 每秒发送的数据量（单位 KB/s）
            - rxcmp_s: ​每秒接收的压缩数据包数
            - txcmp_s: ​每秒发送的压缩数据包数
            - rxmcst_s: 每秒接收的多播数据包数
            - ifutil: 网络接口带宽利用率（百分比）
    '''
    if TopConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    '''
    Using the sar command to analyze the periodic patterns of resource usage or perform historical state analysis
    1. Input values are as follows:
        - host: The name or IP address of the remote host; if not provided, analysis is performed on the local machine.
        - args: The list of parameters following sar.
    2. The return value is a list of dictionaries containing the corresponding information, each dictionary includes the following keys:
        - timestamp: The time when the metrics were collected.
        When args[0] is set to '-u', the collected information is related to CPU:
            - user: The percentage of CPU used by user space programs.
            - nice: The percentage of CPU used by low-priority user processes.
            - system: The percentage of CPU used by kernel space programs.
            - iowait: The percentage of time the CPU spends waiting for disk I/O operations.
            - steal: In a virtualized environment, the percentage of CPU time used by other virtual machines.
            - idle: The percentage of CPU idle time.
        When args[0] is set to '-r', the collected information is related to memory:
            - kbmemfree: The amount of physical free memory (unused memory).
            - kbavail: The actual available memory (including reclaimable parts of cache and buffers).
            - kbmemused: The amount of physical memory used (excluding kernel cache and buffers).
            - memused: The percentage of used memory out of total physical memory (percentage).
            - kbbuffers: The memory used by kernel buffers (Buffer) (used for block device read/write caching).
            - kbcached: The memory used by kernel cache (Cache) (used for file system caching).
            - kbcommit: The total amount of memory required for the current workload (including used and estimated).
            - commit: The percentage of kbcommit out of the system's total available memory (physical memory + Swap) (percentage).
            - kbactive: Active memory (recently accessed memory, not easily reclaimed).
            - kbinact: Inactive memory (less recently accessed memory, can be reclaimed for new processes).
            - kbdirty: The amount of dirty data waiting to be written to disk (unit: KB).
        When args[0] is set to '-d', the following disk I/O related information is collected:
            - name: Disk device name
            - tps: Transactions per second (IOPS)
            - rkB_s: Data read per second (unit: KB/s)
            - wkB_s: Data written per second (unit: KB/s)
            - dkB_s: Data discarded per second (unit: KB/s)
            - areq-sz: Average data size of each I/O request (unit: KB)
            - aqu-sz: Average I/O request queue length
            - await: Average wait time for each I/O request (unit: milliseconds)
            - util: Device bandwidth utilization (percentage)
        When args[0] is set to '-n' and followed by DEV, the following network interface activity information is collected:
            - iface: Network interface name
            - rxpck_s: Number of packets received per second
            - txpck_s: Number of packets sent per second
            - rxkB_s: Data received per second (unit: KB/s)
            - txkB_s: Data sent per second (unit: KB/s)
            - rxcmp_s: Number of compressed packets received per second
            - txcmp_s: Number of compressed packets sent per second
            - rxmcst_s: Number of multicast packets received per second
            - ifutil: Network interface bandwidth utilization (percentage)
    '''

)
def sar_collect_tool(host: Union[str, None] = None, args: List[str] = []) -> List[Dict[str, Any]]:
    """使用sar命令获取服务器整体状态"""
    if host is None:
        try:
            command = ['sar']
            command.extend([arg for arg in args if arg is not None])
            print(f"Running command: {' '.join(command)}")
            result = subprocess.run(command, capture_output=True, text=True)
            lines = result.stdout.split('\n')
            statistics = []
            if args[0] == '-u':
                for line in lines:
                    parts = line.split()
                    if len(parts) < 9:
                        # raise ValueError(f"{command} 命令输出字段不足，无法提取所需信息")
                        # 输出存在表头/空行和Avg行
                        continue
                    try:
                        datetime.strptime(parts[0], "%H:%M:%S")
                        float(parts[3])
                    except ValueError:
                        continue
                    statistics.append({
                        'timestamp': parts[0] + ' ' + parts[1],
                        'user': float(parts[3]),
                        'nice': float(parts[4]),
                        'system': float(parts[5]),
                        'iowait': float(parts[6]),
                        'steal': float(parts[7]), 
                        'idle': float(parts[8])
                    })
            elif args[0] == '-r':
                for line in lines:
                    parts = line.split()
                    if len(parts) < 13:
                        # raise ValueError(f"{command} 命令输出字段不足，无法提取所需信息")
                        continue
                    try:
                        datetime.strptime(parts[0], "%H:%M:%S")
                        int(parts[2])
                    except ValueError:
                        continue
                    statistics.append({
                        'timestamp': parts[0] + ' ' + parts[1],
                        'kbmemfree': int(parts[2]),
                        'kbavail': int(parts[3]),
                        'kbmemused': int(parts[4]),
                        'memused': float(parts[5]),
                        'kbbuffers': int(parts[6]),
                        'kbcached': int(parts[7]), 
                        'kbcommit': int(parts[8]),
                        'commit': float(parts[9]),
                        'kbactive': float(parts[10]),
                        'kbinact': float(parts[11]),
                        'kbdirty': float(parts[12])
                    })
            elif args[0] == '-d':
                for line in lines:
                    parts = line.split()
                    if len(parts) < 11:
                        # raise ValueError(f"{command} 命令输出字段不足，无法提取所需信息")
                        continue
                    try:
                        datetime.strptime(parts[0], "%H:%M:%S")
                        float(parts[3])
                    except ValueError:
                        continue
                    statistics.append({
                        'timestamp': parts[0] + ' ' + parts[1],
                        'name': parts[2],
                        'tps': float(parts[3]),
                        'rkB_s': float(parts[4]),
                        'wkB_s': float(parts[5]),
                        'dkB_s': float(parts[6]),
                        'areq-sz': float(parts[7]),
                        'aqu-sz': float(parts[8]),
                        'await': float(parts[9]),
                        'util': float(parts[10])
                    })
            elif args[0] == '-n' and args[1] == 'DEV':
                for line in lines:
                    parts = line.split()
                    if len(parts) < 11:
                        # raise ValueError(f"{command} 命令输出字段不足，无法提取所需信息")
                        continue
                    try:
                        datetime.strptime(parts[0], "%H:%M:%S")
                        float(parts[3])
                    except ValueError:
                        continue
                    statistics.append({
                        'timestamp': parts[0] + ' ' + parts[1],
                        'iface': parts[2],
                        'rxpck_s': float(parts[3]),
                        'txpck_s': float(parts[4]),
                        'rxkB_s': float(parts[5]),
                        'txkB_s': float(parts[6]),
                        'rxcmp_s': float(parts[7]),
                        'txcmp_s': float(parts[8]),
                        'rxmcst_s': float(parts[9]),
                        'ifutil': float(parts[10])
                    })
            else:
                raise ValueError(f"{command} 命令返回信息无法解析")
            return statistics
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"执行 {command} 命令失败: {e.stderr}") from e
        except Exception as e:
            raise RuntimeError(f"执行 {command} 命令发生未知错误: {str(e)}") from e
    else:
        for host_config in TopConfig().get_config().public_config.remote_hosts:
            if host == host_config.name or host == host_config.host:
                try:
                    # 建立SSH连接
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh.connect(
                        hostname=host_config.host,
                        port=host_config.port,
                        username=host_config.username,
                        password=host_config.password
                    )
                    command = 'sar'
                    command += ''.join(f' {arg}' for arg in args if arg is not None)
                    stdin, stdout, stderr = ssh.exec_command(command, timeout = 20)
                    error = stderr.read().decode().strip()
                    output = stdout.read().decode().strip()

                    if error:
                        raise ValueError(f"Command {command} error: {error}")

                    if not output:
                        raise ValueError("未能获取信息")
                    
                    lines = output.split('\n')
                    statistics = []
                    if args[0] == '-u':
                        for line in lines:
                            parts = line.split()
                            if len(parts) < 9:
                                # raise ValueError(f"{command} 命令输出字段不足，无法提取所需信息")
                                # 输出存在表头/空行和Avg行
                                continue
                            try:
                                datetime.strptime(parts[0], "%H:%M:%S")
                                float(parts[3])
                            except ValueError:
                                continue
                            statistics.append({
                                'timestamp': parts[0] + ' ' + parts[1],
                                'user': float(parts[3]),
                                'nice': float(parts[4]),
                                'system': float(parts[5]),
                                'iowait': float(parts[6]),
                                'steal': float(parts[7]), 
                                'idle': float(parts[8])
                            })
                    elif args[0] == '-r':
                        for line in lines:
                            parts = line.split()
                            if len(parts) < 13:
                                # raise ValueError(f"{command} 命令输出字段不足，无法提取所需信息")
                                continue
                            try:
                                datetime.strptime(parts[0], "%H:%M:%S")
                                int(parts[2])
                            except ValueError:
                                continue
                            statistics.append({
                                'timestamp': parts[0] + ' ' + parts[1],
                                'kbmemfree': int(parts[2]),
                                'kbavail': int(parts[3]),
                                'kbmemused': int(parts[4]),
                                'memused': float(parts[5]),
                                'kbbuffers': int(parts[6]),
                                'kbcached': int(parts[7]), 
                                'kbcommit': int(parts[8]),
                                'commit': float(parts[9]),
                                'kbactive': float(parts[10]),
                                'kbinact': float(parts[11]),
                                'kbdirty': float(parts[12])
                            })
                    elif args[0] == '-d':
                        for line in lines:
                            parts = line.split()
                            if len(parts) < 11:
                                # raise ValueError(f"{command} 命令输出字段不足，无法提取所需信息")
                                continue
                            try:
                                datetime.strptime(parts[0], "%H:%M:%S")
                                float(parts[3])
                            except ValueError:
                                continue
                            statistics.append({
                                'timestamp': parts[0] + ' ' + parts[1],
                                'name': parts[2],
                                'tps': float(parts[3]),
                                'rkB_s': float(parts[4]),
                                'wkB_s': float(parts[5]),
                                'dkB_s': float(parts[6]),
                                'areq-sz': float(parts[7]),
                                'aqu-sz': float(parts[8]),
                                'await': float(parts[9]),
                                'util': float(parts[10])
                            })
                    elif args[0] == '-n' and args[1] == 'DEV':
                        for line in lines:
                            parts = line.split()
                            if len(parts) < 11:
                                # raise ValueError(f"{command} 命令输出字段不足，无法提取所需信息")
                                continue
                            try:
                                datetime.strptime(parts[0], "%H:%M:%S")
                                float(parts[3])
                            except ValueError:
                                continue
                            statistics.append({
                                'timestamp': parts[0] + ' ' + parts[1],
                                'iface': parts[2],
                                'rxpck_s': float(parts[3]),
                                'txpck_s': float(parts[4]),
                                'rxkB_s': float(parts[5]),
                                'txkB_s': float(parts[6]),
                                'rxcmp_s': float(parts[7]),
                                'txcmp_s': float(parts[8]),
                                'rxmcst_s': float(parts[9]),
                                'ifutil': float(parts[10])
                            })
                    else:
                        raise ValueError(f"{command} 命令返回信息无法解析")
                    return statistics
                except paramiko.AuthenticationException:
                    raise ValueError("SSH认证失败，请检查用户名和密码")
                except paramiko.SSHException as e:
                    raise ValueError(f"SSH连接错误: {str(e)}")
                except Exception as e:
                    raise ValueError(f"获取远程内存信息失败: {str(e)}")
                finally:
                    # 确保SSH连接关闭
                    if ssh is not None:
                        try:
                            ssh.close()
                        except Exception:
                            pass
        if TopConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise ValueError(f"未找到远程主机: {host}")
        else:
            raise ValueError(f"Remote host not found: {host}")


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='sse')
