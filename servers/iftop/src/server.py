import logging
from typing import Dict, Optional
from config.private.iftop.config_loader import IftopConfig
from servers.iftop.src.base import execute_local_command, get_local_network_interfaces, get_remote_auth, get_remote_network_interfaces, parse_iftop_output
from servers.iftop.src.base import get_language
from mcp.server import FastMCP

from servers.npu.src.base import execute_remote_command

# 初始化MCP服务
mcp = FastMCP(
    "Iftop Network Monitor MCP",
    host="0.0.0.0",
    port=IftopConfig().get_config().private_config.port
)

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)





@mcp.tool(
    name="get_interface_traffic" if get_language() else "get_interface_traffic",
    description="""
    通过iftop获取指定网卡的实时流量监控数据（支持本地/远程）
    
    参数:
        -iface: 网络网卡名称（如eth0、ens33，必填）
        -sample_seconds: 采样时长（秒，默认5秒，范围3-30）
        -host: 远程主机名/IP（默认localhost，本地操作可不填）
        -port: SSH端口（默认22，远程操作时使用）
        -username: SSH用户名（默认root，远程操作时需指定）
        -password: SSH密码（远程操作时必填）
    
    返回:
        -success: 操作是否成功（布尔值）
        -message: 操作结果描述（字符串）
        -data: 包含流量数据的字典
            -host: 操作的主机名/IP
            -total_stats: 网卡总流量统计
                -interface: 网卡名称
                -tx_total: 总发送流量（MB）
                -rx_total: 总接收流量（MB）
                -tx_rate_avg: 平均发送速率（Mbps）
                -rx_rate_avg: 平均接收速率（Mbps）
            -top_connections: Top 10连接列表（按接收速率降序）
                -source: 源IP:端口
                -destination: 目的IP:端口
                -rx_rate_5s: 5秒平均接收速率（Kbps）
                -rx_rate_unit: 速率单位（固定为Kbps）
    """ if get_language() else """
    Get real-time traffic monitoring data of the specified network interface via iftop (supports local/remote)
    
    Parameters:
        -iface: Network interface name (e.g., eth0, ens33, required)
        -sample_seconds: Sampling duration (seconds, default 5s, range 3-30)
        -host: Remote hostname/IP (default localhost, omit for local operation)
        -port: SSH port (default 22, used for remote operation)
        -username: SSH username (default root, required for remote operation)
        -password: SSH password (required for remote operation)
    
    Returns:
        -success: Whether the operation succeeded (boolean)
        -message: Operation result description (string)
        -data: Dictionary containing traffic data
            -host: Hostname/IP of the operation
            -total_stats: Interface total traffic statistics
                -interface: Interface name
                -tx_total: Total transmit traffic (MB)
                -rx_total: Total receive traffic (MB)
                -tx_rate_avg: Average transmit rate (Mbps)
                -rx_rate_avg: Average receive rate (Mbps)
            -top_connections: Top 10 connections list (sorted by receive rate descending)
                -source: Source IP:port
                -destination: Destination IP:port
                -rx_rate_5s: 5-second average receive rate (Kbps)
                -rx_rate_unit: Rate unit (fixed as Kbps)
    """
)
def get_interface_traffic(
    iface: str,
    sample_seconds: int = 5,
    host: str = "localhost",
    port: int = 22,
    username: str = "root",
    password: Optional[str] = None
) -> Dict:
    is_zh = get_language()
    result = {
        "success": False,
        "message": "",
        "data": {
            "host": host,
            "total_stats": {},
            "top_connections": []
        }
    }
    
    # 1. 参数校验
    if not iface.strip():
        result["message"] = "网卡名称不能为空" if is_zh else "Network interface name cannot be empty"
        return result
    
    if not isinstance(sample_seconds, int) or sample_seconds < 3 or sample_seconds > 30:
        result["message"] = "采样时长需为3-30秒的整数" if is_zh else "Sample duration must be an integer between 3-30 seconds"
        return result
    
    # 2. 构建iftop命令（非交互模式，指定采样时长和网卡）
    command = f"iftop -t -s {sample_seconds} -i {iface.strip()}"
    
    # 3. 本地操作
    if host in ["localhost", "127.0.0.1"]:
        # 校验本地网卡是否存在
        local_ifaces = get_local_network_interfaces()
        if iface.strip() not in local_ifaces:
            result["message"] = f"本地网卡{iface}不存在，可用网卡：{', '.join(local_ifaces)}" if is_zh else f"Local interface {iface} does not exist, available interfaces: {', '.join(local_ifaces)}"
            return result
        
        exec_result = execute_local_command(command)
        if exec_result["success"]:
            try:
                total_stats, top_conns = parse_iftop_output(exec_result["output"], iface.strip())
                result["data"]["total_stats"] = total_stats
                result["data"]["top_connections"] = top_conns
                result["success"] = True
                result["message"] = f"成功获取网卡{iface} {sample_seconds}秒流量数据" if is_zh else f"Successfully obtained {sample_seconds}-second traffic data for interface {iface}"
            except Exception as e:
                result["message"] = f"解析流量数据失败：{str(e)}" if is_zh else f"Failed to parse traffic data: {str(e)}"
        else:
            result["message"] = f"获取本地流量失败：{exec_result['error']}" if is_zh else f"Failed to get local traffic: {exec_result['error']}"
    
    # 4. 远程操作
    else:
        # 使用调整后的get_remote_auth获取认证信息（配置类对象属性访问）
        auth = get_remote_auth(host)
        if not auth:
            result["message"] = f"未找到远程主机{host}的认证配置" if is_zh else f"Authentication config for remote host {host} not found"
            return result
        
        # 校验远程网卡是否存在
        remote_ifaces = get_remote_network_interfaces(auth)
        if not remote_ifaces:
            result["message"] = f"获取远程主机{host}网卡列表失败" if is_zh else f"Failed to get interface list of remote host {host}"
            return result
        if iface.strip() not in remote_ifaces:
            result["message"] = f"远程主机{host}网卡{iface}不存在，可用网卡：{', '.join(remote_ifaces)}" if is_zh else f"Remote interface {iface} on host {host} does not exist, available interfaces: {', '.join(remote_ifaces)}"
            return result
        
        # 执行远程流量查询
        exec_result = execute_remote_command(auth, command)
        if exec_result["success"]:
            try:
                total_stats, top_conns = parse_iftop_output(exec_result["output"], iface.strip())
                result["data"]["total_stats"] = total_stats
                result["data"]["top_connections"] = top_conns
                result["success"] = True
                result["message"] = f"成功获取远程主机{host}网卡{iface} {sample_seconds}秒流量数据" if is_zh else f"Successfully obtained {sample_seconds}-second traffic data for interface {iface} on remote host {host}"
            except Exception as e:
                result["message"] = f"解析远程流量数据失败：{str(e)}" if is_zh else f"Failed to parse remote traffic data: {str(e)}"
        else:
            result["message"] = f"获取远程流量失败：{exec_result['error']}" if is_zh else f"Failed to get remote traffic: {exec_result['error']}"
    
    return result


@mcp.tool(
    name="list_network_interfaces" if get_language() else "list_network_interfaces",
    description="""
    获取本地或远程主机的所有网络网卡名称列表（用于选择监控目标）
    
    参数:
        -host: 远程主机名/IP（默认localhost，本地操作可不填）
        -port: SSH端口（默认22，远程操作时使用）
        -username: SSH用户名（默认root，远程操作时需指定）
        -password: SSH密码（远程操作时必填）
    
    返回:
        -success: 操作是否成功（布尔值）
        -message: 操作结果描述（字符串）
        -data: 包含网卡列表的字典
            -host: 操作的主机名/IP
            -interfaces: 网卡名称列表（如["eth0", "lo"]）
    """ if get_language() else """
    Get list of all network interface names on local or remote host (for selecting monitoring targets)
    
    Parameters:
        -host: Remote hostname/IP (default localhost, omit for local operation)
        -port: SSH port (default 22, used for remote operation)
        -username: SSH username (default root, required for remote operation)
        -password: SSH password (required for remote operation)
    
    Returns:
        -success: Whether the operation succeeded (boolean)
        -message: Operation result description (string)
        -data: Dictionary containing interface list
            -host: Hostname/IP of the operation
            -interfaces: List of interface names (e.g., ["eth0", "lo"])
    """
)
def list_network_interfaces(
    host: str = "localhost",
    port: int = 22,
    username: str = "root",
    password: Optional[str] = None
) -> Dict:
    is_zh = get_language()
    result = {
        "success": False,
        "message": "",
        "data": {
            "host": host,
            "interfaces": []
        }
    }
    
    # 本地操作
    if host in ["localhost", "127.0.0.1"]:
        interfaces = get_local_network_interfaces()
        if interfaces:
            result["data"]["interfaces"] = interfaces
            result["success"] = True
            result["message"] = f"成功获取本地{len(interfaces)}个网卡名称" if is_zh else f"Successfully obtained {len(interfaces)} local interface names"
        else:
            result["message"] = "获取本地网卡列表失败" if is_zh else "Failed to get local interface list"
    
    # 远程操作
    else:
        auth = get_remote_auth(host)
        if not auth:
            result["message"] = f"未找到远程主机{host}的认证配置" if is_zh else f"Authentication config for remote host {host} not found"
            return result
        
        interfaces = get_remote_network_interfaces(auth)
        if interfaces:
            result["data"]["interfaces"] = interfaces
            result["success"] = True
            result["message"] = f"成功获取远程主机{host}的{len(interfaces)}个网卡名称" if is_zh else f"Successfully obtained {len(interfaces)} interface names of remote host {host}"
        else:
            result["message"] = f"获取远程主机{host}网卡列表失败" if is_zh else f"Failed to get interface list of remote host {host}"
    
    return result
