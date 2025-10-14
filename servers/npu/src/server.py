import logging

from typing import Dict, Optional

from mcp.server import FastMCP

from config.private.npu.config_loader import NpuSmiConfig
from servers.npu.src.base import execute_local_command, execute_remote_command, get_language, get_remote_auth, parse_npu_info

# 初始化MCP服务
mcp = FastMCP(
    "NPU SMI MCP",
    host="0.0.0.0",
    port=NpuSmiConfig().get_config().private_config.port
)

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)



@mcp.tool(
    name="get_npu_status" if get_language() else "get_npu_status",
    description="""
    通过npu-smi获取NPU设备状态信息（支持本地/远程）
    
    参数:
        -host: 远程主机名/IP（默认localhost，本地操作可不填）
        -port: SSH端口（默认22，远程操作时使用）
        -username: SSH用户名（默认root，远程操作时需指定）
        -password: SSH密码（远程操作时必填）
        -npu_id: 特定NPU设备ID（可选，默认查询所有设备）
    
    返回:
        -success: 操作是否成功（布尔值）
        -message: 操作结果描述（字符串）
        -data: 包含NPU状态信息的字典
            -host: 操作的主机名/IP
            -npus: NPU设备列表，每个设备包含：
                -Id: 设备ID（整数）
                -Name: 设备名称
                -Memory-Usage: 内存使用情况（字典，包含used和total）
                -Utilization: 设备利用率（百分比）
                -Temperature: 温度（摄氏度）
                -其他设备相关信息
    """ if get_language() else """
    Get NPU device status information via npu-smi (supports local/remote)
    
    Parameters:
        -host: Remote hostname/IP (default localhost, omit for local operation)
        -port: SSH port (default 22, used for remote operation)
        -username: SSH username (default root, required for remote operation)
        -password: SSH password (required for remote operation)
        -npu_id: Specific NPU device ID (optional, queries all devices by default)
    
    Returns:
        -success: Whether the operation succeeded (boolean)
        -message: Operation result description (string)
        -data: Dictionary containing NPU status information
            -host: Hostname/IP of the operation
            -npus: List of NPU devices, each containing:
                -Id: Device ID (integer)
                -Name: Device name
                -Memory-Usage: Memory usage (dictionary with used and total)
                -Utilization: Device utilization (percentage)
                -Temperature: Temperature (celsius)
                -Other device-related information
    """
)
def get_npu_status(
    host: str = "localhost",
    port: int = 22,
    username: str = "root",
    password: Optional[str] = None,
    npu_id: Optional[int] = None
) -> Dict:
    is_zh = get_language()
    result = {
        "success": False,
        "message": "",
        "data": {
            "host": host,
            "npus": []
        }
    }
    
    # 构建npu-smi命令
    if npu_id is not None:
        command = f"npu-smi info -i {npu_id}"
    else:
        command = "npu-smi info"
    
    # 本地操作
    if host in ["localhost", "127.0.0.1"]:
        exec_result = execute_local_command(command)
        
        if exec_result["success"]:
            try:
                result["data"]["npus"] = parse_npu_info(exec_result["output"])
                result["success"] = True
                result["message"] = f"成功获取{len(result['data']['npus'])}个NPU设备信息" if is_zh else f"Successfully obtained information for {len(result['data']['npus'])} NPU devices"
            except Exception as e:
                result["message"] = f"解析NPU信息失败: {str(e)}" if is_zh else f"Failed to parse NPU information: {str(e)}"
        else:
            result["message"] = f"获取NPU状态失败: {exec_result['error']}" if is_zh else f"Failed to get NPU status: {exec_result['error']}"
    
    # 远程操作
    else:
        # 执行远程命令
        auth =get_remote_auth(host)
        if auth is None:
            result["message"] = "无法获取远程主机的认证信息" if is_zh else "Failed to get authentication info for remote host"
            return result
        exec_result = execute_remote_command(auth, command)
        
        if exec_result["success"]:
            try:
                result["data"]["npus"] = parse_npu_info(exec_result["output"])
                result["success"] = True
                result["message"] = f"成功获取远程主机{host}的{len(result['data']['npus'])}个NPU设备信息" if is_zh else f"Successfully obtained information for {len(result['data']['npus'])} NPU devices on remote host {host}"
            except Exception as e:
                result["message"] = f"解析远程NPU信息失败: {str(e)}" if is_zh else f"Failed to parse remote NPU information: {str(e)}"
        else:
            result["message"] = f"获取远程NPU状态失败: {exec_result['error']}" if is_zh else f"Failed to get remote NPU status: {exec_result['error']}"
    
    return result


@mcp.tool(
    name="set_npu_power_limit" if get_language() else "set_npu_power_limit",
    description="""
    通过npu-smi设置NPU设备功率限制（支持本地/远程）
    
    参数:
        -npu_id: NPU设备ID（整数，必填）
        -power_limit: 功率限制值（瓦特，整数，必填）
        -host: 远程主机名/IP（默认localhost，本地操作可不填）
        -port: SSH端口（默认22，远程操作时使用）
        -username: SSH用户名（默认root，远程操作时需指定）
        -password: SSH密码（远程操作时必填）
    
    返回:
        -success: 操作是否成功（布尔值）
        -message: 操作结果描述（字符串）
        -data: 包含操作详情的字典
            -host: 操作的主机名/IP
            -npu_id: 操作的NPU设备ID
            -power_limit: 设置的功率限制值（瓦特）
    """ if get_language() else """
    Set NPU device power limit via npu-smi (supports local/remote)
    
    Parameters:
        -npu_id: NPU device ID (integer, required)
        -power_limit: Power limit value (watts, integer, required)
        -host: Remote hostname/IP (default localhost, omit for local operation)
        -port: SSH port (default 22, used for remote operation)
        -username: SSH username (default root, required for remote operation)
        -password: SSH password (required for remote operation)
    
    Returns:
        -success: Whether the operation succeeded (boolean)
        -message: Operation result description (string)
        -data: Dictionary containing operation details
            -host: Hostname/IP of the operation
            -npu_id: ID of the operated NPU device
            -power_limit: Set power limit value (watts)
    """
)
def set_npu_power_limit(
    npu_id: int,
    power_limit: int,
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
            "npu_id": npu_id,
            "power_limit": power_limit
        }
    }
    
    # 参数校验
    if not isinstance(npu_id, int) or npu_id < 0:
        result["message"] = "NPU设备ID必须是非负整数" if is_zh else "NPU device ID must be a non-negative integer"
        return result
        
    if not isinstance(power_limit, int) or power_limit <= 0:
        result["message"] = "功率限制必须是正整数" if is_zh else "Power limit must be a positive integer"
        return result
    
    # 构建设置功率限制的命令
    command = f"npu-smi set -i {npu_id} -pl {power_limit}"
    
    # 本地操作
    if host in ["localhost", "127.0.0.1"]:
        exec_result = execute_local_command(command)
        
        if exec_result["success"]:
            result["success"] = True
            result["message"] = f"NPU设备{npu_id}功率限制已设置为{power_limit}瓦特" if is_zh else f"Power limit for NPU device {npu_id} has been set to {power_limit} watts"
        else:
            result["message"] = f"设置NPU功率限制失败: {exec_result['error']}" if is_zh else f"Failed to set NPU power limit: {exec_result['error']}"
    
    # 远程操作
    else:
        # 执行远程命令
        auth = get_remote_auth(host)
        if auth is None:
            result["message"] = "无法获取远程主机的认证信息" if is_zh else "Failed to get authentication info for remote host"
            return result
        
        exec_result = execute_remote_command(auth, command)

        if exec_result["success"]:
            result["success"] = True
            result["message"] = f"远程主机{host}的NPU设备{npu_id}功率限制已设置为{power_limit}瓦特" if is_zh else f"Power limit for NPU device {npu_id} on remote host {host} has been set to {power_limit} watts"
        else:
            result["message"] = f"设置远程NPU功率限制失败: {exec_result['error']}" if is_zh else f"Failed to set remote NPU power limit: {exec_result['error']}"
    
    return result


@mcp.tool(
    name="reset_npu_device" if get_language() else "reset_npu_device",
    description="""
    通过npu-smi重置NPU设备（支持本地/远程）
    
    参数:
        -npu_id: NPU设备ID（整数，必填）
        -host: 远程主机名/IP（默认localhost，本地操作可不填）
        -port: SSH端口（默认22，远程操作时使用）
        -username: SSH用户名（默认root，远程操作时需指定）
        -password: SSH密码（远程操作时必填）
    
    返回:
        -success: 操作是否成功（布尔值）
        -message: 操作结果描述（字符串）
        -data: 包含操作详情的字典
            -host: 操作的主机名/IP
            -npu_id: 被重置的NPU设备ID
    """ if get_language() else """
    Reset NPU device via npu-smi (supports local/remote)
    
    Parameters:
        -npu_id: NPU device ID (integer, required)
        -host: Remote hostname/IP (default localhost, omit for local operation)
        -port: SSH port (default 22, used for remote operation)
        -username: SSH username (default root, required for remote operation)
        -password: SSH password (required for remote operation)
    
    Returns:
        -success: Whether the operation succeeded (boolean)
        -message: Operation result description (string)
        -data: Dictionary containing operation details
            -host: Hostname/IP of the operation
            -npu_id: ID of the reset NPU device
    """
)
def reset_npu_device(
    npu_id: int,
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
            "npu_id": npu_id
        }
    }
    
    # 校验NPU ID
    if not isinstance(npu_id, int) or npu_id < 0:
        result["message"] = "NPU设备ID必须是非负整数" if is_zh else "NPU device ID must be a non-negative integer"
        return result
    
    # 构建重置NPU的命令
    command = f"npu-smi reset -i {npu_id}"
    
    # 本地操作
    if host in ["localhost", "127.0.0.1"]:
        exec_result = execute_local_command(command)
        
        if exec_result["success"]:
            result["success"] = True
            result["message"] = f"NPU设备{npu_id}已成功重置" if is_zh else f"NPU device {npu_id} has been successfully reset"
        else:
            result["message"] = f"重置NPU设备失败: {exec_result['error']}" if is_zh else f"Failed to reset NPU device: {exec_result['error']}"
    
    # 远程操作
    else:
        # 执行远程命令
        auth = get_remote_auth(host)
        if not auth:
            result["message"] = "无法获取远程主机的认证信息" if is_zh else "Failed to get authentication info for remote host"
            return result
        exec_result = execute_remote_command(auth, command)
        
        if exec_result["success"]:
            result["success"] = True
            result["message"] = f"远程主机{host}的NPU设备{npu_id}已成功重置" if is_zh else f"NPU device {npu_id} on remote host {host} has been successfully reset"
        else:
            result["message"] = f"重置远程NPU设备失败: {exec_result['error']}" if is_zh else f"Failed to reset remote NPU device: {exec_result['error']}"
    
    return result
