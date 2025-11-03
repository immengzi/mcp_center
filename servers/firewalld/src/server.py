import logging
import re
from typing import Dict
from config.private.firewalld.config_loader import FirewalldConfig
from base import get_language, get_remote_auth, execute_remote_command, execute_local_command, parse_firewalld_rules, parse_firewalld_zones
from mcp.server import FastMCP

# 初始化MCP服务
mcp = FastMCP(
    "Firewalld Firewall Management MCP",
    host="0.0.0.0",
    port=FirewalldConfig().get_config().private_config.port
)

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)




@mcp.tool(
    name="manage_ip_access" if get_language() else "manage_ip_access",
    description="""
    通过firewalld限制或允许特定IP访问（基于富规则）
    
    参数:
        -ip: IP地址（必填，如192.168.1.100，支持CIDR如192.168.1.0/24）
        -action: 操作类型（必填，allow/deny）
        -zone: 防火墙区域（默认public）
        -protocol: 协议（tcp/udp/all，默认all）
        -permanent: 是否永久生效（True/False，默认True）
        -host: 远程主机名/IP（默认localhost，本地操作可不填）
        -port: SSH端口（默认22，远程操作时使用）
    
    返回:
        -success: 操作是否成功（布尔值）
        -message: 操作结果描述
        -data: 包含配置信息的字典
            -host: 操作的主机
            -zone: 应用的区域
            -rule: 配置的规则（ip/action/protocol）
    """ if get_language() else """
    Restrict or allow specific IP access via firewalld (based on rich rules)
    
    Parameters:
        -ip: IP address (required, e.g., 192.168.1.100, supports CIDR like 192.168.1.0/24)
        -action: Operation type (required, allow/deny)
        -zone: Firewall zone (default public)
        -protocol: Protocol (tcp/udp/all, default all)
        -permanent: Whether to take permanent effect (True/False, default True)
        -host: Remote hostname/IP (default localhost)
        -port: SSH port (default 22 for remote operation)
    
    Returns:
        -success: Operation success status (boolean)
        -message: Operation result description
        -data: Configuration information dictionary
            -host: Target host
            -zone: Applied zone
            -rule: Configured rule (ip/action/protocol)
    """
)
def manage_ip_access(
    ip: str,
    action: str,
    zone: str = "public",
    protocol: str = "all",
    permanent: bool = True,
    host: str = "localhost",
    port: int = 22
) -> Dict:
    is_zh = get_language()
    result = {
        "success": False,
        "message": "",
        "data": {
            "host": host,
            "zone": zone,
            "rule": {
                "ip": ip,
                "action": action,
                "protocol": protocol
            }
        }
    }

    # 参数校验
    ip_pattern = re.compile(r'^(\d+\.){3}\d+(/\d+)?$')
    if not ip_pattern.match(ip):
        result["message"] = "IP地址格式无效（支持IPv4和CIDR，如192.168.1.100/24）" if is_zh else "Invalid IP address format (supports IPv4 and CIDR, e.g., 192.168.1.100/24)"
        return result
        
    if action.lower() not in ["allow", "deny"]:
        result["message"] = "操作类型必须是allow或deny" if is_zh else "Action must be allow or deny"
        return result
        
    if protocol.lower() not in ["tcp", "udp", "all"]:
        result["message"] = "协议必须是tcp、udp或all" if is_zh else "Protocol must be tcp, udp or all"
        return result

    # 构建富规则命令
    protocol_param = f"protocol=\"{protocol}\"" if protocol != "all" else ""
    action_cmd = "accept" if action.lower() == "allow" else "reject"
    rich_rule = f'rule family="ipv4" source address="{ip}" {protocol_param} {action_cmd}'
    permanent_flag = "--permanent" if permanent else ""
    command = f'firewall-cmd {permanent_flag} --zone={zone} --add-rich-rule="{rich_rule}"'

    # 执行命令
    if host in ["localhost", "127.0.0.1"]:
        exec_result = execute_local_command(command)
        # 非永久规则无需重载，永久规则需要重载生效
        reload_result = {"success": True}
        if permanent and exec_result["success"]:
            reload_result = execute_local_command("firewall-cmd --reload")
            
        if exec_result["success"] and reload_result["success"]:
            result["success"] = True
            result["message"] = f"成功{action}IP {ip}访问{zone}区域（{'永久' if permanent else '临时'}规则）" if is_zh else f"Successfully {action} IP {ip} access to {zone} zone ({'permanent' if permanent else 'temporary'} rule)"
        else:
            error_msg = []
            if not exec_result["success"]:
                error_msg.append(exec_result["error"])
            if permanent and not reload_result["success"]:
                error_msg.append(reload_result["error"])
            result["message"] = f"操作失败：{'; '.join(error_msg)}" if is_zh else f"Operation failed: {'; '.join(error_msg)}"
    else:
        auth = get_remote_auth(host)
        if not auth:
            result["message"] = f"未找到远程主机{host}的认证配置" if is_zh else f"Authentication config for {host} not found"
            return result
            
        exec_result = execute_remote_command(auth, command)
        reload_result = {"success": True}
        if permanent and exec_result["success"]:
            reload_result = execute_remote_command(auth, "firewall-cmd --reload")
            
        if exec_result["success"] and reload_result["success"]:
            result["success"] = True
            result["message"] = f"成功在{host}上{action}IP {ip}访问{zone}区域（{'永久' if permanent else '临时'}规则）" if is_zh else f"Successfully {action} IP {ip} access to {zone} zone on {host} ({'permanent' if permanent else 'temporary'} rule)"
        else:
            error_msg = []
            if not exec_result["success"]:
                error_msg.append(exec_result["error"])
            if permanent and not reload_result["success"]:
                error_msg.append(reload_result["error"])
            result["message"] = f"远程操作失败：{'; '.join(error_msg)}" if is_zh else f"Remote operation failed: {'; '.join(error_msg)}"

    return result


@mcp.tool(
    name="manage_port_access" if get_language() else "manage_port_access",
    description="""
    通过firewalld限制或允许特定端口访问
    
    参数:
        -port: 端口号（必填，如80，支持范围如80-90）
        -protocol: 协议（tcp/udp，默认tcp）
        -action: 操作类型（必填，add/remove）
        -zone: 防火墙区域（默认public）
        -permanent: 是否永久生效（True/False，默认True）
        -host: 远程主机名/IP（默认localhost）
        -ssh_port: SSH端口（默认22）
    
    返回:
        -success: 操作是否成功
        -message: 操作结果描述
        -data: 包含配置信息的字典
            -host: 操作的主机
            -zone: 应用的区域
            -rule: 配置的规则（port/protocol/action）
    """ if get_language() else """
    Restrict or allow specific port access via firewalld
    
    Parameters:
        -port: Port number (required, e.g., 80, supports range like 80-90)
        -protocol: Protocol (tcp/udp, default tcp)
        -action: Operation type (required, add/remove)
        -zone: Firewall zone (default public)
        -permanent: Whether to take permanent effect (True/False, default True)
        -host: Remote hostname/IP (default localhost)
        -ssh_port: SSH port (default 22)
    
    Returns:
        -success: Operation success status
        -message: Operation result description
        -data: Configuration information dictionary
            -host: Target host
            -zone: Applied zone
            -rule: Configured rule (port/protocol/action)
    """
)
def manage_port_access(
    port: str,
    protocol: str = "tcp",
    action: str = "add",
    zone: str = "public",
    permanent: bool = True,
    host: str = "localhost",
    ssh_port: int = 22
) -> Dict:
    is_zh = get_language()
    result = {
        "success": False,
        "message": "",
        "data": {
            "host": host,
            "zone": zone,
            "rule": {
                "port": port,
                "protocol": protocol,
                "action": action
            }
        }
    }

    # 参数校验
    port_pattern = re.compile(r'^\d+(-\d+)?$')
    if not port_pattern.match(port):
        result["message"] = "端口格式无效（支持单个端口如80或范围如80-90）" if is_zh else "Invalid port format (supports single port like 80 or range like 80-90)"
        return result
        
    if protocol.lower() not in ["tcp", "udp"]:
        result["message"] = "协议必须是tcp或udp" if is_zh else "Protocol must be tcp or udp"
        return result
        
    if action.lower() not in ["add", "remove"]:
        result["message"] = "操作类型必须是add或remove" if is_zh else "Action must be add or remove"
        return result

    # 构建端口操作命令
    permanent_flag = "--permanent" if permanent else ""
    action_cmd = "--add-port" if action.lower() == "add" else "--remove-port"
    command = f'firewall-cmd {permanent_flag} --zone={zone} {action_cmd}={port}/{protocol}'

    # 执行命令
    if host in ["localhost", "127.0.0.1"]:
        exec_result = execute_local_command(command)
        reload_result = {"success": True}
        if permanent and exec_result["success"]:
            reload_result = execute_local_command("firewall-cmd --reload")
            
        if exec_result["success"] and reload_result["success"]:
            result["success"] = True
            result["message"] = f"成功{action}端口{port}/{protocol}访问{zone}区域（{'永久' if permanent else '临时'}规则）" if is_zh else f"Successfully {action} port {port}/{protocol} access to {zone} zone ({'permanent' if permanent else 'temporary'} rule)"
        else:
            error_msg = []
            if not exec_result["success"]:
                error_msg.append(exec_result["error"])
            if permanent and not reload_result["success"]:
                error_msg.append(reload_result["error"])
            result["message"] = f"操作失败：{'; '.join(error_msg)}" if is_zh else f"Operation failed: {'; '.join(error_msg)}"
    else:
        auth = get_remote_auth(host)
        if not auth:
            result["message"] = f"未找到远程主机{host}的认证配置" if is_zh else f"Authentication config for {host} not found"
            return result
        auth["port"] = ssh_port
            
        exec_result = execute_remote_command(auth, command)
        reload_result = {"success": True}
        if permanent and exec_result["success"]:
            reload_result = execute_remote_command(auth, "firewall-cmd --reload")
            
        if exec_result["success"] and reload_result["success"]:
            result["success"] = True
            result["message"] = f"成功在{host}上{action}端口{port}/{protocol}访问{zone}区域（{'永久' if permanent else '临时'}规则）" if is_zh else f"Successfully {action} port {port}/{protocol} access to {zone} zone on {host} ({'permanent' if permanent else 'temporary'} rule)"
        else:
            error_msg = []
            if not exec_result["success"]:
                error_msg.append(exec_result["error"])
            if permanent and not reload_result["success"]:
                error_msg.append(reload_result["error"])
            result["message"] = f"远程操作失败：{'; '.join(error_msg)}" if is_zh else f"Remote operation failed: {'; '.join(error_msg)}"

    return result


@mcp.tool(
    name="configure_port_forward" if get_language() else "configure_port_forward",
    description="""
    配置firewalld的端口转发规则（将源端口流量转发到目标IP:端口）
    
    参数:
        -source_port: 源端口（必填，如80）
        -dest_ip: 目标IP（必填，如192.168.2.100）
        -dest_port: 目标端口（必填，如8080）
        -protocol: 协议（tcp/udp，默认tcp）
        -action: 操作类型（add/remove，默认add）
        -zone: 防火墙区域（默认public）
        -permanent: 是否永久生效（True/False，默认True）
        -host: 远程主机名/IP（默认localhost）
        -port: SSH端口（默认22）
    
    返回:
        -success: 操作是否成功
        -message: 操作结果描述
        -data: 包含转发规则的字典
            -host: 操作的主机
            -zone: 应用的区域
            -forward_rule: 转发规则详情（source_port/dest_ip等）
    """ if get_language() else """
    Configure firewalld port forwarding rules (forward source port traffic to target IP:port)
    
    Parameters:
        -source_port: Source port (required, e.g., 80)
        -dest_ip: Destination IP (required, e.g., 192.168.2.100)
        -dest_port: Destination port (required, e.g., 8080)
        -protocol: Protocol (tcp/udp, default tcp)
        -action: Operation type (add/remove, default add)
        -zone: Firewall zone (default public)
        -permanent: Whether to take permanent effect (True/False, default True)
        -host: Remote hostname/IP (default localhost)
        -port: SSH port (default 22)
    
    Returns:
        -success: Operation success status
        -message: Operation result description
        -data: Forwarding rule dictionary
            -host: Target host
            -zone: Applied zone
            -forward_rule: Forwarding rule details (source_port/dest_ip etc.)
    """
)
def configure_port_forward(
    source_port: int,
    dest_ip: str,
    dest_port: int,
    protocol: str = "tcp",
    action: str = "add",
    zone: str = "public",
    permanent: bool = True,
    host: str = "localhost",
    port: int = 22
) -> Dict:
    is_zh = get_language()
    result = {
        "success": False,
        "message": "",
        "data": {
            "host": host,
            "zone": zone,
            "forward_rule": {
                "source_port": source_port,
                "dest_ip": dest_ip,
                "dest_port": dest_port,
                "protocol": protocol,
                "action": action
            }
        }
    }

    # 参数校验
    if not (1 <= source_port <= 65535 and 1 <= dest_port <= 65535):
        result["message"] = "端口号必须在1-65535范围内" if is_zh else "Port number must be in 1-65535 range"
        return result
        
    if not re.match(r'^\d+\.\d+\.\d+\.\d+$', dest_ip):
        result["message"] = "目标IP地址格式无效" if is_zh else "Invalid destination IP address format"
        return result
        
    if protocol.lower() not in ["tcp", "udp"]:
        result["message"] = "协议必须是tcp或udp" if is_zh else "Protocol must be tcp or udp"
        return result
        
    if action.lower() not in ["add", "remove"]:
        result["message"] = "操作类型必须是add或remove" if is_zh else "Action must be add or remove"
        return result

    # 构建端口转发命令（需要先启用地址伪装）
    permanent_flag = "--permanent" if permanent else ""
    action_cmd = "--add-forward-port" if action.lower() == "add" else "--remove-forward-port"
    forward_rule = f"port={source_port}:proto={protocol}:toport={dest_port}:toaddr={dest_ip}"
    commands = [
        # 启用地址伪装（端口转发必需）
        f'firewall-cmd {permanent_flag} --zone={zone} --add-masquerade',
        # 添加/删除转发规则
        f'firewall-cmd {permanent_flag} --zone={zone} {action_cmd}={forward_rule}'
    ]

    # 执行命令
    def run_commands(exec_func, cmd_list, auth=None):
        results = []
        for cmd in cmd_list:
            if auth:
                res = exec_func(auth, cmd)
            else:
                res = exec_func(cmd)
            results.append(res)
            if not res["success"]:
                break
        return results

    if host in ["localhost", "127.0.0.1"]:
        exec_results = run_commands(execute_local_command, commands)
        reload_result = {"success": True}
        if permanent and all(res["success"] for res in exec_results):
            reload_result = execute_local_command("firewall-cmd --reload")
            
        if all(res["success"] for res in exec_results) and reload_result["success"]:
            result["success"] = True
            result["message"] = f"成功{action}端口转发规则：{source_port}/{protocol} -> {dest_ip}:{dest_port}（{'永久' if permanent else '临时'}）" if is_zh else f"Successfully {action} port forwarding rule: {source_port}/{protocol} -> {dest_ip}:{dest_port} ({'permanent' if permanent else 'temporary'})"
        else:
            error_msg = [res["error"] for res in exec_results if not res["success"]]
            if permanent and not reload_result["success"]:
                error_msg.append(reload_result["error"])
            result["message"] = f"操作失败：{'; '.join(error_msg)}" if is_zh else f"Operation failed: {'; '.join(error_msg)}"
    else:
        auth = get_remote_auth(host)
        if not auth:
            result["message"] = f"未找到远程主机{host}的认证配置" if is_zh else f"Authentication config for {host} not found"
            return result
        auth["port"] = port
            
        exec_results = run_commands(execute_remote_command, commands, auth)
        reload_result = {"success": True}
        if permanent and all(res["success"] for res in exec_results):
            reload_result = execute_remote_command(auth, "firewall-cmd --reload")
            
        if all(res["success"] for res in exec_results) and reload_result["success"]:
            result["success"] = True
            result["message"] = f"成功在{host}上{action}端口转发规则：{source_port}/{protocol} -> {dest_ip}:{dest_port}（{'永久' if permanent else '临时'}）" if is_zh else f"Successfully {action} port forwarding rule on {host}: {source_port}/{protocol} -> {dest_ip}:{dest_port} ({'permanent' if permanent else 'temporary'})"
        else:
            error_msg = [res["error"] for res in exec_results if not res["success"]]
            if permanent and not reload_result["success"]:
                error_msg.append(reload_result["error"])
            result["message"] = f"远程操作失败：{'; '.join(error_msg)}" if is_zh else f"Remote operation failed: {'; '.join(error_msg)}"

    return result


@mcp.tool(
    name="list_firewall_rules" if get_language() else "list_firewall_rules",
    description="""
    展示当前所有firewalld规则（按区域分组）
    
    参数:
        -zone: 防火墙区域（可选，不填则显示所有区域）
        -host: 远程主机名/IP（默认localhost）
        -port: SSH port（默认22）
    
    返回:
        -success: 操作是否成功
        -message: 操作结果描述
        -data: 包含所有规则的字典
            -host: 操作的主机
            -zone: 查询的区域（all表示所有）
            -rule_count: 规则总数
            -rules: 规则列表（按区域分组）
    """ if get_language() else """
    List all current firewalld rules (grouped by zone)
    
    Parameters:
        -zone: Firewall zone (optional, all zones if not specified)
        -host: Remote hostname/IP (default localhost)
        -port: SSH port (default 22)
    
    Returns:
        -success: Operation success status
        -message: Operation result description
        -data: Dictionary containing all rules
            -host: Target host
            -zone: Queried zone (all for all zones)
            -rule_count: Total number of rules
            -rules: Rule list (grouped by zone)
    """
)
def list_firewall_rules(
    zone: str = "",
    host: str = "localhost",
    port: int = 22
) -> Dict:
    is_zh = get_language()
    result = {
        "success": False,
        "message": "",
        "data": {
            "host": host,
            "zone": zone if zone else "all",
            "rule_count": 0,
            "rules": []
        }
    }

    # 构建查询命令
    zone_param = f"--zone={zone}" if zone else ""
    command = f"firewall-cmd {zone_param} --list-all-zones"

    # 执行命令
    if host in ["localhost", "127.0.0.1"]:
        exec_result = execute_local_command(command)
        if exec_result["success"]:
            rules = parse_firewalld_rules(exec_result["output"])
            result["data"]["rules"] = rules
            result["data"]["rule_count"] = len(rules)
            result["success"] = True
            result["message"] = f"成功获取{zone if zone else '所有'}区域的防火墙规则，共{len(rules)}条" if is_zh else f"Successfully obtained firewall rules for {zone if zone else 'all'} zones, total {len(rules)} rules"
        else:
            result["message"] = f"获取规则失败：{exec_result['error']}" if is_zh else f"Failed to get rules: {exec_result['error']}"
    else:
        auth = get_remote_auth(host)
        if not auth:
            result["message"] = f"未找到远程主机{host}的认证配置" if is_zh else f"Authentication config for {host} not found"
            return result
        auth["port"] = port
            
        exec_result = execute_remote_command(auth, command)
        if exec_result["success"]:
            rules = parse_firewalld_rules(exec_result["output"])
            result["data"]["rules"] = rules
            result["data"]["rule_count"] = len(rules)
            result["success"] = True
            result["message"] = f"成功获取{host}的{zone if zone else '所有'}区域防火墙规则，共{len(rules)}条" if is_zh else f"Successfully obtained firewall rules for {zone if zone else 'all'} zones on {host}, total {len(rules)} rules"
        else:
            result["message"] = f"远程获取规则失败：{exec_result['error']}" if is_zh else f"Failed to get remote rules: {exec_result['error']}"

    return result


@mcp.tool(
    name="list_firewall_zones" if get_language() else "list_firewall_zones",
    description="""
    展示当前所有firewalld区域信息（包含默认区域和关联接口）
    
    参数:
        -host: 远程主机名/IP（默认localhost）
        -port: SSH端口（默认22）
    
    返回:
        -success: 操作是否成功
        -message: 操作结果描述
        -data: 包含区域信息的字典
            -host: 操作的主机
            -zone_count: 区域总数
            -default_zone: 默认区域名称
            -zones: 区域列表（含名称、是否默认、关联接口等）
    """ if get_language() else """
    List all current firewalld zones (including default zone and associated interfaces)
    
    Parameters:
        -host: Remote hostname/IP (default localhost)
        -port: SSH port (default 22)
    
    Returns:
        -success: Operation success status
        -message: Operation result description
        -data: Dictionary containing zone information
            -host: Target host
            -zone_count: Total number of zones
            -default_zone: Default zone name
            -zones: Zone list (including name, is_default, associated interfaces etc.)
    """
)
def list_firewall_zones(
    host: str = "localhost",
    port: int = 22
) -> Dict:
    is_zh = get_language()
    result = {
        "success": False,
        "message": "",
        "data": {
            "host": host,
            "zone_count": 0,
            "default_zone": "",
            "zones": []
        }
    }

    # 执行命令
    command = "firewall-cmd --get-zones; firewall-cmd --get-default-zone; firewall-cmd --list-all-zones"
    if host in ["localhost", "127.0.0.1"]:
        exec_result = execute_local_command(command)
        if exec_result["success"]:
            zones = parse_firewalld_zones(exec_result["output"])
            default_zone = next((z["name"] for z in zones if z["is_default"]), "")
            result["data"]["zones"] = zones
            result["data"]["zone_count"] = len(zones)
            result["data"]["default_zone"] = default_zone
            result["success"] = True
            result["message"] = f"成功获取所有防火墙区域信息，共{len(zones)}个区域，默认区域：{default_zone}" if is_zh else f"Successfully obtained all firewall zones, total {len(zones)} zones, default zone: {default_zone}"
        else:
            result["message"] = f"获取区域信息失败：{exec_result['error']}" if is_zh else f"Failed to get zone information: {exec_result['error']}"
    else:
        auth = get_remote_auth(host)
        if not auth:
            result["message"] = f"未找到远程主机{host}的认证配置" if is_zh else f"Authentication config for {host} not found"
            return result
        auth["port"] = port
            
        exec_result = execute_remote_command(auth, command)
        if exec_result["success"]:
            zones = parse_firewalld_zones(exec_result["output"])
            default_zone = next((z["name"] for z in zones if z["is_default"]), "")
            result["data"]["zones"] = zones
            result["data"]["zone_count"] = len(zones)
            result["data"]["default_zone"] = default_zone
            result["success"] = True
            result["message"] = f"成功获取{host}的所有防火墙区域信息，共{len(zones)}个区域，默认区域：{default_zone}" if is_zh else f"Successfully obtained all firewall zones on {host}, total {len(zones)} zones, default zone: {default_zone}"
        else:
            result["message"] = f"远程获取区域信息失败：{exec_result['error']}" if is_zh else f"Failed to get remote zone information: {exec_result['error']}"

    return result
    
if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='sse')