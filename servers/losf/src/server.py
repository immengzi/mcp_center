import logging
from typing import Dict
from mcp.server import FastMCP
from config.private.lsof.config_loader import LsofConfig
from servers.losf.src.base import execute_local_command, execute_remote_command, get_language, get_remote_auth, parse_lsof_file_output, parse_lsof_network_output

# 初始化MCP服务
mcp = FastMCP(
    "Lsof File & Network Monitor MCP",
    host="0.0.0.0",
    port=LsofConfig().get_config().private_config.port
)

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)



@mcp.tool(
    name="list_open_files" if get_language() else "list_open_files",
    description="""
    通过lsof查询本地/远程主机的打开文件列表
    
    参数:
        -path: 文件路径（可选，指定后只显示该文件的打开情况）
        -user: 用户名（可选，筛选指定用户打开的文件）
        -host: 远程主机名/IP（默认localhost，本地操作可不填）
        -port: SSH端口（默认22，远程操作时使用，覆盖配置端口）
    
    返回:
        -success: 操作是否成功（布尔值）
        -message: 操作结果描述（字符串）
        -data: 包含文件信息的字典
            -host: 操作的主机名/IP
            -file_count: 打开的文件总数
            -files: 文件列表（每条含command/pid/user/fd/type/file_path等字段）
            -filter: 筛选条件（path/user）
    """ if get_language() else """
    Query list of open files on local/remote host via lsof
    
    Parameters:
        -path: File path (optional, only show open status of this file when specified)
        -user: Username (optional, filter files opened by specified user)
        -host: Remote hostname/IP (default localhost, omit for local operation)
        -port: SSH port (default 22, used for remote operation, overrides config port)
    
    Returns:
        -success: Whether the operation succeeded (boolean)
        -message: Operation result description (string)
        -data: Dictionary containing file information
            -host: Hostname/IP of the operation
            -file_count: Total number of open files
            -files: File list (each entry includes command/pid/user/fd/type/file_path etc.)
            -filter: Filter criteria (path/user)
    """
)
def list_open_files(
    path: str = "",
    user: str = "",
    host: str = "localhost",
    port: int = 22
) -> Dict:
    is_zh = get_language()
    result = {
        "success": False,
        "message": "",
        "data": {
            "host": host,
            "file_count": 0,
            "files": [],
            "filter": {"path": path, "user": user}
        }
    }

    # 构建lsof命令
    command_parts = ["lsof"]
    if path:
        command_parts.append(f'"{path}"')  # 支持带空格的路径
    if user:
        command_parts.append(f"-u {user}")
    command = " ".join(command_parts)

    # 本地操作
    if host in ["localhost", "127.0.0.1"]:
        exec_result = execute_local_command(command)
        if exec_result["success"]:
            files = parse_lsof_file_output(exec_result["output"])
            result["data"]["files"] = files
            result["data"]["file_count"] = len(files)
            result["success"] = True
            result["message"] = f"成功获取本地打开文件，共{len(files)}个" if is_zh else f"Successfully obtained local open files, total {len(files)}"
        else:
            result["message"] = f"获取本地打开文件失败：{exec_result['error']}" if is_zh else f"Failed to get local open files: {exec_result['error']}"

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
            files = parse_lsof_file_output(exec_result["output"])
            result["data"]["files"] = files
            result["data"]["file_count"] = len(files)
            result["success"] = True
            result["message"] = f"成功获取{host}的打开文件，共{len(files)}个" if is_zh else f"Successfully obtained open files of {host}, total {len(files)}"
        else:
            result["message"] = f"获取{host}的打开文件失败：{exec_result['error']}" if is_zh else f"Failed to get open files of {host}: {exec_result['error']}"

    return result


@mcp.tool(
    name="list_network_files" if get_language() else "list_network_files",
    description="""
    通过lsof查询本地/远程主机的网络连接相关文件（网络套接字）
    
    参数:
        -proto: 协议类型（tcp/udp/all，默认all）
        -port: 端口号（可选，筛选指定端口的网络连接）
        -host: 远程主机名/IP（默认localhost，本地操作可不填）
        -ssh_port: SSH端口（默认22，远程操作时使用，覆盖配置端口）
    
    返回:
        -success: 操作是否成功（布尔值）
        -message: 操作结果描述（字符串）
        -data: 包含网络连接信息的字典
            -host: 操作的主机名/IP
            -connection_count: 网络连接总数
            -connections: 连接列表（每条含command/pid/user/local_address/foreign_address/state等字段）
            -filter: 筛选条件（proto/port）
    """ if get_language() else """
    Query network connection-related files (network sockets) on local/remote host via lsof
    
    Parameters:
        -proto: Protocol type (tcp/udp/all, default all)
        -port: Port number (optional, filter network connections of specified port)
        -host: Remote hostname/IP (default localhost, omit for local operation)
        -ssh_port: SSH port (default 22, used for remote operation, overrides config port)
    
    Returns:
        -success: Whether the operation succeeded (boolean)
        -message: Operation result description (string)
        -data: Dictionary containing network connection information
            -host: Hostname/IP of the operation
            -connection_count: Total number of network connections
            -connections: Connection list (each entry includes command/pid/user/local_address/foreign_address/state etc.)
            -filter: Filter criteria (proto/port)
    """
)
def list_network_files(
    proto: str = "all",
    port: str = "",
    host: str = "localhost",
    ssh_port: int = 22
) -> Dict:
    is_zh = get_language()
    result = {
        "success": False,
        "message": "",
        "data": {
            "host": host,
            "connection_count": 0,
            "connections": [],
            "filter": {"proto": proto, "port": port}
        }
    }

    # 参数校验
    valid_protos = ["tcp", "udp", "all"]
    if proto.lower() not in valid_protos:
        result["message"] = f"协议类型无效，支持：{', '.join(valid_protos)}" if is_zh else f"Invalid protocol type, supports: {', '.join(valid_protos)}"
        return result

    if port and (not port.isdigit() or not (1 <= int(port) <= 65535)):
        result["message"] = "端口号必须是1-65535的整数" if is_zh else "Port number must be an integer between 1-65535"
        return result

    # 构建lsof命令
    command_parts = ["lsof -i"]
    if proto.lower() != "all":
        command_parts.append(f"+{proto.lower()}")
    if port:
        command_parts.append(f":{port}")
    command = " ".join(command_parts)

    # 本地操作
    if host in ["localhost", "127.0.0.1"]:
        exec_result = execute_local_command(command)
        if exec_result["success"]:
            connections = parse_lsof_network_output(exec_result["output"])
            result["data"]["connections"] = connections
            result["data"]["connection_count"] = len(connections)
            result["success"] = True
            result["message"] = f"成功获取本地{proto.upper()}网络连接，共{len(connections)}条" if is_zh else f"Successfully obtained local {proto.upper()} network connections, total {len(connections)}"
        else:
            result["message"] = f"获取本地网络连接失败：{exec_result['error']}" if is_zh else f"Failed to get local network connections: {exec_result['error']}"

    # 远程操作
    else:
        auth = get_remote_auth(host)
        if not auth:
            result["message"] = f"未找到远程主机{host}的认证配置" if is_zh else f"Authentication config for remote host {host} not found"
            return result
        if not all(key in auth for key in ["username", "password"]):
            result["message"] = f"远程主机{host}认证配置不完整" if is_zh else f"Incomplete authentication config for remote host {host}"
            return result
        auth["port"] = ssh_port

        exec_result = execute_remote_command(auth, command)
        if exec_result["success"]:
            connections = parse_lsof_network_output(exec_result["output"])
            result["data"]["connections"] = connections
            result["data"]["connection_count"] = len(connections)
            result["success"] = True
            result["message"] = f"成功获取{host}的{proto.upper()}网络连接，共{len(connections)}条" if is_zh else f"Successfully obtained {proto.upper()} network connections of {host}, total {len(connections)}"
        else:
            result["message"] = f"获取{host}的网络连接失败：{exec_result['error']}" if is_zh else f"Failed to get network connections of {host}: {exec_result['error']}"

    return result


@mcp.tool(
    name="find_process_by_file" if get_language() else "find_process_by_file",
    description="""
    通过lsof查找打开指定文件的进程信息
    
    参数:
        -path: 文件路径（必填，如/tmp/test.log）
        -host: 远程主机名/IP（默认localhost，本地操作可不填）
        -port: SSH端口（默认22，远程操作时使用，覆盖配置端口）
    
    返回:
        -success: 操作是否成功（布尔值）
        -message: 操作结果描述（字符串，如"找到2个打开/tmp/test.log的进程"）
        -data: 包含进程信息的字典
            -host: 操作的主机名/IP
            -file_path: 目标文件路径
            -process_count: 相关进程总数
            -processes: 进程列表（每条含command/pid/user/fd等字段）
    """ if get_language() else """
    Find process information that opened specified file via lsof
    
    Parameters:
        -path: File path (required, e.g., /tmp/test.log)
        -host: Remote hostname/IP (default localhost, omit for local operation)
        -port: SSH port (default 22, used for remote operation, overrides config port)
    
    Returns:
        -success: Whether the operation succeeded (boolean)
        -message: Operation result description (string, e.g., "Found 2 processes opening /tmp/test.log")
        -data: Dictionary containing process information
            -host: Hostname/IP of the operation
            -file_path: Target file path
            -process_count: Total number of related processes
            -processes: Process list (each entry includes command/pid/user/fd etc.)
    """
)
def find_process_by_file(
    path: str,
    host: str = "localhost",
    port: int = 22
) -> Dict:
    is_zh = get_language()
    result = {
        "success": False,
        "message": "",
        "data": {
            "host": host,
            "file_path": path,
            "process_count": 0,
            "processes": []
        }
    }

    # 参数校验
    if not path.strip():
        result["message"] = "文件路径不能为空" if is_zh else "File path cannot be empty"
        return result

    # 构建lsof命令
    command = f'lsof "{path.strip()}"'

    # 本地操作
    if host in ["localhost", "127.0.0.1"]:
        exec_result = execute_local_command(command)
        if exec_result["success"]:
            processes = parse_lsof_file_output(exec_result["output"])
            result["data"]["processes"] = processes
            result["data"]["process_count"] = len(processes)
            result["success"] = True
            result["message"] = f"找到{len(processes)}个打开{path}的进程" if is_zh else f"Found {len(processes)} processes opening {path}"
        else:
            result["message"] = f"查找打开{path}的进程失败：{exec_result['error']}" if is_zh else f"Failed to find processes opening {path}: {exec_result['error']}"

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
            processes = parse_lsof_file_output(exec_result["output"])
            result["data"]["processes"] = processes
            result["data"]["process_count"] = len(processes)
            result["success"] = True
            result["message"] = f"找到{len(processes)}个在{host}上打开{path}的进程" if is_zh else f"Found {len(processes)} processes opening {path} on {host}"
        else:
            result["message"] = f"查找{host}上打开{path}的进程失败：{exec_result['error']}" if is_zh else f"Failed to find processes opening {path} on {host}: {exec_result['error']}"

    return result

if __name__ == "__main__":
    mcp.run(transport="sse")