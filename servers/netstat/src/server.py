import logging
from typing import Dict
from mcp.server import FastMCP
from config.private.netstat.config_loader import NetstatConfig
from servers.netstat.src.base import get_language, parse_netstat_connections, parse_port_occupation
from servers.nload.src.base import execute_local_command, execute_remote_command, get_remote_auth

# 初始化MCP服务
mcp = FastMCP(
    "Netstat Network Connection Monitor MCP",
    host="0.0.0.0",
    port=NetstatConfig().get_config().private_config.port
)

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)




@mcp.tool(
    name="query_network_connections" if get_language() else "query_network_connections",
    description="""
    通过netstat查询本地/远程主机的网络连接列表（支持TCP/UDP）
    
    参数:
        -proto: 协议类型（tcp/udp/all，默认all）
        -state: 连接状态（仅TCP有效，如ESTABLISHED/LISTENING，默认不筛选）
        -host: 远程主机名/IP（默认localhost，本地操作可不填）
        -port: SSH端口（默认22，远程操作时使用，覆盖配置端口）
    
    返回:
        -success: 操作是否成功（布尔值）
        -message: 操作结果描述（字符串）
        -data: 包含连接数据的字典
            -host: 操作的主机名/IP
            -connection_count: 连接总数
            -connections: 连接列表（每个元素含protocol/local_ip/local_port等字段）
            -filter: 筛选条件（proto/state）
    """ if get_language() else """
    Query network connection list of local/remote host via netstat (supports TCP/UDP)
    
    Parameters:
        -proto: Protocol type (tcp/udp/all, default all)
        -state: Connection state (TCP only, e.g., ESTABLISHED/LISTENING, default no filter)
        -host: Remote hostname/IP (default localhost, omit for local operation)
        -port: SSH port (default 22, used for remote operation, overrides config port)
    
    Returns:
        -success: Whether the operation succeeded (boolean)
        -message: Operation result description (string)
        -data: Dictionary containing connection data
            -host: Hostname/IP of the operation
            -connection_count: Total number of connections
            -connections: Connection list (each item includes protocol/local_ip/local_port etc.)
            -filter: Filter conditions (proto/state)
    """
)
def query_network_connections(
    proto: str = "all",
    state: str = "",
    host: str = "localhost",
    port: int = 22
) -> Dict:
    is_zh = get_language()
    result = {
        "success": False,
        "message": "",
        "data": {
            "host": host,
            "connection_count": 0,
            "connections": [],
            "filter": {"proto": proto, "state": state}
        }
    }

    # 1. 参数校验
    valid_protos = ["tcp", "udp", "all"]
    if proto.lower() not in valid_protos:
        result["message"] = f"协议类型无效，支持：{', '.join(valid_protos)}" if is_zh else f"Invalid protocol type, supports: {', '.join(valid_protos)}"
        return result

    # 2. 构建netstat命令（-t:tcp, -u:udp, -l:监听, -n:数字地址, -p:进程）
    proto_flag = ""
    if proto.lower() == "tcp":
        proto_flag = "-t"
    elif proto.lower() == "udp":
        proto_flag = "-u"
    elif proto.lower() == "all":
        proto_flag = "-tu"
    # 基础命令：显示所有监听+非监听连接，带进程信息
    command = f"netstat {proto_flag}nlp"

    # 3. 本地操作
    if host in ["localhost", "127.0.0.1"]:
        exec_result = execute_local_command(command)
        if exec_result["success"]:
            connections = parse_netstat_connections(exec_result["output"])
            # 按状态筛选（仅TCP）
            if state and proto.lower() == "tcp":
                connections = [conn for conn in connections if conn["state"].upper() == state.upper()]
            result["data"]["connections"] = connections
            result["data"]["connection_count"] = len(connections)
            result["success"] = True
            result["message"] = f"成功获取本地{proto.upper()}连接，共{len(connections)}条" if is_zh else f"Successfully obtained local {proto.upper()} connections, total {len(connections)}"
        else:
            result["message"] = f"获取本地连接失败：{exec_result['error']}" if is_zh else f"Failed to get local connections: {exec_result['error']}"

    # 4. 远程操作（依赖配置认证）
    else:
        auth = get_remote_auth(host)
        if not auth:
            result["message"] = f"未找到远程主机{host}的认证配置" if is_zh else f"Authentication config for remote host {host} not found"
            return result
        # 检查配置完整性
        if not all(key in auth for key in ["username", "password"]):
            result["message"] = f"远程主机{host}认证配置不完整" if is_zh else f"Incomplete authentication config for remote host {host}"
            return result
        # 覆盖SSH端口
        auth["port"] = port

        exec_result = execute_remote_command(auth, command)
        if exec_result["success"]:
            connections = parse_netstat_connections(exec_result["output"])
            # 按状态筛选
            if state and proto.lower() == "tcp":
                connections = [conn for conn in connections if conn["state"].upper() == state.upper()]
            result["data"]["connections"] = connections
            result["data"]["connection_count"] = len(connections)
            result["success"] = True
            result["message"] = f"成功获取{host}的{proto.upper()}连接，共{len(connections)}条" if is_zh else f"Successfully obtained {proto.upper()} connections of {host}, total {len(connections)}"
        else:
            result["message"] = f"获取{host}连接失败：{exec_result['error']}" if is_zh else f"Failed to get connections of {host}: {exec_result['error']}"

    return result


@mcp.tool(
    name="check_port_occupation" if get_language() else "check_port_occupation",
    description="""
    通过netstat检测本地/远程主机指定端口的占用情况
    
    参数:
        -port: 端口号（必填，如80、443）
        -proto: 协议类型（tcp/udp，默认tcp）
        -host: 远程主机名/IP（默认localhost，本地操作可不填）
        -ssh_port: SSH端口（默认22，远程操作时使用，覆盖配置端口）
    
    返回:
        -success: 操作是否成功（布尔值）
        -message: 操作结果描述（字符串，如"端口80被nginx占用"）
        -data: 包含端口占用数据的字典
            -host: 操作的主机名/IP
            -check_port: 检测的端口号
            -proto: 检测的协议
            -is_occupied: 是否被占用（布尔值）
            -occupations: 占用列表（含protocol/pid/program等字段）
    """ if get_language() else """
    Check occupation of specified port on local/remote host via netstat
    
    Parameters:
        -port: Port number (required, e.g., 80, 443)
        -proto: Protocol type (tcp/udp, default tcp)
        -host: Remote hostname/IP (default localhost, omit for local operation)
        -ssh_port: SSH port (default 22, used for remote operation, overrides config port)
    
    Returns:
        -success: Whether the operation succeeded (boolean)
        -message: Operation result description (string, e.g., "Port 80 is occupied by nginx")
        -data: Dictionary containing port occupation data
            -host: Hostname/IP of the operation
            -check_port: Checked port number
            -proto: Checked protocol
            -is_occupied: Whether the port is occupied (boolean)
            -occupations: Occupation list (includes protocol/pid/program etc.)
    """
)
def check_port_occupation(
    port: str,
    proto: str = "tcp",
    host: str = "localhost",
    ssh_port: int = 22
) -> Dict:
    is_zh = get_language()
    result = {
        "success": False,
        "message": "",
        "data": {
            "host": host,
            "check_port": port,
            "proto": proto,
            "is_occupied": False,
            "occupations": []
        }
    }

    # 1. 参数校验
    if not port.isdigit() or not (1 <= int(port) <= 65535):
        result["message"] = "端口号必须是1-65535的整数" if is_zh else "Port number must be an integer between 1-65535"
        return result
    if proto.lower() not in ["tcp", "udp"]:
        result["message"] = "协议类型仅支持tcp/udp" if is_zh else "Protocol type only supports tcp/udp"
        return result

    # 2. 构建netstat命令（指定协议，显示进程）
    proto_flag = "-t" if proto.lower() == "tcp" else "-u"
    command = f"netstat {proto_flag}nlp"

    # 3. 本地操作
    if host in ["localhost", "127.0.0.1"]:
        exec_result = execute_local_command(command)
        if exec_result["success"]:
            occupations = parse_port_occupation(exec_result["output"], port)
            result["data"]["occupations"] = occupations
            result["data"]["is_occupied"] = len(occupations) > 0
            result["success"] = True
            if result["data"]["is_occupied"]:
                programs = [occ["program"] for occ in occupations]
                result["message"] = f"本地端口{port}/{proto.upper()}被占用：{', '.join(programs)}" if is_zh else f"Local port {port}/{proto.upper()} is occupied by: {', '.join(programs)}"
            else:
                result["message"] = f"本地端口{port}/{proto.upper()}未被占用" if is_zh else f"Local port {port}/{proto.upper()} is not occupied"
        else:
            result["message"] = f"检测本地端口失败：{exec_result['error']}" if is_zh else f"Failed to check local port: {exec_result['error']}"

    # 4. 远程操作
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
            occupations = parse_port_occupation(exec_result["output"], port)
            result["data"]["occupations"] = occupations
            result["data"]["is_occupied"] = len(occupations) > 0
            result["success"] = True
            if result["data"]["is_occupied"]:
                programs = [occ["program"] for occ in occupations]
                result["message"] = f"远程主机{host}的端口{port}/{proto.upper()}被占用：{', '.join(programs)}" if is_zh else f"Port {port}/{proto.upper()} on {host} is occupied by: {', '.join(programs)}"
            else:
                result["message"] = f"远程主机{host}的端口{port}/{proto.upper()}未被占用" if is_zh else f"Port {port}/{proto.upper()} on {host} is not occupied"
        else:
            result["message"] = f"检测{host}的端口{port}失败：{exec_result['error']}" if is_zh else f"Failed to check port {port} on {host}: {exec_result['error']}"

    return result


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='sse')