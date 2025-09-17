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
from config.private.vmstat.config_loader import VmstatConfig
mcp = FastMCP("Vmstat MCP Server", host="0.0.0.0", port=VmstatConfig().get_config().private_config.port)


@mcp.tool(
    name="vmstat_collect_tool"
    if VmstatConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "vmstat_collect_tool",
    description='''
    使用vmstat命令快速诊断系统资源交互瓶颈
    1. 输入值如下：
        - host: 远程主机名称或IP地址，若不提供则表示监控本机系统资源整体状态
    2. 返回值为包含识别性能瓶颈指标的字典列表，每个字典包含以下键
        - r: 运行队列中的进程数
        - b: 等待 I/O 的进程数
        - si: 每秒从磁盘加载到内存的数据量（单位KB/s）
        - so: 每秒从内存换出到磁盘的数据量（单位KB/s）
        - bi: 从磁盘读取的块数
        - bo: 写入磁盘的块数
        - in: 每秒发生的中断次数，包括时钟中断
        - cs: 每秒上下文切换次数
        - us: 用户进程消耗 CPU 时间
        - sy: 内核进程消耗 CPU 时间
        - id: CPU 空闲时间
        - wa: CPU 等待 I/O 完成的时间百分比
        - st: 被虚拟机偷走的 CPU 时间百分比
    '''
    if VmstatConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    '''
    Using the vmstat Command to Quickly Diagnose System Resource Interaction Bottlenecks
    1. Input values are as follows:
        - host: The name or IP address of the remote host. If not provided, it indicates monitoring the overall status of the local system resources.
    2. The return value is a list of dictionaries containing indicators that identify performance bottlenecks. Each dictionary includes the following keys:
        - r: The number of processes in the run queue.
        - b: The number of processes waiting for I/O.
        - si: The amount of data loaded from disk to memory per second (in KB/s).
        - so: The amount of data swapped from memory to disk per second (in KB/s).
        - bi: The number of blocks read from disk.
        - bo: The number of blocks written to disk.
        - in: The number of interrupts per second, including clock interrupts.
        - cs: The number of context switches per second.
        - us: The CPU time consumed by user processes.
        - sy: The CPU time consumed by kernel processes.
        - id: The CPU idle time.
        - wa: The percentage of CPU time waiting for I/O to complete.
        - st: The percentage of CPU time stolen by virtual machines.
    '''

)
def vmstat_collect_tool(host: Union[str, None] = None, options: str = None) -> Dict[str, Any]:
    """使用vmstat命令快速诊断系统资源交互瓶颈"""
    if host is None:
        try:
            command = ['vmstat']
            result = subprocess.run(command, capture_output=True, text=True)
            lines = result.stdout.split('\n')
            if len(lines) < 3:
                if VmstatConfig().get_config().public_config.language == LanguageEnum.ZH:
                    raise ValueError(f"{command} 命令输出格式不正确")
                else:
                    raise ValueError(f"{command} command output format is incorrect")
            parts = lines[2].split()
            if len(parts) < 17:
                if VmstatConfig().get_config().public_config.language == LanguageEnum.ZH:
                    raise ValueError(f"{command} 命令输出字段不足，无法提取所需信息")
                else:
                    raise ValueError(f"{command} command output fields are insufficient, cannot extract required information")
            vmstat_output = {
                'r': int(parts[0]),
                'b': int(parts[1]),
                'si': int(parts[6]),
                'so': int(parts[7]),
                'bi': int(parts[8]),
                'bo': int(parts[9]),
                'in': int(parts[10]),
                'cs': int(parts[11]),
                'us': int(parts[12]),
                'sy': int(parts[13]),
                'id': int(parts[14]),
                'wa': int(parts[15]),
                'st': int(parts[16])
            }
            return vmstat_output
        except Exception as e:
            if VmstatConfig().get_config().public_config.language == LanguageEnum.ZH:
                raise RuntimeError(f"获取 {command} 输出信息时发生未知错误: {str(e)}") from e
            else:
                raise RuntimeError(f"An unknown error occurred while retrieving the output information for {command} : {str(e)}") from e
    else:
        for host_config in VmstatConfig().get_config().public_config.remote_hosts:
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
                    command = 'vmstat'
                    stdin, stdout, stderr = ssh.exec_command(command, timeout = 10)
                    error = stderr.read().decode().strip()
                    output = stdout.read().decode().strip()

                    if error:
                        if VmstatConfig().get_config().public_config.language == LanguageEnum.ZH:
                            raise ValueError(f"执行命令 {command} 错误：{error}")
                        else:
                            raise ValueError(f"Executing command {command} error: {error}")

                    if not output:
                        if VmstatConfig().get_config().public_config.language == LanguageEnum.ZH:
                            raise ValueError(f"未能获取 {command} 输出信息")
                        else:
                            raise ValueError(f"Failed to get {command} output information")
                    
                    lines = output.split('\n')
                    if len(lines) < 3:
                        if VmstatConfig().get_config().public_config.language == LanguageEnum.ZH:
                            raise ValueError(f"{command} 命令输出格式不正确")
                        else:
                            raise ValueError(f"{command} command output format is incorrect")

                    parts = lines[2].split()
                    if len(parts) < 17:
                        if VmstatConfig().get_config().public_config.language == LanguageEnum.ZH:
                            raise ValueError(f"{command} 命令输出字段不足，无法提取所需信息")
                        else:
                            raise ValueError(f"{command} command output fields are insufficient, cannot extract required information")

                    vmstat_output = {
                        'r': int(parts[0]),
                        'b': int(parts[1]),
                        'si': int(parts[6]),
                        'so': int(parts[7]),
                        'bi': int(parts[8]),
                        'bo': int(parts[9]),
                        'in': int(parts[10]),
                        'cs': int(parts[11]),
                        'us': int(parts[12]),
                        'sy': int(parts[13]),
                        'id': int(parts[14]),
                        'wa': int(parts[15]),
                        'st': int(parts[16])
                    }
                    return vmstat_output
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
        if VmstatConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise ValueError(f"未找到远程主机: {host}")
        else:
            raise ValueError(f"Remote host not found: {host}")

@mcp.tool(
    name="vmstat_slabinfo_collect_tool"
    if VmstatConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "vmstat_slabinfo_collect_tool",
    description='''
    使用vmstat命令收集slab相关信息
    1. 输入值如下：
        - host: 远程主机名称或IP地址，若不提供则表示获取本机的slab相关信息
    2. 返回值为包含slab内存占用情况的字典列表，每个字典包含以下键
        - cache: 内核中slab缓存名称
        - num: 当前活跃的缓存对象数量
        - total: 该缓存的总对象数量
        - size: 每个缓存对象的大小
        - pages: 每个slab中包含的缓存对象数量
    '''
    if VmstatConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    '''
    Using the vmstat command to collect slab-related information
    1. The input values are as follows:
        - host: The name or IP address of the remote host. If not provided, it indicates that the slab-related information of the local machine is to be retrieved.
    2. The return value is a list of dictionaries containing slab memory usage information. Each dictionary includes the following keys:
        - cache: The name of the slab cache in the kernel.
        - num: The number of currently active cache objects.
        - total: The total number of objects in the cache.
        - size: The size of each cache object.
        - pages: The number of cache objects contained in each slab.
    '''

)
def vmstat_slabinfo_collect_tool(host: Union[str, None] = None) -> List[Dict[str, Any]]:
    """使用vmstat命令收集slab相关信息"""
    if host is None:
        try:
            command = ['vmstat', '-m']
            result = subprocess.run(command, capture_output=True, text=True)
            lines = result.stdout.split('\n')
            vmstat_output = []
            
            if len(lines) < 2:
                if VmstatConfig().get_config().public_config.language == LanguageEnum.ZH:
                    raise ValueError(f"{command} 命令输出格式不正确")
                else:
                    raise ValueError(f"{command} command output format is incorrect")
            for line in lines[1:-1]:
                parts = line.split()
                if len(parts) < 5:
                    if VmstatConfig().get_config().public_config.language == LanguageEnum.ZH:
                        raise ValueError(f"{command} 命令输出字段不足，无法提取所需信息")
                    else:
                        raise ValueError(f"{command} command output fields are insufficient, cannot extract required information")
                try:
                    num = int(parts[1])
                except ValueError:
                    # 遇到重复输出的表头行，选择跳过
                    continue
                vmstat_output.append({
                    'cache': parts[0],
                    'num': int(parts[1]),
                    'total': int(parts[2]),
                    'size': int(parts[3]),
                    'pages': int(parts[4])
                })
            return vmstat_output
        except Exception as e:
            if VmstatConfig().get_config().public_config.language == LanguageEnum.ZH:
                raise RuntimeError(f"获取 {command} 输出信息时发生未知错误: {str(e)}") from e
            else:
                raise RuntimeError(f"An unknown error occurred while retrieving the output information for {command} : {str(e)}") from e
    else:
        for host_config in VmstatConfig().get_config().public_config.remote_hosts:
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
                    command = 'vmstat -m'
                    stdin, stdout, stderr = ssh.exec_command(command, timeout = 20)
                    error = stderr.read().decode().strip()
                    output = stdout.read().decode().strip()

                    if error:
                        if VmstatConfig().get_config().public_config.language == LanguageEnum.ZH:
                            raise ValueError(f"执行命令 {command} 错误：{error}")
                        else:
                            raise ValueError(f"Executing command {command} error: {error}")

                    if not output:
                        if VmstatConfig().get_config().public_config.language == LanguageEnum.ZH:
                            raise ValueError(f"未能获取 {command} 输出信息")
                        else:
                            raise ValueError(f"Failed to get {command} output information")
                    
                    lines = output.split('\n')
                    vmstat_output = []
                    
                    if len(lines) < 2:
                        if VmstatConfig().get_config().public_config.language == LanguageEnum.ZH:
                            raise ValueError(f"{command} 命令输出格式不正确")
                        else:
                            raise ValueError(f"{command} command output format is incorrect")
                    for line in lines[1:-1]:
                        parts = line.split()
                        if len(parts) < 5:
                            if VmstatConfig().get_config().public_config.language == LanguageEnum.ZH:
                                raise ValueError(f"{command} 命令输出字段不足，无法提取所需信息")
                            else:
                                raise ValueError(f"{command} command output fields are insufficient, cannot extract required information")
                        try:
                            num = int(parts[1])
                        except ValueError:
                            # 遇到重复输出的表头行，选择跳过
                            continue
                        vmstat_output.append({
                            'cache': parts[0],
                            'num': int(parts[1]),
                            'total': int(parts[2]),
                            'size': int(parts[3]),
                            'pages': int(parts[4])
                        })
                    return vmstat_output
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
        if VmstatConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise ValueError(f"未找到远程主机: {host}")
        else:
            raise ValueError(f"Remote host not found: {host}")

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='sse')
