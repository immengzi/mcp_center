import logging

from typing import Dict
from config.private.ifconfig.config_loader import IfconfigConfig
from servers.ifconfig.src.base import execute_local_command, execute_remote_command, get_language, get_remote_auth, parse_ifconfig_output
from mcp.server import FastMCP

# 初始化MCP服务
mcp = FastMCP(
    "Ifconfig Network Interface Monitor MCP",
    host="0.0.0.0",
    port=IfconfigConfig().get_config().private_config.port
)

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)



@mcp.tool(
    name="get_network_interfaces" if get_language() else "get_network_interfaces",
    description="""
    通过ifconfig查询本地/远程主机的网络接口详细信息
    
    参数:
        -iface: 网卡名称（可选，如eth0，不填则返回所有网卡）
        -host: 远程主机名/IP（默认localhost，本地操作可不填）
        -port: SSH端口（默认22，远程操作时使用，覆盖配置端口）
    
    返回:
        -success: 操作是否成功（布尔值）
        -message: 操作结果描述（字符串）
        -data: 包含网卡信息的字典
            -host: 操作的主机名/IP
            -interface_count: 网卡总数
            -interfaces: 网卡列表（每条含name/status/mac_address/ipv4/ipv6/mtu/statistics等字段）
            -filter: 筛选条件（iface）
    """ if get_language() else """
    Query detailed information of network interfaces on local/remote host via ifconfig
    
    Parameters:
        -iface: Interface name (optional, e.g., eth0, returns all interfaces if not specified)
        -host: Remote hostname/IP (default localhost, omit for local operation)
        -port: SSH port (default 22, used for remote operation, overrides config port)
    
    Returns:
        -success: Whether the operation succeeded (boolean)
        -message: Operation result description (string)
        -data: Dictionary containing interface information
            -host: Hostname/IP of the operation
            -interface_count: Total number of interfaces
            -interfaces: Interface list (each entry includes name/status/mac_address/ipv4/ipv6/mtu/statistics etc.)
            -filter: Filter criteria (iface)
    """
)
def get_network_interfaces(
    iface: str = "",
    host: str = "localhost",
    port: int = 22
) -> Dict:
    is_zh = get_language()
    result = {
        "success": False,
        "message": "",
        "data": {
            "host": host,
            "interface_count": 0,
            "interfaces": [],
            "filter": {"iface": iface}
        }
    }

    # 构建ifconfig命令
    command = "ifconfig"
    if iface:
        command += f" {iface}"

    # 本地操作
    if host in ["localhost", "127.0.0.1"]:
        exec_result = execute_local_command(command)
        if exec_result["success"]:
            interfaces = parse_ifconfig_output(exec_result["output"])
            result["data"]["interfaces"] = interfaces
            result["data"]["interface_count"] = len(interfaces)
            result["success"] = True
            if iface:
                result["message"] = f"成功获取本地网卡{iface}信息" if is_zh else f"Successfully obtained information of local interface {iface}"
            else:
                result["message"] = f"成功获取本地所有网卡信息，共{len(interfaces)}个" if is_zh else f"Successfully obtained information of all local interfaces, total {len(interfaces)}"
        else:
            result["message"] = f"获取本地网卡信息失败：{exec_result['error']}" if is_zh else f"Failed to get local interface information: {exec_result['error']}"

    # 远程操作
    else:
        auth = get_remote_auth(host)
        if not auth:
            result["message"] = f"未找到远程主机{host}的认证配置" if is_zh else f"Authentication config for remote host {host} not found"
            return result
        if not all(key in auth for key in ["username", "password"]):
            result["message"] = f"远程主机{host}认证配置不完整" if is_zh else f"Incomplete authentication config for remote host {host}"
            return result
        auth["port"] = port

        exec_result = execute_remote_command(auth, command)
        if exec_result["success"]:
            interfaces = parse_ifconfig_output(exec_result["output"])
            result["data"]["interfaces"] = interfaces
            result["data"]["interface_count"] = len(interfaces)
            result["success"] = True
            if iface:
                result["message"] = f"成功获取{host}的网卡{iface}信息" if is_zh else f"Successfully obtained information of interface {iface} on {host}"
            else:
                result["message"] = f"成功获取{host}的所有网卡信息，共{len(interfaces)}个" if is_zh else f"Successfully obtained information of all interfaces on {host}, total {len(interfaces)}"
        else:
            result["message"] = f"获取{host}的网卡信息失败：{exec_result['error']}" if is_zh else f"Failed to get interface information of {host}: {exec_result['error']}"

    return result


@mcp.tool(
    name="get_interface_ip" if get_language() else "get_interface_ip",
    description="""
    通过ifconfig查询本地/远程主机指定网卡的IP地址信息
    
    参数:
        -iface: 网卡名称（必填，如eth0、ens33）
        -host: 远程主机名/IP（默认localhost，本地操作可不填）
        -port: SSH port（默认22，远程操作时使用，覆盖配置端口）
    
    返回:
        -success: 操作是否成功（布尔值）
        -message: 操作结果描述（字符串，如"成功获取eth0的IP地址"）
        -data: 包含IP信息的字典
            -host: 操作的主机名/IP
            -interface: 网卡名称
            -ipv4: IPv4地址信息（address/subnet_mask/broadcast）
            -ipv6: IPv6地址信息（address）
    """ if get_language() else """
    Query IP address information of specified interface on local/remote host via ifconfig
    
    Parameters:
        -iface: Interface name (required, e.g., eth0, ens33)
        -host: Remote hostname/IP (default localhost, omit for local operation)
        -port: SSH port (default 22, used for remote operation, overrides config port)
    
    Returns:
        -success: Whether the operation succeeded (boolean)
        -message: Operation result description (string, e.g., "Successfully obtained IP address of eth0")
        -data: Dictionary containing IP information
            -host: Hostname/IP of the operation
            -interface: Interface name
            -ipv4: IPv4 address information (address/subnet_mask/broadcast)
            -ipv6: IPv6 address information (address)
    """
)
def get_interface_ip(
    iface: str,
    host: str = "localhost",
    port: int = 22
) -> Dict:
    is_zh = get_language()
    result = {
        "success": False,
        "message": "",
        "data": {
            "host": host,
            "interface": iface,
            "ipv4": {
                "address": "",
                "subnet_mask": "",
                "broadcast": ""
            },
            "ipv6": {
                "address": ""
            }
        }
    }

    # 参数校验
    if not iface.strip():
        result["message"] = "网卡名称不能为空" if is_zh else "Interface name cannot be empty"
        return result

    # 调用通用接口查询指定网卡信息
    interface_result = get_network_interfaces(iface=iface, host=host, port=port)
    if not interface_result["success"]:
        result["message"] = interface_result["message"]
        return result

    # 提取IP信息
    if interface_result["data"]["interfaces"]:
        interface_data = interface_result["data"]["interfaces"][0]
        result["data"]["ipv4"] = interface_data["ipv4"]
        result["data"]["ipv6"] = interface_data["ipv6"]
        result["success"] = True
        result["message"] = f"成功获取{iface}的IP地址信息" if is_zh else f"Successfully obtained IP address information of {iface}"
    else:
        result["message"] = f"未找到网卡{iface}的信息" if is_zh else f"No information found for interface {iface}"

    return result