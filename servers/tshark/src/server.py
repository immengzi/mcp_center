import logging

from config.private.tshark.config_loader import TsharkConfig
from .base import get_language, get_remote_auth, execute_remote_command, execute_local_command, parse_tshark_capture, parse_tshark_protocol_stats
from typing import Dict
from mcp.server import FastMCP

# 初始化MCP服务
mcp = FastMCP(
    "Tshark Packet Capture & Analysis MCP",
    host="0.0.0.0",
    port=TsharkConfig().get_config().private_config.port
)

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)





@mcp.tool(
    name="capture_packets" if get_language() else "capture_packets",
    description="""
    通过tshark在本地/远程主机捕获指定网卡的网络数据包
    
    参数:
        -iface: 网卡名称（必填，如eth0、ens33）
        -duration: 捕获时长（秒，默认10秒，范围3-60）
        -count: 最大捕获包数（可选，如100，达到即停止）
        -filter: 捕获过滤规则（可选，如'tcp port 80'，遵循pcap过滤语法）
        -host: 远程主机名/IP（默认localhost，本地操作可不填）
        -port: SSH端口（默认22，远程操作时使用，覆盖配置端口）
    
    返回:
        -success: 操作是否成功（布尔值）
        -message: 操作结果描述（字符串）
        -data: 包含捕获数据的字典
            -host: 操作的主机名/IP
            -interface: 网卡名称
            -capture_params: 捕获参数（duration/count/filter）
            -packet_count: 实际捕获包数
            -packets: 数据包列表（每条含packet_id/timestamp/src_ip/dst_ip等字段）
    """ if get_language() else """
    Capture network packets of specified interface on local/remote host via tshark
    
    Parameters:
        -iface: Interface name (required, e.g., eth0, ens33)
        -duration: Capture duration (seconds, default 10s, range 3-60)
        -count: Maximum number of packets to capture (optional, e.g., 100, stop when reached)
        -filter: Capture filter rule (optional, e.g., 'tcp port 80', follows pcap filter syntax)
        -host: Remote hostname/IP (default localhost, omit for local operation)
        -port: SSH port (default 22, used for remote operation, overrides config port)
    
    Returns:
        -success: Whether the operation succeeded (boolean)
        -message: Operation result description (string)
        -data: Dictionary containing capture data
            -host: Hostname/IP of the operation
            -interface: Interface name
            -capture_params: Capture parameters (duration/count/filter)
            -packet_count: Actual number of captured packets
            -packets: Packet list (each entry includes packet_id/timestamp/src_ip/dst_ip etc.)
    """
)
def capture_packets(
    iface: str,
    duration: int = 10,
    count: int = 0,
    filter: str = "",
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
            "capture_params": {
                "duration": duration,
                "count": count,
                "filter": filter
            },
            "packet_count": 0,
            "packets": []
        }
    }

    # 参数校验
    if not iface.strip():
        result["message"] = "网卡名称不能为空" if is_zh else "Interface name cannot be empty"
        return result

    if not isinstance(duration, int) or not (3 <= duration <= 60):
        result["message"] = "捕获时长需为3-60秒的整数" if is_zh else "Capture duration must be an integer between 3-60 seconds"
        return result

    if count < 0:
        result["message"] = "最大捕获包数不能为负数" if is_zh else "Maximum packet count cannot be negative"
        return result

    # 构建tshark命令（指定输出格式便于解析）
    command_parts = [
        f"tshark -i {iface.strip()}",
        "-T fields",
        "-e frame.number",
        "-e frame.time",
        "-e ip.src",
        "-e ip.dst",
        "-e tcp.srcport",
        "-e tcp.dstport",
        "-e udp.srcport",
        "-e udp.dstport",
        "-e frame.protocols",
        "-e frame.len",
        "-e frame.info",
        "-E separator=\t"  # 使用制表符分隔字段
    ]

    # 添加捕获时长限制
    command_parts.append(f"-a duration:{duration}")

    # 添加包数限制
    if count > 0:
        command_parts.append(f"-c {count}")

    # 添加过滤规则
    if filter.strip():
        command_parts.append(f"-f '{filter.strip()}'")

    command = " ".join(command_parts)

    # 本地操作
    if host in ["localhost", "127.0.0.1"]:
        exec_result = execute_local_command(command)
        if exec_result["success"] or "Capturing" in exec_result["output"]:
            packets = parse_tshark_capture(exec_result["output"])
            result["data"]["packets"] = packets
            result["data"]["packet_count"] = len(packets)
            result["success"] = True
            result["message"] = f"在本地网卡{iface}上成功捕获{len(packets)}个数据包" if is_zh else f"Successfully captured {len(packets)} packets on local interface {iface}"
        else:
            result["message"] = f"本地捕获数据包失败：{exec_result['error']}" if is_zh else f"Failed to capture local packets: {exec_result['error']}"

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
        if exec_result["success"] or "Capturing" in exec_result["output"]:
            packets = parse_tshark_capture(exec_result["output"])
            result["data"]["packets"] = packets
            result["data"]["packet_count"] = len(packets)
            result["success"] = True
            result["message"] = f"在{host}的网卡{iface}上成功捕获{len(packets)}个数据包" if is_zh else f"Successfully captured {len(packets)} packets on interface {iface} of {host}"
        else:
            result["message"] = f"远程捕获数据包失败：{exec_result['error']}" if is_zh else f"Failed to capture remote packets: {exec_result['error']}"

    return result


@mcp.tool(
    name="analyze_protocol_stats" if get_language() else "analyze_protocol_stats",
    description="""
    通过tshark分析本地/远程主机指定网卡的协议分布统计
    
    参数:
        -iface: 网卡名称（必填，如eth0、ens33）
        -duration: 分析时长（秒，默认10秒，范围3-60）
        -filter: 分析过滤规则（可选，如'ip'，仅统计符合条件的流量）
        -host: 远程主机名/IP（默认localhost，本地操作可不填）
        -port: SSH端口（默认22，远程操作时使用，覆盖配置端口）
    
    返回:
        -success: 操作是否成功（布尔值）
        -message: 操作结果描述（字符串）
        -data: 包含统计数据的字典
            -host: 操作的主机名/IP
            -interface: 网卡名称
            -analysis_params: 分析参数（duration/filter）
            -stats: 协议统计信息（total_packets/protocols）
    """ if get_language() else """
    Analyze protocol distribution statistics of specified interface on local/remote host via tshark
    
    Parameters:
        -iface: Interface name (required, e.g., eth0, ens33)
        -duration: Analysis duration (seconds, default 10s, range 3-60)
        -filter: Analysis filter rule (optional, e.g., 'ip', only statistics on qualified traffic)
        -host: Remote hostname/IP (default localhost, omit for local operation)
        -port: SSH port (default 22, used for remote operation, overrides config port)
    
    Returns:
        -success: Whether the operation succeeded (boolean)
        -message: Operation result description (string)
        -data: Dictionary containing statistical data
            -host: Hostname/IP of the operation
            -interface: Interface name
            -analysis_params: Analysis parameters (duration/filter)
            -stats: Protocol statistics (total_packets/protocols)
    """
)
def analyze_protocol_stats(
    iface: str,
    duration: int = 10,
    filter: str = "",
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
            "analysis_params": {
                "duration": duration,
                "filter": filter
            },
            "stats": {
                "total_packets": 0,
                "protocols": {}
            }
        }
    }

    # 参数校验
    if not iface.strip():
        result["message"] = "网卡名称不能为空" if is_zh else "Interface name cannot be empty"
        return result

    if not isinstance(duration, int) or not (3 <= duration <= 60):
        result["message"] = "分析时长需为3-60秒的整数" if is_zh else "Analysis duration must be an integer between 3-60 seconds"
        return result

    # 构建tshark命令（协议统计模式）
    command_parts = [
        f"tshark -i {iface.strip()}",
        f"-a duration:{duration}",
        "-z io,phs"  # 协议分层统计
    ]

    if filter.strip():
        command_parts.append(f"-f '{filter.strip()}'")

    command = " ".join(command_parts)

    # 本地操作
    if host in ["localhost", "127.0.0.1"]:
        exec_result = execute_local_command(command)
        if exec_result["success"] or "Capturing" in exec_result["output"]:
            stats = parse_tshark_protocol_stats(exec_result["output"])
            result["data"]["stats"] = stats
            result["success"] = True
            result["message"] = f"成功分析本地网卡{iface}的协议分布，共捕获{stats['total_packets']}个数据包" if is_zh else f"Successfully analyzed protocol distribution of local interface {iface}, captured {stats['total_packets']} packets"
        else:
            result["message"] = f"本地协议分析失败：{exec_result['error']}" if is_zh else f"Failed to analyze local protocols: {exec_result['error']}"

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
        if exec_result["success"] or "Capturing" in exec_result["output"]:
            stats = parse_tshark_protocol_stats(exec_result["output"])
            result["data"]["stats"] = stats
            result["success"] = True
            result["message"] = f"成功分析{host}的网卡{iface}的协议分布，共捕获{stats['total_packets']}个数据包" if is_zh else f"Successfully analyzed protocol distribution of interface {iface} on {host}, captured {stats['total_packets']} packets"
        else:
            result["message"] = f"远程协议分析失败：{exec_result['error']}" if is_zh else f"Failed to analyze remote protocols: {exec_result['error']}"

    return result