from asyncio.log import logger
import logging
from typing import Union, List, Dict, Optional
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
from config.private.top.config_loader import TopCommandConfig

from cpu import get_cpu_metrics
from servers.top.src.base import create_base_result, get_server_auth
from servers.top.src.disk import get_disk_metrics
from servers.top.src.memory import get_memory_metrics
from servers.top.src.network import get_network_metrics
from servers.top.src.proc import get_process_metrics
from servers.top.src.ssh_connection import SSHConnection


mcp = FastMCP("Perf_Svg MCP Server", host="0.0.0.0", port=TopCommandConfig().get_config().private_config.port)


@mcp.tool(
    name="top_collect_tool"
    if TopCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "top_collect_tool",
    description="""
    使用top命令获取远端机器或者本机内存占用最多的k个进程
    1. 输入值如下：
        - host: 远程主机名称或IP地址，若不提供则表示获取本机的top k进程
        - k: 需要获取的进程数量，默认为5，可根据实际需求调整
    2. 返回值为包含进程信息的字典列表，每个字典包含以下键
        - pid: 进程ID
        - name: 进程名称
        - memory: 内存使用量（单位MB）
    """
    if TopCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    """
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
    """

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
        for host_config in TopCommandConfig().get_config().public_config.remote_hosts:
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
        if TopCommandConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise ValueError(f"未找到远程主机: {host}")
        else:
            raise ValueError(f"Remote host not found: {host}")


@mcp.tool(
    name="top_servers_tool"
    if TopCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "top_servers_tool",
    description="""
    获取服务器负载信息的主入口函数，支持多服务器、多维度、进程信息
    
    参数:
        -host: 服务器IP地址/主机名称，支持单个IP/主机名称字符串或IP/主机名称列表，可为None即本机
            示例: "192.168.1.100" 或 ["192.168.1.100", "192.168.1.101"]
        -dimensions: 监控维度列表，可选值：cpu、memory、disk、network
            默认为 ["cpu", "memory"]
        -include_processes: 是否返回Top N进程信息
            默认为False
        -top_n: 当include_processes为True时，返回的进程数量
            默认为5
    
    返回:
        服务器负载信息列表，每个元素包含：
        - server_info: 服务器基本信息（IP、状态、时间戳）
        - metrics: 各维度指标（仅包含请求的维度）
        - processes: 进程信息（仅当include_processes=True时存在）
        - error: 错误信息（仅当发生错误时存在）
    """
    if TopCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    """
    Main entry function for obtaining server load information, supporting multiple servers, 
    multiple dimensions, and process information
    
    Parameters:
        -host:  Server IP address/hostname, supports a single IP/hostname string or IP/hostname list, can be None for localhost.
            Example: "192.168.1.100" or ["192.168.1.100", "192.168.1.101"] or None(localhost)
        -dimensions: List of monitoring dimensions, optional values: cpu, memory, disk, network
            Default: ["cpu", "memory"]
        -include_processes: Whether to return Top N process information
            Default: False
        -top_n: Number of processes to return when include_processes is True
            Default: 5
    
    Returns:
        A list of server load information, where each element contains:
        - server_info: Basic server information (IP, status, timestamp)
        - metrics: Various dimension metrics (only includes requested dimensions)
        - processes: Process information (only present when include_processes=True)
        - error: Error information (only present when an error occurs)
    """
)
def top_servers_tool(
    host: Optional[Union[str, List[str]]] = None,
    dimensions: Optional[List[str]] = None,
    include_processes: bool = False,
    top_n: int = 5
) -> List[Dict]:
    # 标准化输入参数
    logger.info("into--------------------------")
    if host is None:
        logger.info("127.0.0.1")
        host_list = ["127.0.0.1"]
    else:
        host_list = [host] if isinstance(host, str) else host

    # 标准化监控维度
    valid_dimensions = {"cpu", "memory", "disk", "network"}
    dimensions = dimensions or ["cpu", "memory"]
    invalid_dims = [d for d in dimensions if d not in valid_dimensions]
    if invalid_dims:
        raise ValueError(
            f"无效的监控维度: {invalid_dims}，支持的维度: {sorted(valid_dimensions)}"
            if TopCommandConfig().get_config().public_config.language == LanguageEnum.ZH else
            ValueError(
                f"Invalid monitoring dimension: {invalid_dims}, supported dimensions: {sorted(valid_dimensions)}"))

    # 处理每个IP的负载采集
    results = []
    for ip in host_list:
        # 创建基础结果结构
        result = create_base_result(ip)

        try:
            # 获取服务器认证信息
            server_auth = get_server_auth(ip, TopCommandConfig().get_config().public_config.remote_hosts)
            # 本地服务器直接采集（无需SSH）
            if server_auth is None:
                # 采集指定维度指标
                is_local = True
                for dim in dimensions:
                    if dim == "cpu":
                        result["metrics"].update(get_cpu_metrics(is_local, None))
                    elif dim == "memory":
                        result["metrics"].update(get_memory_metrics(is_local, None))
                    elif dim == "disk":
                        result["metrics"].update(get_disk_metrics(is_local, None))
                    elif dim == "network":
                        result["metrics"].update(get_network_metrics(is_local, None))

                # 采集进程信息（如果需要）
                if include_processes:
                    result["metrics"].update(get_process_metrics(is_local, None, top_n))

                result["server_info"]["status"] = "online"

            # 远程服务器通过SSH采集
            else:
                # 使用SSH上下文管理器，自动处理连接生命周期
                with SSHConnection(
                    ip=server_auth.host,
                    port=server_auth.port,
                    username=server_auth.username,
                    password=server_auth.password,
                ) as (conn_success, conn_obj):
                    is_local = False
                    logger.info("into--------------------------SSH链接:%s", conn_success)
                    if not conn_success:
                        logger.info("into--------------------------SSH-offline")
                        result["server_info"]["status"] = "offline"
                        result["error"] = conn_obj
                        results.append(result)
                        continue
                    ssh_conn = conn_obj
                    if not isinstance(ssh_conn, paramiko.SSHClient):
                        # 可以选择抛出异常
                        logger.info("into--------------------------SSH-无效对象")
                        result["server_info"]["status"] = "error"
                        result["error"] = "无效的SSH连接对象" if TopCommandConfig().get_config(
                        ).public_config.language == LanguageEnum.ZH else "Invalid SSH connection object"
                        results.append(result)
                        return results
                    # 采集指定维度指标
                    logger.info("info-----------------choice dim")
                    for dim in dimensions:
                        logger.info("info-----------------choice %s", dim)
                        if dim == "cpu":
                            result["metrics"].update(get_cpu_metrics(is_local, ssh_conn))
                        elif dim == "memory":
                            result["metrics"].update(get_memory_metrics(is_local, ssh_conn))
                        elif dim == "disk":
                            result["metrics"].update(get_disk_metrics(is_local, ssh_conn))
                        elif dim == "network":
                            result["metrics"].update(get_network_metrics(is_local, ssh_conn))

                    # 采集进程信息（如果需要）
                    if include_processes:
                        result["metrics"].update(get_process_metrics(is_local, ssh_conn, top_n))

                    result["server_info"]["status"] = "online"

        except Exception as e:
            result["server_info"]["status"] = "server——error"
            result["error"] = str(e)

        results.append(result)

    return results


# 注册其他专用工具函数（按需扩展）
@mcp.tool(name="get_server_cpu", description="获取目标服务器的CPU指标"
          if TopCommandConfig().get_config().public_config.language == LanguageEnum.ZH else
          "Get CPU metrics of the target server")
def get_server_cpu(host: Union[str, List[str]]) -> List[Dict]:
    """专用工具：仅获取CPU指标"""
    return top_servers_tool(host, dimensions=["cpu"])


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='sse')
