import logging
from mcp.server import FastMCP
from typing import Dict

from config.private.ethtool.config_loader import EthtoolConfig
from servers.ethtool.src.base import get_language, get_remote_auth, execute_remote_command, execute_local_command, parse_ethtool_basic, parse_ethtool_features

# 初始化MCP服务
mcp = FastMCP(
    "Ethtool Network Interface Tool MCP",
    host="0.0.0.0",
    port=EthtoolConfig().get_config().private_config.port
)

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)




@mcp.tool(
    name="get_interface_details" if get_language() else "get_interface_details",
    description="""
    通过ethtool查询本地/远程主机指定网卡的详细信息（驱动、固件、速率等）
    
    参数:
        -iface: 网卡名称（必填，如eth0、ens33）
        -host: 远程主机名/IP（默认localhost，本地操作可不填）
        -port: SSH端口（默认22，远程操作时使用，覆盖配置端口）
    
    返回:
        -success: 操作是否成功（布尔值）
        -message: 操作结果描述（字符串）
        -data: 包含网卡详细信息的字典
            -host: 操作的主机名/IP
            -interface: 网卡名称
            -basic_info: 基础信息（driver/version/firmware_version/speed/duplex/link_detected等）
    """ if get_language() else """
    Query detailed information (driver, firmware, speed, etc.) of specified interface on local/remote host via ethtool
    
    Parameters:
        -iface: Interface name (required, e.g., eth0, ens33)
        -host: Remote hostname/IP (default localhost, omit for local operation)
        -port: SSH port (default 22, used for remote operation, overrides config port)
    
    Returns:
        -success: Whether the operation succeeded (boolean)
        -message: Operation result description (string)
        -data: Dictionary containing detailed interface information
            -host: Hostname/IP of the operation
            -interface: Interface name
            -basic_info: Basic information (driver/version/firmware_version/speed/duplex/link_detected etc.)
    """
)
def get_interface_details(
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
            "basic_info": {}
        }
    }

    # 参数校验
    if not iface.strip():
        result["message"] = "网卡名称不能为空" if is_zh else "Interface name cannot be empty"
        return result

    # 构建ethtool命令
    command = f"ethtool {iface.strip()}"

    # 本地操作
    if host in ["localhost", "127.0.0.1"]:
        exec_result = execute_local_command(command)
        if exec_result["success"]:
            basic_info = parse_ethtool_basic(exec_result["output"], iface.strip())
            result["data"]["basic_info"] = basic_info
            result["success"] = True
            result["message"] = f"成功获取本地网卡{iface}的详细信息" if is_zh else f"Successfully obtained detailed information of local interface {iface}"
        else:
            result["message"] = f"获取本地网卡{iface}信息失败：{exec_result['error']}" if is_zh else f"Failed to get information of local interface {iface}: {exec_result['error']}"

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
            basic_info = parse_ethtool_basic(exec_result["output"], iface.strip())
            result["data"]["basic_info"] = basic_info
            result["success"] = True
            result["message"] = f"成功获取{host}的网卡{iface}详细信息" if is_zh else f"Successfully obtained detailed information of interface {iface} on {host}"
        else:
            result["message"] = f"获取{host}的网卡{iface}信息失败：{exec_result['error']}" if is_zh else f"Failed to get information of interface {iface} on {host}: {exec_result['error']}"

    return result


@mcp.tool(
    name="get_interface_features" if get_language() else "get_interface_features",
    description="""
    通过ethtool查询本地/远程主机指定网卡的特性支持情况（网络特性、速率模式等）
    
    参数:
        -iface: 网卡名称（必填，如eth0、ens33）
        -host: 远程主机名/IP（默认localhost，本地操作可不填）
        -port: SSH端口（默认22，远程操作时使用，覆盖配置端口）
    
    返回:
        -success: 操作是否成功（布尔值）
        -message: 操作结果描述（字符串）
        -data: 包含网卡特性信息的字典
            -host: 操作的主机名/IP
            -interface: 网卡名称
            -features: 特性信息（supported/advertised/speed_duplex列表）
    """ if get_language() else """
    Query feature support (network features, speed modes, etc.) of specified interface on local/remote host via ethtool
    
    Parameters:
        -iface: Interface name (required, e.g., eth0, ens33)
        -host: Remote hostname/IP (default localhost, omit for local operation)
        -port: SSH port (default 22, used for remote operation, overrides config port)
    
    Returns:
        -success: Whether the operation succeeded (boolean)
        -message: Operation result description (string)
        -data: Dictionary containing interface feature information
            -host: Hostname/IP of the operation
            -interface: Interface name
            -features: Feature information (supported/advertised/speed_duplex lists)
    """
)
def get_interface_features(
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
            "features": {}
        }
    }

    # 参数校验
    if not iface.strip():
        result["message"] = "网卡名称不能为空" if is_zh else "Interface name cannot be empty"
        return result

    # 构建ethtool命令（查询特性）
    command = f"ethtool -k {iface.strip()}; ethtool {iface.strip()}"

    # 本地操作
    if host in ["localhost", "127.0.0.1"]:
        exec_result = execute_local_command(command)
        if exec_result["success"]:
            features = parse_ethtool_features(exec_result["output"])
            result["data"]["features"] = features
            result["success"] = True
            result["message"] = f"成功获取本地网卡{iface}的特性信息" if is_zh else f"Successfully obtained feature information of local interface {iface}"
        else:
            result["message"] = f"获取本地网卡{iface}特性失败：{exec_result['error']}" if is_zh else f"Failed to get feature information of local interface {iface}: {exec_result['error']}"

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
            features = parse_ethtool_features(exec_result["output"])
            result["data"]["features"] = features
            result["success"] = True
            result["message"] = f"成功获取{host}的网卡{iface}特性信息" if is_zh else f"Successfully obtained feature information of interface {iface} on {host}"
        else:
            result["message"] = f"获取{host}的网卡{iface}特性失败：{exec_result['error']}" if is_zh else f"Failed to get feature information of interface {iface} on {host}: {exec_result['error']}"

    return result


@mcp.tool(
    name="set_interface_speed" if get_language() else "set_interface_speed",
    description="""
    通过ethtool设置本地/远程主机指定网卡的速率和双工模式（需要管理员权限）
    
    参数:
        -iface: 网卡名称（必填，如eth0、ens33）
        -speed: 速率（Mbps，必填，如10/100/1000）
        -duplex: 双工模式（必填，full/half）
        -host: 远程主机名/IP（默认localhost，本地操作可不填）
        -port: SSH端口（默认22，远程操作时使用，覆盖配置端口）
    
    返回:
        -success: 操作是否成功（布尔值）
        -message: 操作结果描述（字符串，如"成功将eth0设置为1000Mbps全双工"）
        -data: 包含设置结果的字典
            -host: 操作的主机名/IP
            -interface: 网卡名称
            -configured: 配置信息（speed/duplex）
    """ if get_language() else """
    Set speed and duplex mode of specified interface on local/remote host via ethtool (requires admin privileges)
    
    Parameters:
        -iface: Interface name (required, e.g., eth0, ens33)
        -speed: Speed (Mbps, required, e.g., 10/100/1000)
        -duplex: Duplex mode (required, full/half)
        -host: Remote hostname/IP (default localhost, omit for local operation)
        -port: SSH port (default 22, used for remote operation, overrides config port)
    
    Returns:
        -success: Whether the operation succeeded (boolean)
        -message: Operation result description (string, e.g., "Successfully set eth0 to 1000Mbps full duplex")
        -data: Dictionary containing configuration result
            -host: Hostname/IP of the operation
            -interface: Interface name
            -configured: Configuration information (speed/duplex)
    """
)
def set_interface_speed(
    iface: str,
    speed: int,
    duplex: str,
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
            "configured": {
                "speed": speed,
                "duplex": duplex
            }
        }
    }

    # 参数校验
    if not iface.strip():
        result["message"] = "网卡名称不能为空" if is_zh else "Interface name cannot be empty"
        return result

    valid_speeds = [10, 100, 1000, 10000]
    if speed not in valid_speeds:
        result["message"] = f"速率必须是{valid_speeds}中的一个（Mbps）" if is_zh else f"Speed must be one of {valid_speeds} (Mbps)"
        return result

    if duplex.lower() not in ["full", "half"]:
        result["message"] = "双工模式必须是full或half" if is_zh else "Duplex mode must be full or half"
        return result

    # 构建ethtool命令（需要sudo权限）
    command = f"sudo ethtool -s {iface.strip()} speed {speed} duplex {duplex.lower()}"

    # 本地操作
    if host in ["localhost", "127.0.0.1"]:
        exec_result = execute_local_command(command)
        if exec_result["success"]:
            # 验证设置结果
            verify_cmd = f"ethtool {iface.strip()}"
            verify_result = execute_local_command(verify_cmd)
            if verify_result["success"]:
                info = parse_ethtool_basic(verify_result["output"], iface.strip())
                if f"{speed}Mb/s" in info["speed"] and duplex.lower() in info["duplex"].lower():
                    result["success"] = True
                    result["message"] = f"成功将本地网卡{iface}设置为{speed}Mbps {duplex}双工" if is_zh else f"Successfully set local interface {iface} to {speed}Mbps {duplex} duplex"
                else:
                    result["message"] = f"设置本地网卡{iface}成功，但验证失败" if is_zh else f"Setting local interface {iface} succeeded, but verification failed"
            else:
                result["message"] = f"设置本地网卡{iface}成功，但验证时出错：{verify_result['error']}" if is_zh else f"Setting local interface {iface} succeeded, but error during verification: {verify_result['error']}"
        else:
            result["message"] = f"设置本地网卡{iface}失败：{exec_result['error']}" if is_zh else f"Failed to set local interface {iface}: {exec_result['error']}"

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
            # 验证设置结果
            verify_cmd = f"ethtool {iface.strip()}"
            verify_result = execute_remote_command(auth, verify_cmd)
            if verify_result["success"]:
                info = parse_ethtool_basic(verify_result["output"], iface.strip())
                if f"{speed}Mb/s" in info["speed"] and duplex.lower() in info["duplex"].lower():
                    result["success"] = True
                    result["message"] = f"成功将{host}的网卡{iface}设置为{speed}Mbps {duplex}双工" if is_zh else f"Successfully set interface {iface} on {host} to {speed}Mbps {duplex} duplex"
                else:
                    result["message"] = f"设置{host}的网卡{iface}成功，但验证失败" if is_zh else f"Setting interface {iface} on {host} succeeded, but verification failed"
            else:
                result["message"] = f"设置{host}的网卡{iface}成功，但验证时出错：{verify_result['error']}" if is_zh else f"Setting interface {iface} on {host} succeeded, but error during verification: {verify_result['error']}"
        else:
            result["message"] = f"设置{host}的网卡{iface}失败：{exec_result['error']}" if is_zh else f"Failed to set interface {iface} on {host}: {exec_result['error']}"

    return result