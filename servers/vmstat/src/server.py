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
    使用vmstat命令快速诊断系统资源交互瓶颈
    1. 输入值如下：
        - host: 远程主机名称或IP地址，若不提供则表示获取本机的内存使用情况
        - options: vmstat命令后跟的具体选项
    2. 返回值为包含进程信息的字典列表，每个字典包含以下键
        当options为空时，返回系统资源交互情况
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
        当options为'-m'时，返回系统slab内存占用情况
            - cache: 内核中slab缓存名称
            - num: 当前活跃的缓存对象数量
            - total: 该缓存的总对象数量
            - size: 每个缓存对象的大小
            - pages: 每个slab中包含的缓存对象数量
    '''
    if TopConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    '''
    Using the vmstat Command to Quickly Diagnose System Resource Interaction Bottlenecks
    1. Input values are as follows:
        - host: The name or IP address of the remote host. If not provided, it indicates retrieving the memory usage of the local machine.
        - options: Specific options following the vmstat command.
    2. The return value is a list of dictionaries containing process information, each dictionary includes the following keys:
    When options are empty, the system resource interaction status is returned:
        - r: Number of processes in the run queue.
        - b: Number of processes waiting for I/O.
        - si: Amount of data loaded from disk to memory per second (unit: KB/s).
        - so: Amount of data swapped from memory to disk per second (unit: KB/s).
        - bi: Number of blocks read from disk.
        - bo: Number of blocks written to disk.
        - in: Number of interrupts per second, including clock interrupts.
        - cs: Number of context switches per second.
        - us: CPU time consumed by user processes.
        - sy: CPU time consumed by kernel processes.
        - id: CPU idle time.
        - wa: Percentage of CPU time waiting for I/O completion.
        - st: Percentage of CPU time stolen by virtual machines.
    When options are '-m', the system slab memory usage is returned:
        - cache: Name of the slab cache in the kernel.
        - num: Number of currently active cache objects.
        - total: Total number of objects in the cache.
        - size: Size of each cache object.
        - pages: Number of cache objects contained in each slab.
    '''

)
def vmstat_collect_tool(host: Union[str, None] = None, options: str = None) -> List[Dict[str, Any]]:
    """使用vmstat命令快速诊断系统资源交互瓶颈"""
    if host is None:
        try:
            command = ['vmstat']
            valid_options = {'-m'}
            if options is not None:
                if options not in valid_options:
                    raise ValueError(f"不支持的选项参数：{options}")
                else:
                    command.append(options)
            result = subprocess.run(command, capture_output=True, text=True)
            lines = result.stdout.split('\n')
            vmstat_output = []
            if options is None:
                if len(lines) < 3:
                    raise ValueError(f"{command} 命令输出格式不正确")
                parts = lines[2].split()
                if len(parts) < 17:
                    raise ValueError(f"{command} 命令输出字段不足，无法提取所需信息")
                vmstat_output = [{
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
                }]
                return vmstat_output
            elif options in valid_options:
                if len(lines) < 2:
                    raise ValueError(f"{command} 命令输出格式不正确")
                for line in lines[1:-1]:
                    parts = line.split()
                    if len(parts) < 5:
                        raise ValueError(f"{command} 命令输出字段不足，无法提取所需信息")
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
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"执行 {command} 命令失败: {e.stderr}") from e
        except Exception as e:
            raise RuntimeError(f"获取 {command} 输出信息时发生未知错误: {str(e)}") from e
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
                    command = 'vmstat'
                    valid_options = {'-m'}
                    if options:
                        if options not in valid_options:
                            raise ValueError(f"不支持的选项参数：{options}")
                        command += f' {options}'
                    stdin, stdout, stderr = ssh.exec_command(command, timeout = 20)
                    error = stderr.read().decode().strip()
                    output = stdout.read().decode().strip()

                    if error:
                        raise ValueError(f"Command {command} error: {error}")

                    if not output:
                        raise ValueError(f"未能获取 {command} 输出信息")
                    
                    lines = output.split('\n')
                    vmstat_output = []
                    if options is None:
                        if len(lines) < 3:
                            raise ValueError(f"{command} 命令输出格式不正确")
                        parts = lines[2].split()
                        if len(parts) < 17:
                            raise ValueError(f"{command} 命令输出字段不足，无法提取所需信息")
                        vmstat_output = [{
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
                        }]
                        return vmstat_output
                    elif options in valid_options:
                        if len(lines) < 2:
                            raise ValueError(f"{command} 命令输出格式不正确")
                        for line in lines[1:-1]:
                            parts = line.split()
                            if len(parts) < 5:
                                raise ValueError(f"{command} 命令输出字段不足，无法提取所需信息")
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
