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


def get_language_config() -> bool:
    """获取语言配置：True=中文，False=英文（避免重复调用配置）"""
    return TopCommandConfig().get_config().public_config.language == LanguageEnum.ZH

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
    if get_language_config() else "top_servers_tool",
    description="""
    获取单个服务器负载信息的工具函数，支持多维度、进程信息（多服务器需多次调用）
    
    参数:
        -host: 服务器IP地址/主机名称，可为None（None即表示本机127.0.0.1）
            示例: "192.168.1.100" 或 "localhost" 或 None
        -dimensions: 监控维度列表，可选值：cpu、memory、disk、network
            默认为 ["cpu", "memory"]
        -include_processes: 是否返回Top N进程信息
            默认为False
        -top_n: 当include_processes为True时，返回的进程数量
            默认为5
    
    返回:
        单个服务器负载信息字典，包含：
        - server_info: 服务器基本信息（IP、状态、时间戳）
        - metrics: 各维度指标（仅包含请求的维度）
        - processes: 进程信息（仅当include_processes=True时存在）
        - error: 错误信息（仅当发生错误时存在）
    """
    if get_language_config() else
    """
    Tool function for obtaining load information of a single server, supporting multiple dimensions and process information (multiple calls required for multiple servers)
    
    Parameters:
        -host: Server IP address/hostname, can be None (None means localhost 127.0.0.1)
            Example: "192.168.1.100" or "localhost" or None
        -dimensions: List of monitoring dimensions, optional values: cpu, memory, disk, network
            Default: ["cpu", "memory"]
        -include_processes: Whether to return Top N process information
            Default: False
        -top_n: Number of processes to return when include_processes is True
            Default: 5
    
    Returns:
        Single server load information dictionary, including:
        - server_info: Basic server information (IP, status, timestamp)
        - metrics: Various dimension metrics (only includes requested dimensions)
        - processes: Process information (only present when include_processes=True)
        - error: Error information (only present when an error occurs)
    """
)
def top_servers_tool(
    host: Optional[str] = None,
    dimensions: Optional[list[str]] = None,
    include_processes: bool = False,
    top_n: int = 5
) -> Dict:
    is_zh = get_language_config()
    # 1. 标准化输入：统一处理None/具体IP，明确当前监控的单个主机
    target_ip = "127.0.0.1" if host is None else host.strip()
    logger.info(f"开始处理单个服务器负载采集：{target_ip}（{'本机' if target_ip == '127.0.0.1' else '远程主机'}）")

    # 2. 标准化监控维度（保留原校验逻辑，确保输入有效）
    valid_dimensions = {"cpu", "memory", "disk", "network"}
    dimensions = dimensions or ["cpu", "memory"]
    invalid_dims = [d for d in dimensions if d not in valid_dimensions]
    if invalid_dims:
        err_msg = (
            f"无效的监控维度: {invalid_dims}，支持的维度: {sorted(valid_dimensions)}"
            if is_zh else
            f"Invalid monitoring dimension: {invalid_dims}, supported dimensions: {sorted(valid_dimensions)}")
        logger.error(err_msg)
        raise ValueError(err_msg)
    logger.info(f"监控维度：{dimensions}，是否包含进程信息：{include_processes}（Top {top_n}）")

    # 3. 初始化结果结构（单个主机结果，无需列表包装）
    result = create_base_result(target_ip)
    remote_hosts_config = TopCommandConfig().get_config().public_config.remote_hosts  # 远程主机配置（假设为字典列表）

    try:
        # 3.1 本地采集：target_ip为127.0.0.1时走本地逻辑（无需SSH）
        if target_ip == "127.0.0.1":
            logger.info(f"开始采集本机（{target_ip}）负载信息")
            # 调用本地指标采集函数（ssh_conn传None）
            for dim in dimensions:
                if dim == "cpu":
                    result["metrics"].update(get_cpu_metrics(is_local=True, ssh_conn=None))
                elif dim == "memory":
                    result["metrics"].update(get_memory_metrics(is_local=True, ssh_conn=None))
                elif dim == "disk":
                    result["metrics"].update(get_disk_metrics(is_local=True, ssh_conn=None))
                elif dim == "network":
                    result["metrics"].update(get_network_metrics(is_local=True, ssh_conn=None))
            # 采集进程信息（如需）
            if include_processes:
                result["processes"] = get_process_metrics(is_local=True, ssh_conn=None, top_n=top_n)
            result["server_info"]["status"] = "online"
            logger.info(f"本机（{target_ip}）负载采集完成")

        # 3.2 远程采集：非127.0.0.1时走SSH逻辑（修复参数报红核心区）
        else:
            logger.info(f"开始采集远程主机（{target_ip}）负载信息，尝试获取认证配置")
            # 1. 获取远程认证配置（返回字典，避免自定义对象属性访问报红）
            server_auth = get_server_auth(target_ip, remote_hosts_config)
            if not server_auth:
                err_msg = (
                    f"未找到远程主机（{target_ip}）的认证配置，无法建立连接"
                    if is_zh else
                    f"Authentication config for remote host ({target_ip}) not found, cannot establish connection")
                logger.error(err_msg)
                result["server_info"]["status"] = "config_error"
                result["error"] = err_msg
                return result

            # 2. 提取SSH连接参数（增加默认值，避免KeyError）
            ssh_host = server_auth.get("host", target_ip)  # 主机地址：优先配置，其次目标IP
            ssh_port = server_auth.get("port", 22)         # 端口：默认22（SSH标准端口）
            ssh_user = server_auth.get("username")         # 用户名：配置必须提供
            ssh_pwd = server_auth.get("password")          # 密码：配置必须提供

            # 3. 校验关键参数（避免空值导致连接失败）
            if not ssh_user or not ssh_pwd:
                err_msg = (
                    f"远程主机（{target_ip}）的认证配置缺失用户名或密码"
                    if is_zh else f"Authentication config for remote host ({target_ip}) lacks username or password")
                logger.error(err_msg)
                result["server_info"]["status"] = "config_error"
                result["error"] = err_msg
                return result

            # 4. SSH连接逻辑（使用提取的参数，避免直接访问字典属性报红）
            ssh_conn = None
            try:
                # 初始化SSH客户端并设置密钥策略
                ssh_conn = paramiko.SSHClient()
                ssh_conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                logger.info(f"尝试连接远程主机：地址={ssh_host}，端口={ssh_port}，用户名={ssh_user}")

                # 建立SSH连接（参数均为明确变量，无字典属性访问，避免报红）
                ssh_conn.connect(
                    hostname=ssh_host,
                    port=ssh_port,
                    username=ssh_user,
                    password=ssh_pwd,
                    timeout=10,          # 连接超时（秒）
                    banner_timeout=10    # 服务器Banner响应超时（适配慢网络）
                )
                logger.info(f"远程主机（{target_ip}）SSH连接成功")

                # 调用远程指标采集函数（is_local传False）
                for dim in dimensions:
                    if dim == "cpu":
                        result["metrics"].update(get_cpu_metrics(is_local=False, ssh_conn=ssh_conn))
                    elif dim == "memory":
                        result["metrics"].update(get_memory_metrics(is_local=False, ssh_conn=ssh_conn))
                    elif dim == "disk":
                        result["metrics"].update(get_disk_metrics(is_local=False, ssh_conn=ssh_conn))
                    elif dim == "network":
                        result["metrics"].update(get_network_metrics(is_local=False, ssh_conn=ssh_conn))
                # 采集远程进程信息（如需）
                if include_processes:
                    result["processes"] = get_process_metrics(is_local=False, ssh_conn=ssh_conn, top_n=top_n)

                result["server_info"]["status"] = "online"
                logger.info(f"远程主机（{target_ip}）负载采集完成")

            # SSH错误分类：明确不同错误场景，便于排查
            except paramiko.AuthenticationException:
                err_msg = (
                    f"远程主机（{target_ip}）SSH认证失败：用户名或密码错误"
                    if is_zh else
                    f"SSH authentication failed for remote host ({target_ip}): wrong username or password")
                logger.error(err_msg)
                result["server_info"]["status"] = "auth_error"
                result["error"] = err_msg
            except paramiko.SSHException as e:
                err_msg = (f"远程主机（{target_ip}）SSH连接异常：{str(e)}"
                           if is_zh else f"SSH connection exception for remote host ({target_ip}): {str(e)}")
                logger.error(err_msg)
                result["server_info"]["status"] = "ssh_error"
                result["error"] = err_msg
            except TimeoutError:
                err_msg = (
                    f"远程主机（{target_ip}）SSH连接超时：请检查网络连通性或主机是否在线"
                    if is_zh else
                    f"SSH connection timed out for remote host ({target_ip}): check network or host status")
                logger.error(err_msg)
                result["server_info"]["status"] = "timeout"
                result["error"] = err_msg
            except Exception as e:
                err_msg = (f"远程主机（{target_ip}）连接未知错误：{str(e)}"
                           if is_zh else f"Unknown connection error for remote host ({target_ip}): {str(e)}")
                logger.error(err_msg)
                result["server_info"]["status"] = "unknown_error"
                result["error"] = err_msg
    # 3.3 全局异常捕获：覆盖采集过程中所有未预料的错误
    except Exception as e:
        err_msg = (f"服务器（{target_ip}）负载采集异常：{str(e)}"
                   if is_zh else f"Load collection exception for server ({target_ip}): {str(e)}")
        logger.error(err_msg)
        result["server_info"]["status"] = "collect_error"
        result["error"] = err_msg

    logger.info(f"单个服务器（{target_ip}）负载采集流程结束")
    return result


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
