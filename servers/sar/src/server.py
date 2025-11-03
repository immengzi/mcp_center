from typing import Union, List, Dict, Any
import os
import paramiko
import datetime
import subprocess
from mcp.server import FastMCP
from config.public.base_config_loader import LanguageEnum
from config.private.sar.config_loader import SarConfig
mcp = FastMCP("Sar MCP Server", host="0.0.0.0", port=SarConfig().get_config().private_config.port)


@mcp.tool(
    name="sar_cpu_collect_tool"
    if SarConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "sar_cpu_collect_tool",
    description='''
    使用sar命令分析cpu使用的周期性规律
    1. 输入值如下：
        - host: 远程主机名称或IP地址，若不提供则对本机进行分析
        - interval: 监控的时间间隔
        - count: 监控次数
    2. 返回值为包含相应信息的字典列表，每个字典包含以下键
        - timestamp: 采集指标的时间
        - user: 用户空间程序占用CPU的百分比
        - nice: 低优先级用户进程占用的CPU百分比
        - system: 内核空间程序占用CPU的百分比
        - iowait: CPU等待磁盘I/O操作的时间百分比
        - steal: 虚拟化环境中，其他虚拟机占用的CPU时间百分比
        - idle: CPU空闲时间百分比
    '''
    if SarConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    '''
    Using the sar command to analyze the periodic patterns of resource usage
    1. Input values are as follows:
        - host: The name or IP address of the remote host; if not provided, the analysis is performed on the local machine
        - interval: The time interval for monitoring
        - count: The number of monitoring instances
    2. The return value is a list of dictionaries containing the corresponding information, each dictionary includes the following keys:
        - timestamp: The time when the metrics were collected.
        - user: The percentage of CPU used by user space programs.
        - nice: The percentage of CPU used by low-priority user processes.
        - system: The percentage of CPU used by kernel space programs.
        - iowait: The percentage of time the CPU spends waiting for disk I/O operations.
        - steal: In a virtualized environment, the percentage of CPU time used by other virtual machines.
        - idle: The percentage of CPU idle time.
    '''

)
def sar_cpu_collect_tool(host: Union[str, None] = None, interval: int = None, count: int = None) -> List[Dict[str, Any]]:
    """使用sar命令分析cpu使用的周期性规律"""
    if host is None:
        try:
            command = ['sar', '-u']
            if interval is not None:
                command.append(str(interval))
            if count is not None:
                command.append(str(count))
            result = subprocess.run(command, capture_output=True, text=True)
            lines = result.stdout.split('\n')
            statistics = []
            for line in lines:
                parts = line.split()
                if len(parts) < 9:
                    # 表头/空行和Avg行跳过
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
            return statistics
        except Exception as e:
            if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                raise RuntimeError(f"获取 {command} 输出信息时发生未知错误: {str(e)}") from e
            else:
                raise RuntimeError(f"An unknown error occurred while retrieving the output information for {command} : {str(e)}") from e
    else:
        for host_config in SarConfig().get_config().public_config.remote_hosts:
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
                    command = f'sar -u'
                    if interval is not None:
                        command += f' {interval}'
                    if count is not None:
                        command += f' {count}'
                    stdin, stdout, stderr = ssh.exec_command(command, timeout = 20)
                    error = stderr.read().decode().strip()
                    output = stdout.read().decode().strip()

                    if error:
                        if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                            raise ValueError(f"执行命令 {command} 错误：{error}")
                        else:
                            raise ValueError(f"Executing command {command} error: {error}")

                    if not output:
                        if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                            raise ValueError("未能获取信息")
                        else:
                            raise ValueError("No information obtained")
                    
                    lines = output.split('\n')
                    statistics = []
                    for line in lines:
                        parts = line.split()
                        if len(parts) < 9:
                            # 表头/空行和Avg行跳过
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
                    return statistics
                except paramiko.AuthenticationException:
                    raise ValueError("SSH认证失败，请检查用户名和密码")
                except paramiko.SSHException as e:
                    raise ValueError(f"SSH连接错误: {str(e)}")
                except Exception as e:
                    raise ValueError(f"远程执行 {command} 失败: {str(e)}")
                finally:
                    # 确保SSH连接关闭
                    if ssh is not None:
                        try:
                            ssh.close()
                        except Exception:
                            pass
        if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise ValueError(f"未找到远程主机: {host}")
        else:
            raise ValueError(f"Remote host not found: {host}")

@mcp.tool(
    name="sar_memory_collect_tool"
    if SarConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "sar_memory_collect_tool",
    description='''
    使用sar命令分析内存使用的周期性规律
    1. 输入值如下：
        - host: 远程主机名称或IP地址，若不提供则对本机进行分析
        - interval: 监控的时间间隔
        - count: 监控次数
    2. 返回值为包含相应信息的字典列表，每个字典包含以下键
        - timestamp: 采集指标的时间
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
    '''
    if SarConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    '''
    Use the sar command to analyze the periodic patterns of memory usage.
    1. Input values are as follows:
        - host: The name or IP address of the remote host; if not provided, the analysis is performed on the local machine
        - interval: The time interval for monitoring
        - count: The number of monitoring instances
    2. The return value is a list of dictionaries containing the corresponding information, each dictionary includes the following keys:
        - timestamp: The time when the metrics were collected.
        - kbmemfree: Physical free memory (unused memory)
        - kbavail: Actual available memory (including reclaimable parts of cache and buffers)
        - kbmemused: Used physical memory (excluding kernel cache and buffers)
        - memused: Percentage of used memory relative to total physical memory (percentage)
        - kbbuffers: Memory used by kernel buffers (used for block device read/write caching)
        - kbcached: Memory used by kernel cache (used for file system caching)
        - kbcommit: Total memory required for the current workload (including used and estimated)
        - commit: Percentage of `kbcommit` relative to the system's total available memory (physical memory + Swap) (percentage)
        - kbactive: Active memory (recently accessed memory, not easily reclaimable)
        - kbinact: Inactive memory (less recently accessed memory, reclaimable for new processes)
        - kbdirty: Amount of dirty data waiting to be written to disk (unit: KB)
    '''

)
def sar_memory_collect_tool(host: Union[str, None] = None, interval: int = None, count: int = None) -> List[Dict[str, Any]]:
    """使用sar命令分析内存使用的周期性规律"""
    if host is None:
        try:
            command = ['sar', '-r']
            if interval is not None:
                command.append(str(interval))
            if count is not None:
                command.append(str(count))
            result = subprocess.run(command, capture_output=True, text=True)
            lines = result.stdout.split('\n')
            statistics = []
            for line in lines:
                parts = line.split()
                if len(parts) < 13:
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
            return statistics
        except Exception as e:
            if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                raise RuntimeError(f"获取 {command} 输出信息时发生未知错误: {str(e)}") from e
            else:
                raise RuntimeError(f"An unknown error occurred while retrieving the output information for {command} : {str(e)}") from e
    else:
        for host_config in SarConfig().get_config().public_config.remote_hosts:
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
                    command = f'sar -r'
                    if interval is not None:
                        command += f' {interval}'
                    if count is not None:
                        command += f' {count}'
                    stdin, stdout, stderr = ssh.exec_command(command, timeout = 20)
                    error = stderr.read().decode().strip()
                    output = stdout.read().decode().strip()

                    if error:
                        if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                            raise ValueError(f"执行命令 {command} 错误：{error}")
                        else:
                            raise ValueError(f"Executing command {command} error: {error}")

                    if not output:
                        if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                            raise ValueError("未能获取信息")
                        else:
                            raise ValueError("No information obtained")
                    
                    lines = output.split('\n')
                    statistics = []
                    for line in lines:
                        parts = line.split()
                        if len(parts) < 13:
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
                    return statistics
                except paramiko.AuthenticationException:
                    raise ValueError("SSH认证失败，请检查用户名和密码")
                except paramiko.SSHException as e:
                    raise ValueError(f"SSH连接错误: {str(e)}")
                except Exception as e:
                    raise ValueError(f"远程执行 {command} 失败: {str(e)}")
                finally:
                    # 确保SSH连接关闭
                    if ssh is not None:
                        try:
                            ssh.close()
                        except Exception:
                            pass
        if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise ValueError(f"未找到远程主机: {host}")
        else:
            raise ValueError(f"Remote host not found: {host}")

@mcp.tool(
    name="sar_disk_collect_tool"
    if SarConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "sar_disk_collect_tool",
    description='''
    使用sar命令分析磁盘使用的周期性规律
    1. 输入值如下：
        - host: 远程主机名称或IP地址，若不提供则对本机进行分析
        - interval: 监控的时间间隔
        - count: 监控次数
    2. 返回值为包含相应信息的字典列表，每个字典包含以下键
        - timestamp: 采集指标的时间
        - name: 磁盘设备名称
        - tps: 每秒传输次数（IOPS）
        - rkB_s: 每秒读取的数据量（单位 KB/s）
        - wkB_s: 每秒写入的数据量（单位 KB/s）
        - dkB_s: 每秒丢弃的数据量（单位 KB/s）
        - areq-sz: 平均每次 I/O 请求的数据大小（单位 KB）
        - aqu-sz: 平均 I/O 请求队列长度
        - await: 平均每次 I/O 请求的等待时间（单位 毫秒）
        - util: 设备带宽利用率（百分比）
    '''
    if SarConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    '''
    Using the sar command to analyze the periodic patterns of disk usage
    1. Input values are as follows:
        - host: The name or IP address of the remote host; if not provided, the analysis is performed on the local machine.
        - interval: The monitoring time interval.
        - count: The number of monitoring instances.
    2. The return value is a list of dictionaries containing the corresponding information, with each dictionary including the following keys:
        - timestamp: The time when the metrics were collected.
        - name: The name of the disk device.
        - tps: The number of transactions per second (IOPS).
        - rkB_s: The amount of data read per second (unit: KB/s).
        - wkB_s: The amount of data written per second (unit: KB/s).
        - dkB_s: The amount of data discarded per second (unit: KB/s).
        - areq-sz: The average size of each I/O request (unit: KB).
        - aqu-sz: The average length of the I/O request queue.
        - await: The average wait time for each I/O request (unit: milliseconds).
        - util: The bandwidth utilization of the device (percentage).
    '''

)
def sar_disk_collect_tool(host: Union[str, None] = None, interval: int = None, count: int = None) -> List[Dict[str, Any]]:
    """使用sar命令分析磁盘使用的周期性规律"""
    if host is None:
        try:
            command = ['sar', '-d']
            if interval is not None:
                command.append(str(interval))
            if count is not None:
                command.append(str(count))
            result = subprocess.run(command, capture_output=True, text=True)
            lines = result.stdout.split('\n')
            statistics = []
            for line in lines:
                parts = line.split()
                if len(parts) < 11:
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
            return statistics
        except Exception as e:
            if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                raise RuntimeError(f"获取 {command} 输出信息时发生未知错误: {str(e)}") from e
            else:
                raise RuntimeError(f"An unknown error occurred while retrieving the output information for {command} : {str(e)}") from e
    else:
        for host_config in SarConfig().get_config().public_config.remote_hosts:
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
                    command = f'sar -d'
                    if interval is not None:
                        command += f' {interval}'
                    if count is not None:
                        command += f' {count}'
                    stdin, stdout, stderr = ssh.exec_command(command, timeout = 20)
                    error = stderr.read().decode().strip()
                    output = stdout.read().decode().strip()

                    if error:
                        if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                            raise ValueError(f"执行命令 {command} 错误：{error}")
                        else:
                            raise ValueError(f"Executing command {command} error: {error}")

                    if not output:
                        if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                            raise ValueError("未能获取信息")
                        else:
                            raise ValueError("No information obtained")
                    
                    lines = output.split('\n')
                    statistics = []
                    for line in lines:
                        parts = line.split()
                        if len(parts) < 11:
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
                    return statistics
                except paramiko.AuthenticationException:
                    raise ValueError("SSH认证失败，请检查用户名和密码")
                except paramiko.SSHException as e:
                    raise ValueError(f"SSH连接错误: {str(e)}")
                except Exception as e:
                    raise ValueError(f"远程执行 {command} 失败: {str(e)}")
                finally:
                    # 确保SSH连接关闭
                    if ssh is not None:
                        try:
                            ssh.close()
                        except Exception:
                            pass
        if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise ValueError(f"未找到远程主机: {host}")
        else:
            raise ValueError(f"Remote host not found: {host}")

@mcp.tool(
    name="sar_network_collect_tool"
    if SarConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "sar_network_collect_tool",
    description='''
    使用sar命令分析网络设备的吞吐率
    1. 输入值如下：
        - host: 远程主机名称或IP地址，若不提供则对本机进行分析
        - interval: 监控的时间间隔
        - count: 监控次数
    2. 返回值为包含相应信息的字典列表，每个字典包含以下键
        - timestamp: 采集指标的时间
        - iface: 网络接口名称
        - rxpck_s: 每秒接收的数据包数量
        - txpck_s: 每秒发送的数据包数量
        - rxkB_s: 每秒接收的数据量（单位 KB/s)
        - txkB_s: 每秒发送的数据量（单位 KB/s)
        - rxcmp_s: ​每秒接收的压缩数据包数
        - txcmp_s: ​每秒发送的压缩数据包数
        - rxmcst_s: 每秒接收的多播数据包数
        - ifutil: 网络接口带宽利用率（百分比）
    '''
    if SarConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    '''
    Using the sar command to analyze the throughput of network devices
    1. The input values are as follows:
        - host: The name or IP address of the remote host; if not provided, the analysis is performed on the local machine.
        - interval: The monitoring time interval.
        - count: The number of monitoring instances.
    2. The return value is a list of dictionaries containing the corresponding information, with each dictionary including the following keys:
        - timestamp: The time when the metrics were collected.
        - iface: The name of the network interface.
        - rxpck_s: The number of packets received per second.
        - txpck_s: The number of packets sent per second.
        - rxkB_s: The amount of data received per second (in KB/s).
        - txkB_s: The amount of data sent per second (in KB/s).
        - rxcmp_s: The number of compressed packets received per second.
        - txcmp_s: The number of compressed packets sent per second.
        - rxmcst_s: The number of multicast packets received per second.
        - ifutil: The bandwidth utilization of the network interface (in percentage).
    '''

)
def sar_network_collect_tool(host: Union[str, None] = None, interval: int = None, count: int = None) -> List[Dict[str, Any]]:
    """使用sar命令分析网络设备的吞吐率"""
    if host is None:
        try:
            command = ['sar', '-n', 'DEV']
            if interval is not None:
                command.append(str(interval))
            if count is not None:
                command.append(str(count))
            result = subprocess.run(command, capture_output=True, text=True)
            lines = result.stdout.split('\n')
            statistics = []
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
            return statistics
        except Exception as e:
            if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                raise RuntimeError(f"获取 {command} 输出信息时发生未知错误: {str(e)}") from e
            else:
                raise RuntimeError(f"An unknown error occurred while retrieving the output information for {command} : {str(e)}") from e
    else:
        for host_config in SarConfig().get_config().public_config.remote_hosts:
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
                    command = f'sar -n DEV'
                    if interval is not None:
                        command += f' {interval}'
                    if count is not None:
                        command += f' {count}'
                    stdin, stdout, stderr = ssh.exec_command(command, timeout = 20)
                    error = stderr.read().decode().strip()
                    output = stdout.read().decode().strip()

                    if error:
                        if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                            raise ValueError(f"执行命令 {command} 错误：{error}")
                        else:
                            raise ValueError(f"Executing command {command} error: {error}")

                    if not output:
                        if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                            raise ValueError("未能获取信息")
                        else:
                            raise ValueError("No information obtained")
                    
                    lines = output.split('\n')
                    statistics = []
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
                    return statistics
                except paramiko.AuthenticationException:
                    raise ValueError("SSH认证失败，请检查用户名和密码")
                except paramiko.SSHException as e:
                    raise ValueError(f"SSH连接错误: {str(e)}")
                except Exception as e:
                    raise ValueError(f"远程执行 {command} 失败: {str(e)}")
                finally:
                    # 确保SSH连接关闭
                    if ssh is not None:
                        try:
                            ssh.close()
                        except Exception:
                            pass
        if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise ValueError(f"未找到远程主机: {host}")
        else:
            raise ValueError(f"Remote host not found: {host}")


@mcp.tool(
    name="sar_cpu_historicalinfo_collect_tool"
    if SarConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "sar_cpu_historicalinfo_collect_tool",
    description='''
    使用sar命令进行历史状态分析，排查过去某时段cpu的性能问题
    1. 输入值如下：
        - host: 远程主机名称或IP地址，若不提供则对本机进行分析
        - file: sar要分析的log文件
        - starttime: 分析开始的时间点
        - endtime: 分析结束的时间点
    2. 返回值为包含相应信息的字典列表，每个字典包含以下键
        - timestamp: 采集指标的时间
        - user: 用户空间程序占用CPU的百分比
        - nice: 低优先级用户进程占用的CPU百分比
        - system: 内核空间程序占用CPU的百分比
        - iowait: CPU等待磁盘I/O操作的时间百分比
        - steal: 虚拟化环境中，其他虚拟机占用的CPU时间百分比
        - idle:CPU空闲时间百分比
    '''
    if SarConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    '''
    Use the sar command for historical status analysis to investigate CPU performance issues during a specific past period:
    1. Input values are as follows:
        - host: The name or IP address of the remote host; if not provided, analysis is performed on the local machine.
        - file: The log file that sar is to analyze.
        - starttime: The starting point of the analysis.
        - endtime: The endpoint of the analysis.
    2. The return value is a list of dictionaries containing the corresponding information, each dictionary includes the following keys:
        - timestamp: The time when the metrics were collected.
        - user: The percentage of CPU used by user space programs.
        - nice: The percentage of CPU used by low-priority user processes.
        - system: The percentage of CPU used by kernel space programs.
        - iowait: The percentage of time the CPU spends waiting for disk I/O operations.
        - steal: In a virtualized environment, the percentage of CPU time used by other virtual machines.
        - idle: The percentage of CPU idle time.
    '''

)
def sar_cpu_historicalinfo_collect_tool(host: Union[str, None] = None, file: str = None, starttime: str = None, endtime: str = None) -> List[Dict[str, Any]]:
    """使用sar命令进行历史状态分析，排查过去某时段cpu的性能问题"""
    if host is None:
        try:
            command = ['sar', '-u']
            command.append('-f')
            if not os.path.isfile(file):
                if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                    raise ValueError(f"文件 {file} 不存在")
                else:
                    raise ValueError(f"File {file} does not exist")
            command.append(file)
            command.append('-s')
            command.append(starttime)
            command.append('-e')
            command.append(endtime)
            try:
                datetime.strptime(starttime, "%H:%M:%S")
                datetime.strptime(endtime, "%H:%M:%S")
            except ValueError:
                if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                    raise ValueError("时间格式错误，应为HH:MM:SS")
                else:
                    raise ValueError("Time format error, should be HH:MM:SS")
            start_dt = datetime.strptime(starttime, '%H:%M:%S').time()
            end_dt = datetime.strptime(endtime, '%H:%M:%S').time()
            if start_dt >= end_dt:
                if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                    raise ValueError("开始时间必须早于结束时间")
                else:
                    raise ValueError("Start time must be earlier than end time")
            result = subprocess.run(command, capture_output=True, text=True)
            lines = result.stdout.split('\n')
            statistics = []
            for line in lines:
                parts = line.split()
                if len(parts) < 9:
                    # 表头/空行和Avg行跳过
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
            return statistics
        except Exception as e:
            if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                raise RuntimeError(f"获取 {command} 输出信息时发生未知错误: {str(e)}") from e
            else:
                raise RuntimeError(f"An unknown error occurred while retrieving the output information for {command} : {str(e)}") from e
    else:
        for host_config in SarConfig().get_config().public_config.remote_hosts:
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
                    command = f'sar -u -f {file} -s {starttime} -e {endtime}'
                    try:
                        datetime.strptime(starttime, "%H:%M:%S")
                        datetime.strptime(endtime, "%H:%M:%S")
                    except ValueError:
                        if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                            raise ValueError("时间格式错误，应为HH:MM:SS")
                        else:
                            raise ValueError("Time format error, should be HH:MM:SS")
                    start_dt = datetime.strptime(starttime, '%H:%M:%S').time()
                    end_dt = datetime.strptime(endtime, '%H:%M:%S').time()
                    if start_dt >= end_dt:
                        if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                            raise ValueError("开始时间必须早于结束时间")
                        else:
                            raise ValueError("Start time must be earlier than end time")
                    stdin, stdout, stderr = ssh.exec_command(command, timeout = 20)
                    error = stderr.read().decode().strip()
                    output = stdout.read().decode().strip()

                    if error:
                        if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                            raise ValueError(f"命令 {command} 错误：{error}")
                        else:
                            raise ValueError(f"Command {command} error: {error}")

                    if not output:
                        if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                            raise ValueError("未能获取信息")
                        else:
                            raise ValueError("No information obtained")
                    
                    lines = output.split('\n')
                    statistics = []
                    for line in lines:
                        parts = line.split()
                        if len(parts) < 9:
                            # 表头/空行和Avg行跳过
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
                    return statistics
                except paramiko.AuthenticationException:
                    raise ValueError("SSH认证失败，请检查用户名和密码")
                except paramiko.SSHException as e:
                    raise ValueError(f"SSH连接错误: {str(e)}")
                except Exception as e:
                    raise ValueError(f"远程执行 {command} 失败: {str(e)}")
                finally:
                    # 确保SSH连接关闭
                    if ssh is not None:
                        try:
                            ssh.close()
                        except Exception:
                            pass
        if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise ValueError(f"未找到远程主机: {host}")
        else:
            raise ValueError(f"Remote host not found: {host}")

@mcp.tool(
    name="sar_memory_historicalinfo_collect_tool"
    if SarConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "sar_memory_historicalinfo_collect_tool",
    description='''
    使用sar命令进行历史状态分析，排查过去某时段内存的性能问题
    1. 输入值如下：
        - host: 远程主机名称或IP地址，若不提供则对本机进行分析
        - file: sar要分析的log文件
        - starttime: 分析开始的时间点
        - endtime: 分析结束的时间点
    2. 返回值为包含相应信息的字典列表，每个字典包含以下键
        - timestamp: 采集指标的时间
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
    '''
    if SarConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    '''
    Using the sar command for historical status analysis to troubleshoot performance issues over a past period:
    1. Input values are as follows:
        - host: The name or IP address of the remote host; if not provided, analysis is performed on the local machine.
        - device: The aspect of the status to be analyzed (CPU, memory, disk, etc.).
        - file: The log file that sar is to analyze.
        - starttime: The starting point of the analysis.
        - endtime: The endpoint of the analysis.
    2. The return value is a list of dictionaries containing the corresponding information, each dictionary includes the following keys:
        - timestamp: The time when the metrics were collected.
        - kbmemfree: Physical free memory (unused memory)
        - kbavail: Actual available memory (including reclaimable parts of cache and buffers)
        - kbmemused: Used physical memory (excluding kernel cache and buffers)
        - memused: Percentage of used memory relative to total physical memory (percentage)
        - kbbuffers: Memory used by kernel buffers (used for block device read/write caching)
        - kbcached: Memory used by kernel cache (used for file system caching)
        - kbcommit: Total memory required for the current workload (including used and estimated)
        - commit: Percentage of `kbcommit` relative to the system's total available memory (physical memory + Swap) (percentage)
        - kbactive: Active memory (recently accessed memory, not easily reclaimable)
        - kbinact: Inactive memory (less recently accessed memory, reclaimable for new processes)
        - kbdirty: Amount of dirty data waiting to be written to disk (unit: KB)
    '''

)
def sar_memory_historicalinfo_collect_tool(host: Union[str, None] = None, file: str = None, starttime: str = None, endtime: str = None) -> List[Dict[str, Any]]:
    """使用sar命令进行历史状态分析，排查过去某时段内存的性能问题"""
    if host is None:
        try:
            command = ['sar', '-r']
            command.append(device)
            command.append('-f')
            if not os.path.isfile(file):
                if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                    raise ValueError(f"文件 {file} 不存在")
                else:
                    raise ValueError(f"File {file} does not exist")
            command.append(file)
            command.append('-s')
            command.append(starttime)
            command.append('-e')
            command.append(endtime)
            try:
                datetime.strptime(starttime, "%H:%M:%S")
                datetime.strptime(endtime, "%H:%M:%S")
            except ValueError:
                if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                    raise ValueError("时间格式错误，应为HH:MM:SS")
                else:
                    raise ValueError("Time format error, should be HH:MM:SS")
            start_dt = datetime.strptime(starttime, '%H:%M:%S').time()
            end_dt = datetime.strptime(endtime, '%H:%M:%S').time()
            if start_dt >= end_dt:
                if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                    raise ValueError("开始时间必须早于结束时间")
                else:
                    raise ValueError("Start time must be earlier than end time")
            result = subprocess.run(command, capture_output=True, text=True)
            lines = result.stdout.split('\n')
            statistics = []
            for line in lines:
                parts = line.split()
                if len(parts) < 13:
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
            return statistics
        except Exception as e:
            if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                raise RuntimeError(f"获取 {command} 输出信息时发生未知错误: {str(e)}") from e
            else:
                raise RuntimeError(f"An unknown error occurred while retrieving the output information for {command} : {str(e)}") from e
    else:
        for host_config in SarConfig().get_config().public_config.remote_hosts:
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
                    command = f'sar -r -f {file} -s {starttime} -e {endtime}'
                    try:
                        datetime.strptime(starttime, "%H:%M:%S")
                        datetime.strptime(endtime, "%H:%M:%S")
                    except ValueError:
                        if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                            raise ValueError("时间格式错误，应为HH:MM:SS")
                        else:
                            raise ValueError("Time format error, should be HH:MM:SS")
                    start_dt = datetime.strptime(starttime, '%H:%M:%S').time()
                    end_dt = datetime.strptime(endtime, '%H:%M:%S').time()
                    if start_dt >= end_dt:
                        if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                            raise ValueError("开始时间必须早于结束时间")
                        else:
                            raise ValueError("Start time must be earlier than end time")
                    stdin, stdout, stderr = ssh.exec_command(command, timeout = 20)
                    error = stderr.read().decode().strip()
                    output = stdout.read().decode().strip()

                    if error:
                        if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                            raise ValueError(f"命令 {command} 错误：{error}")
                        else:
                            raise ValueError(f"Command {command} error: {error}")

                    if not output:
                        if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                            raise ValueError("未能获取信息")
                        else:
                            raise ValueError("No information obtained")
                    
                    lines = output.split('\n')
                    statistics = []
                    for line in lines:
                        parts = line.split()
                        if len(parts) < 13:
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
                    return statistics
                except paramiko.AuthenticationException:
                    raise ValueError("SSH认证失败，请检查用户名和密码")
                except paramiko.SSHException as e:
                    raise ValueError(f"SSH连接错误: {str(e)}")
                except Exception as e:
                    raise ValueError(f"远程执行 {command} 失败: {str(e)}")
                finally:
                    # 确保SSH连接关闭
                    if ssh is not None:
                        try:
                            ssh.close()
                        except Exception:
                            pass
        if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise ValueError(f"未找到远程主机: {host}")
        else:
            raise ValueError(f"Remote host not found: {host}")

@mcp.tool(
    name="sar_disk_historicalinfo_collect_tool"
    if SarConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "sar_disk_historicalinfo_collect_tool",
    description='''
    使用sar命令进行历史状态分析，排查过去某时段磁盘的性能问题
    1. 输入值如下：
        - host: 远程主机名称或IP地址，若不提供则对本机进行分析
        - file: sar要分析的log文件
        - starttime: 分析开始的时间点
        - endtime: 分析结束的时间点
    2. 返回值为包含相应信息的字典列表，每个字典包含以下键
        - timestamp: 采集指标的时间
        - name: 磁盘设备名称
        - tps: 每秒传输次数（IOPS）
        - rkB_s: 每秒读取的数据量（单位 KB/s）
        - wkB_s: 每秒写入的数据量（单位 KB/s）
        - dkB_s: 每秒丢弃的数据量（单位 KB/s）
        - areq-sz: 平均每次 I/O 请求的数据大小（单位 KB）
        - aqu-sz: 平均 I/O 请求队列长度
        - await: 平均每次 I/O 请求的等待时间（单位 毫秒）
        - util: 设备带宽利用率（百分比）
    '''
    if SarConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    '''
    Use the sar command for historical status analysis to troubleshoot disk performance issues during a specific past period:
    1. Input values are as follows:
        - host: The name or IP address of the remote host; if not provided, analysis is performed on the local machine.
        - file: The log file that sar is to analyze.
        - starttime: The starting point of the analysis.
        - endtime: The endpoint of the analysis.
    2. The return value is a list of dictionaries containing the corresponding information, each dictionary includes the following keys:
        - timestamp: The time when the metrics were collected.
        - name: Disk device name
        - tps: Transactions per second (IOPS)
        - rkB_s: Data read per second (unit: KB/s)
        - wkB_s: Data written per second (unit: KB/s)
        - dkB_s: Data discarded per second (unit: KB/s)
        - areq-sz: Average data size per I/O request (unit: KB)
        - aqu-sz: Average I/O request queue length
        - await: Average wait time per I/O request (unit: milliseconds)
        - util: Device bandwidth utilization (percentage)
    '''

)
def sar_disk_historicalinfo_collect_tool(host: Union[str, None] = None, file: str = None, starttime: str = None, endtime: str = None) -> List[Dict[str, Any]]:
    """使用sar命令进行历史状态分析，排查过去某时段磁盘的性能问题"""
    if host is None:
        try:
            command = ['sar', '-d']
            command.append('-f')
            if not os.path.isfile(file):
                if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                    raise ValueError(f"文件 {file} 不存在")
                else:
                    raise ValueError(f"File {file} does not exist")
            command.append(file)
            command.append('-s')
            command.append(starttime)
            command.append('-e')
            command.append(endtime)
            try:
                datetime.strptime(starttime, "%H:%M:%S")
                datetime.strptime(endtime, "%H:%M:%S")
            except ValueError:
                if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                    raise ValueError("时间格式错误，应为HH:MM:SS")
                else:
                    raise ValueError("Time format error, should be HH:MM:SS")
            start_dt = datetime.strptime(starttime, '%H:%M:%S').time()
            end_dt = datetime.strptime(endtime, '%H:%M:%S').time()
            if start_dt >= end_dt:
                if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                    raise ValueError("开始时间必须早于结束时间")
                else:
                    raise ValueError("Start time must be earlier than end time")
            result = subprocess.run(command, capture_output=True, text=True)
            lines = result.stdout.split('\n')
            statistics = []
            for line in lines:
                parts = line.split()
                if len(parts) < 11:
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
            return statistics
        except Exception as e:
            if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                raise RuntimeError(f"获取 {command} 输出信息时发生未知错误: {str(e)}") from e
            else:
                raise RuntimeError(f"An unknown error occurred while retrieving the output information for {command} : {str(e)}") from e
    else:
        for host_config in SarConfig().get_config().public_config.remote_hosts:
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
                    command = f'sar -d -f {file} -s {starttime} -e {endtime}'
                    try:
                        datetime.strptime(starttime, "%H:%M:%S")
                        datetime.strptime(endtime, "%H:%M:%S")
                    except ValueError:
                        if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                            raise ValueError("时间格式错误，应为HH:MM:SS")
                        else:
                            raise ValueError("Time format error, should be HH:MM:SS")
                    start_dt = datetime.strptime(starttime, '%H:%M:%S').time()
                    end_dt = datetime.strptime(endtime, '%H:%M:%S').time()
                    if start_dt >= end_dt:
                        if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                            raise ValueError("开始时间必须早于结束时间")
                        else:
                            raise ValueError("Start time must be earlier than end time")
                    stdin, stdout, stderr = ssh.exec_command(command, timeout = 20)
                    error = stderr.read().decode().strip()
                    output = stdout.read().decode().strip()

                    if error:
                        if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                            raise ValueError(f"命令 {command} 错误：{error}")
                        else:
                            raise ValueError(f"Command {command} error: {error}")

                    if not output:
                        if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                            raise ValueError("未能获取信息")
                        else:
                            raise ValueError("No information obtained")
                    
                    lines = output.split('\n')
                    statistics = []
                    for line in lines:
                        parts = line.split()
                        if len(parts) < 11:
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
                    return statistics
                except paramiko.AuthenticationException:
                    raise ValueError("SSH认证失败，请检查用户名和密码")
                except paramiko.SSHException as e:
                    raise ValueError(f"SSH连接错误: {str(e)}")
                except Exception as e:
                    raise ValueError(f"远程执行 {command} 失败: {str(e)}")
                finally:
                    # 确保SSH连接关闭
                    if ssh is not None:
                        try:
                            ssh.close()
                        except Exception:
                            pass
        if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise ValueError(f"未找到远程主机: {host}")
        else:
            raise ValueError(f"Remote host not found: {host}")

@mcp.tool(
    name="sar_network_historicalinfo_collect_tool"
    if SarConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "sar_network_historicalinfo_collect_tool",
    description='''
    使用sar命令进行历史状态分析，排查过去某时段的网络吞吐性能问题
    1. 输入值如下：
        - host: 远程主机名称或IP地址，若不提供则对本机进行分析
        - file: sar要分析的log文件
        - starttime: 分析开始的时间点
        - endtime: 分析结束的时间点
    2. 返回值为包含相应信息的字典列表，每个字典包含以下键
        - timestamp: 采集指标的时间
        - iface: 网络接口名称
        - rxpck_s: 每秒接收的数据包数量
        - txpck_s: 每秒发送的数据包数量
        - rxkB_s: 每秒接收的数据量（单位 KB/s)
        - txkB_s: 每秒发送的数据量（单位 KB/s)
        - rxcmp_s: ​每秒接收的压缩数据包数
        - txcmp_s: ​每秒发送的压缩数据包数
        - rxmcst_s: 每秒接收的多播数据包数
        - ifutil: 网络接口带宽利用率（百分比）
    '''
    if SarConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    '''
    Using the sar command for historical status analysis to troubleshoot network throughput performance issues over a past period:
    1. Input values are as follows:
        - host: The name or IP address of the remote host; if not provided, analysis is performed on the local machine.
        - file: The log file that sar is to analyze.
        - starttime: The starting point of the analysis.
        - endtime: The ending point of the analysis.
    2. The return value is a list of dictionaries containing the corresponding information, with each dictionary including the following keys:
        - timestamp: The time when the metrics were collected.
        - iface: The name of the network interface.
        - rxpck_s: The number of packets received per second.
        - txpck_s: The number of packets sent per second.
        - rxkB_s: The amount of data received per second (in KB/s).
        - txkB_s: The amount of data sent per second (in KB/s).
        - rxcmp_s: The number of compressed packets received per second.
        - txcmp_s: The number of compressed packets sent per second.
        - rxmcst_s: The number of multicast packets received per second.
        - ifutil: The bandwidth utilization of the network interface (in percentage).
    '''

)
def sar_network_historicalinfo_collect_tool(host: Union[str, None] = None, file: str = None, starttime: str = None, endtime: str = None) -> List[Dict[str, Any]]:
    """使用sar命令进行历史状态分析，排查过去某时段的网络吞吐性能问题"""
    if host is None:
        try:
            command = ['sar', '-n', 'DEV']
            command.append('-f')
            if not os.path.isfile(file):
                if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                    raise ValueError(f"文件 {file} 不存在")
                else:
                    raise ValueError(f"File {file} does not exist")
            command.append(file)
            command.append('-s')
            command.append(starttime)
            command.append('-e')
            command.append(endtime)
            try:
                datetime.strptime(starttime, "%H:%M:%S")
                datetime.strptime(endtime, "%H:%M:%S")
            except ValueError:
                if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                    raise ValueError("时间格式错误，应为HH:MM:SS")
                else:
                    raise ValueError("Time format error, should be HH:MM:SS")
            start_dt = datetime.strptime(starttime, '%H:%M:%S').time()
            end_dt = datetime.strptime(endtime, '%H:%M:%S').time()
            if start_dt >= end_dt:
                if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                    raise ValueError("开始时间必须早于结束时间")
                else:
                    raise ValueError("Start time must be earlier than end time")
            result = subprocess.run(command, capture_output=True, text=True)
            lines = result.stdout.split('\n')
            statistics = []
            for line in lines:
                parts = line.split()
                if len(parts) < 11:
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
            return statistics
        except Exception as e:
            if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                raise RuntimeError(f"获取 {command} 输出信息时发生未知错误: {str(e)}") from e
            else:
                raise RuntimeError(f"An unknown error occurred while retrieving the output information for {command} : {str(e)}") from e
    else:
        for host_config in SarConfig().get_config().public_config.remote_hosts:
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
                    command = f'sar -n DEV -f {file} -s {starttime} -e {endtime}'
                    try:
                        datetime.strptime(starttime, "%H:%M:%S")
                        datetime.strptime(endtime, "%H:%M:%S")
                    except ValueError:
                        if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                            raise ValueError("时间格式错误，应为HH:MM:SS")
                        else:
                            raise ValueError("Time format error, should be HH:MM:SS")
                    start_dt = datetime.strptime(starttime, '%H:%M:%S').time()
                    end_dt = datetime.strptime(endtime, '%H:%M:%S').time()
                    if start_dt >= end_dt:
                        if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                            raise ValueError("开始时间必须早于结束时间")
                        else:
                            raise ValueError("Start time must be earlier than end time")
                    stdin, stdout, stderr = ssh.exec_command(command, timeout = 20)
                    error = stderr.read().decode().strip()
                    output = stdout.read().decode().strip()

                    if error:
                        if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                            raise ValueError(f"命令 {command} 错误：{error}")
                        else:
                            raise ValueError(f"Command {command} error: {error}")

                    if not output:
                        if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
                            raise ValueError("未能获取信息")
                        else:
                            raise ValueError("No information obtained")
                    
                    lines = output.split('\n')
                    statistics = []
                    for line in lines:
                        parts = line.split()
                        if len(parts) < 11:
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
                    return statistics
                except paramiko.AuthenticationException:
                    raise ValueError("SSH认证失败，请检查用户名和密码")
                except paramiko.SSHException as e:
                    raise ValueError(f"SSH连接错误: {str(e)}")
                except Exception as e:
                    raise ValueError(f"远程执行 {command} 失败: {str(e)}")
                finally:
                    # 确保SSH连接关闭
                    if ssh is not None:
                        try:
                            ssh.close()
                        except Exception:
                            pass
        if SarConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise ValueError(f"未找到远程主机: {host}")
        else:
            raise ValueError(f"Remote host not found: {host}")

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='sse')
