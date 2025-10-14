import logging
from typing import Dict

from mcp.server import FastMCP

from config.private.nload.config_loader import NloadConfig
from servers.nload.src.base import execute_local_command, execute_remote_command, get_language, get_local_network_interfaces, get_remote_auth, get_remote_network_interfaces, parse_nload_output

# 初始化MCP服务
mcp = FastMCP(
    "Nload Bandwidth Monitor MCP",
    host="0.0.0.0",
    port=NloadConfig().get_config().private_config.port
)

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)



@mcp.tool(
    name="monitor_bandwidth" if get_language() else "monitor_bandwidth",
    description="""
    通过nload监控指定网卡的实时带宽使用情况（支持本地/远程）
    
    参数:
        -iface: 网络网卡名称（如eth0、ens33，必填）
        -duration: 监控时长（秒，默认10秒，范围5-60）
        -host: 远程主机名/IP（默认localhost，本地操作可不填）
        -port: SSH端口（默认22，远程操作时使用，会覆盖配置中的port）
    
    返回:
        -success: 操作是否成功（布尔值）
        -message: 操作结果描述（字符串）
        -data: 包含带宽数据的字典
            -host: 操作的主机名/IP
            -bandwidth: 带宽监控数据
                -interface: 网卡名称
                -incoming: 入站流量信息（current/average/maximum/total/unit）
                -outgoing: 出站流量信息（结构同incoming）
            -monitor_duration: 实际监控时长（秒）
    """ if get_language() else """
    Monitor real-time bandwidth usage of specified network interface via nload (supports local/remote)
    
    Parameters:
        -iface: Network interface name (e.g., eth0, ens33, required)
        -duration: Monitoring duration (seconds, default 10s, range 5-60)
        -host: Remote hostname/IP (default localhost, omit for local operation)
        -port: SSH port (default 22, used for remote operation, overrides config port)
    
    Returns:
        -success: Whether the operation succeeded (boolean)
        -message: Operation result description (string)
        -data: Dictionary containing bandwidth data
            -host: Hostname/IP of the operation
            -bandwidth: Bandwidth monitoring data
                -interface: Interface name
                -incoming: Inbound traffic info (current/average/maximum/total/unit)
                -outgoing: Outbound traffic info (same structure as incoming)
            -monitor_duration: Actual monitoring duration (seconds)
    """
)
def monitor_bandwidth(
    iface: str,
    duration: int = 10,
    host: str = "localhost",
    port: int = 22  # 仅用于覆盖配置中的端口，不接收密码参数
) -> Dict:
    is_zh = get_language()
    result = {
        "success": False,
        "message": "",
        "data": {
            "host": host,
            "bandwidth": {},
            "monitor_duration": duration
        }
    }
    
    # 1. 参数校验
    if not iface.strip():
        result["message"] = "网卡名称不能为空" if is_zh else "Network interface name cannot be empty"
        return result
    
    if not isinstance(duration, int) or not (5 <= duration <= 60):
        result["message"] = "监控时长需为5-60秒的整数" if is_zh else "Monitoring duration must be an integer between 5-60 seconds"
        return result
    
    # 2. 构建nload命令
    command = f"nload -u M -t 1000 {iface.strip()} {duration}"
    
    # 3. 本地操作
    if host in ["localhost", "127.0.0.1"]:
        local_ifaces = get_local_network_interfaces()
        if iface.strip() not in local_ifaces:
            result["message"] = f"本地网卡{iface}不存在，可用网卡：{', '.join(local_ifaces)}" if is_zh else f"Local interface {iface} does not exist, available interfaces: {', '.join(local_ifaces)}"
            return result
        
        exec_result = execute_local_command(command)
        if exec_result["success"]:
            try:
                bandwidth_data = parse_nload_output(exec_result["output"], iface.strip())
                result["data"]["bandwidth"] = bandwidth_data
                result["success"] = True
                result["message"] = f"成功获取网卡{iface} {duration}秒带宽数据" if is_zh else f"Successfully obtained {duration}-second bandwidth data for interface {iface}"
            except Exception as e:
                result["message"] = f"解析带宽数据失败：{str(e)}" if is_zh else f"Failed to parse bandwidth data: {str(e)}"
        else:
            result["message"] = f"获取本地带宽数据失败：{exec_result['error']}" if is_zh else f"Failed to get local bandwidth data: {exec_result['error']}"
    
    # 4. 远程操作（完全依赖配置中的认证信息）
    else:
        # 从配置获取完整认证信息（包含password）
        auth = get_remote_auth(host)
        if not auth:
            result["message"] = f"未找到远程主机{host}的认证配置" if is_zh else f"Authentication config for remote host {host} not found"
            return result
        
        # 检查配置中是否包含必要的认证信息
        if not all(key in auth for key in ["username", "password"]):
            result["message"] = f"远程主机{host}的认证配置不完整（缺少用户名或密码）" if is_zh else f"Authentication config for {host} is incomplete (missing username or password)"
            return result
        
        # 允许通过参数覆盖端口（优先级：函数参数 > 配置）
        auth["port"] = port
        
        # 校验远程网卡是否存在
        remote_ifaces = get_remote_network_interfaces(auth)
        if not remote_ifaces:
            result["message"] = f"获取远程主机{host}网卡列表失败" if is_zh else f"Failed to get interface list of remote host {host}"
            return result
        if iface.strip() not in remote_ifaces:
            result["message"] = f"远程主机{host}网卡{iface}不存在，可用网卡：{', '.join(remote_ifaces)}" if is_zh else f"Remote interface {iface} on host {host} does not exist, available interfaces: {', '.join(remote_ifaces)}"
            return result
        
        # 执行远程监控（使用配置中的password）
        exec_result = execute_remote_command(auth, command)
        if exec_result["success"]:
            try:
                bandwidth_data = parse_nload_output(exec_result["output"], iface.strip())
                result["data"]["bandwidth"] = bandwidth_data
                result["success"] = True
                result["message"] = f"成功获取远程主机{host}网卡{iface} {duration}秒带宽数据" if is_zh else f"Successfully obtained {duration}-second bandwidth data for interface {iface} on remote host {host}"
            except Exception as e:
                result["message"] = f"解析远程带宽数据失败：{str(e)}" if is_zh else f"Failed to parse remote bandwidth data: {str(e)}"
        else:
            result["message"] = f"获取远程带宽数据失败：{exec_result['error']}" if is_zh else f"Failed to get remote bandwidth data: {exec_result['error']}"
    
    return result


@mcp.tool(
    name="list_network_interfaces" if get_language() else "list_network_interfaces",
    description="""
    获取本地或远程主机的所有网络网卡名称列表
    
    参数:
        -host: 远程主机名/IP（默认localhost，本地操作可不填）
        -port: SSH端口（默认22，远程操作时使用，会覆盖配置中的port）
    
    返回:
        -success: 操作是否成功（布尔值）
        -message: 操作结果描述（字符串）
        -data: 包含网卡列表的字典
            -host: 操作的主机名/IP
            -interfaces: 网卡名称列表
    """ if get_language() else """
    Get list of all network interface names on local or remote host
    
    Parameters:
        -host: Remote hostname/IP (default localhost, omit for local operation)
        -port: SSH port (default 22, used for remote operation, overrides config port)
    
    Returns:
        -success: Whether the operation succeeded (boolean)
        -message: Operation result description (string)
        -data: Dictionary containing interface list
            -host: Hostname/IP of the operation
            -interfaces: List of interface names
    """
)
def list_network_interfaces(
    host: str = "localhost",
    port: int = 22  # 仅用于覆盖配置中的端口，不接收密码参数
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
    
    # 远程操作（完全依赖配置中的认证信息）
    else:
        auth = get_remote_auth(host)
        if not auth:
            result["message"] = f"未找到远程主机{host}的认证配置" if is_zh else f"Authentication config for remote host {host} not found"
            return result
        
        if not all(key in auth for key in ["username", "password"]):
            result["message"] = f"远程主机{host}的认证配置不完整" if is_zh else f"Authentication config for {host} is incomplete"
            return result
        
        # 覆盖端口配置
        auth["port"] = port
        
        interfaces = get_remote_network_interfaces(auth)
        if interfaces:
            result["data"]["interfaces"] = interfaces
            result["success"] = True
            result["message"] = f"成功获取远程主机{host}的{len(interfaces)}个网卡名称" if is_zh else f"Successfully obtained {len(interfaces)} interface names of remote host {host}"
        else:
            result["message"] = f"获取远程主机{host}网卡列表失败" if is_zh else f"Failed to get interface list of remote host {host}"
    
    return result
