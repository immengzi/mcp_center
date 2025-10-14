import logging
from typing import Dict

from config.private.nmap.config_loader import NmapConfig
from .base import get_language, get_remote_auth, validate_target, parse_scan_results, execute_local_command, execute_remote_command
from mcp.server import FastMCP

# 初始化MCP服务
mcp = FastMCP(
    "Nmap Network Scan Management MCP",
    host="0.0.0.0",
    port=NmapConfig().get_config().private_config.port
)

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)



@mcp.tool(
    name="scan_network" if get_language() else "scan_network",
    description="""
    扫描指定IP或网段的网络设备及开放端口
    
    参数:
        -target: 扫描目标（必填，支持单个IP、CIDR网段或IP范围，如192.168.1.1、192.168.1.0/24、192.168.1.1-100）
        -scan_type: 扫描类型（可选，basic/full/quick，默认basic）
                    basic: 基本端口扫描（常用100个端口）
                    full: 全端口扫描（1-65535）
                    quick: 快速扫描（仅检查常用10个端口）
        -port_range: 自定义端口范围（可选，如1-100,8080，优先级高于scan_type）
        -host_discovery: 是否仅进行主机发现（不扫描端口，True/False，默认False）
        -host: 远程主机名/IP（默认localhost，本地操作可不填）
        -ssh_port: SSH端口（默认22，远程操作时使用）
        -ssh_user: SSH用户名（远程操作必填）
        -ssh_pwd: SSH密码（远程操作可选，与ssh_key二选一）
        -ssh_key: SSH私钥路径（远程操作可选，优先于密码）
    
    返回:
        -success: 操作是否成功（布尔值）
        -message: 操作结果描述（如"成功扫描192.168.1.0/24网段，发现5台活跃主机"）
        -data: 包含扫描结果的字典
                -host: 执行扫描的主机名/IP
                -target: 扫描目标
                -scan_type: 扫描类型
                -host_count: 发现的主机总数
                -up_host_count: 活跃主机数量
                -results: 扫描结果列表（每台主机的IP、状态、开放端口等信息）
    """ if get_language() else """
    Scan network devices and open ports of specified IP or network segment
    
    Parameters:
        -target: Scan target (required, supports single IP, CIDR network segment or IP range, 
                 e.g., 192.168.1.1, 192.168.1.0/24, 192.168.1.1-100)
        -scan_type: Scan type (optional, basic/full/quick, default basic)
                    basic: Basic port scan (100 common ports)
                    full: Full port scan (1-65535)
                    quick: Quick scan (only checks 10 common ports)
        -port_range: Custom port range (optional, e.g., 1-100,8080, takes precedence over scan_type)
        -host_discovery: Whether to perform host discovery only (no port scanning, True/False, default False)
        -host: Remote hostname/IP (default localhost, not required for local operations)
        -ssh_port: SSH port (default 22, used for remote operations)
        -ssh_user: SSH username (required for remote operations)
        -ssh_pwd: SSH password (optional for remote operations, alternative to ssh_key)
        -ssh_key: SSH private key path (optional for remote operations, prioritized over password)
    
    Returns:
        -success: Whether the operation is successful (boolean)
        -message: Operation result description (e.g., "Successfully scanned 192.168.1.0/24, found 5 active hosts")
        -data: Dictionary containing scan results
                -host: Hostname/IP performing the scan
                -target: Scan target
                -scan_type: Scan type
                -host_count: Total number of discovered hosts
                -up_host_count: Number of active hosts
                -results: List of scan results (IP, status, open ports, etc. for each host)
    """
)
def scan_network(
    target: str,
    scan_type: str = "basic",
    port_range: str = "",
    host_discovery: bool = False,
    host: str = "localhost",
    ssh_port: int = 22,
    ssh_user: str = "",
    ssh_pwd: str = "",
    ssh_key: str = ""
) -> Dict:
    is_zh = get_language()
    result = {
        "success": False,
        "message": "",
        "data": {
            "host": host,
            "target": target,
            "scan_type": scan_type,
            "host_count": 0,
            "up_host_count": 0,
            "results": []
        }
    }

    # 参数校验
    if not validate_target(target):
        result["message"] = "无效的目标格式，请检查IP/网段（支持格式：192.168.1.1、192.168.1.0/24、192.168.1.1-100）" if is_zh else "Invalid target format, please check IP/network segment (supported formats: 192.168.1.1, 192.168.1.0/24, 192.168.1.1-100)"
        return result
    
    valid_scan_types = ["basic", "full", "quick"]
    if scan_type not in valid_scan_types:
        result["message"] = f"扫描类型必须是{valid_scan_types}之一" if is_zh else f"Scan type must be one of {valid_scan_types}"
        return result
    
    # 远程操作参数校验
    if host not in ["localhost", "127.0.0.1"]:
        if not ssh_user:
            result["message"] = "远程操作必须指定SSH用户名（ssh_user）" if is_zh else "SSH username (ssh_user) must be specified for remote operations"
            return result
        if not ssh_pwd and not ssh_key:
            result["message"] = "远程操作必须提供SSH密码（ssh_pwd）或私钥（ssh_key）" if is_zh else "SSH password (ssh_pwd) or private key (ssh_key) must be provided for remote operations"
            return result

    # 构建Nmap命令
    command_parts = ["nmap", "-oG -"]  # -oG - 表示以 grep 友好格式输出到标准输出
    
    # 主机发现模式（不扫描端口）
    if host_discovery:
        command_parts.append("-sn")  # -sn: 只进行主机发现，不扫描端口
    else:
        # 端口范围配置
        if port_range:
            command_parts.extend(["-p", port_range])
        else:
            # 根据扫描类型设置端口范围
            if scan_type == "basic":
                command_parts.append("-F")  # -F: 快速扫描（约100个常用端口）
            elif scan_type == "full":
                command_parts.extend(["-p", "-"])  # -p-: 扫描所有端口（1-65535）
            elif scan_type == "quick":
                command_parts.extend(["-p", "1-10,80,443,3389,22,21,23,5900,8080,3306"])  # 最常用10个端口
    
    # 添加目标
    command_parts.append(target)
    
    # 组合命令
    command = " ".join(command_parts)

    # 执行命令
    exec_result = {}
    if host in ["localhost", "127.0.0.1"]:
        exec_result = execute_local_command(command)
    else:
        # 远程操作：构建临时认证信息（优先使用传入的参数，其次使用配置）
        auth = {
            "host": host,
            "port": ssh_port,
            "username": ssh_user,
            "password": ssh_pwd,
            "key_path": ssh_key,
            "nmap_path": "/usr/bin"  # 默认路径，可在配置中覆盖
        }
        # 尝试从配置获取补充信息
        config_auth = get_remote_auth(host)
        if config_auth:
            auth["nmap_path"] = config_auth["nmap_path"]
            # 如果未传入密钥或密码，使用配置中的
            if not auth["key_path"]:
                auth["key_path"] = config_auth.get("key_path", "")
            if not auth["password"]:
                auth["password"] = config_auth.get("password", "")
        
        exec_result = execute_remote_command(auth, command)

    # 处理扫描结果
    if exec_result["success"]:
        # 解析扫描结果
        scan_results = parse_scan_results(exec_result["output"])
        result["data"]["results"] = scan_results
        result["data"]["host_count"] = len(scan_results)
        result["data"]["up_host_count"] = sum(1 for host in scan_results if host["status"] == "up")
        
        result["success"] = True
        result["message"] = f"成功扫描{target}，发现{result['data']['host_count']}台主机，其中{result['data']['up_host_count']}台活跃" if is_zh else f"Successfully scanned {target}, found {result['data']['host_count']} hosts, {result['data']['up_host_count']} of which are active"
    else:
        result["message"] = f"扫描{target}失败：{exec_result['error']}" if is_zh else f"Failed to scan {target}: {exec_result['error']}"

    return result
    