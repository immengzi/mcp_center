import logging
from config.private.iptables.config_loader import IptablesConfig
from servers.iptables.src.base import get_language, get_remote_auth, execute_remote_command, execute_local_command, parse_iptables_rules, parse_nat_rules
import re
from typing import Dict 

from mcp.server import FastMCP

# 初始化MCP服务
mcp = FastMCP(
    "Iptables Firewall Management MCP",
    host="0.0.0.0",
    port=IptablesConfig().get_config().private_config.port
)

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)




@mcp.tool(
    name="manage_ip_rule" if get_language() else "manage_ip_rule",
    description="""
    添加/删除iptables规则限制或允许特定IP访问
    
    参数:
        -ip: 目标IP地址（必填，支持CIDR如192.168.1.0/24）
        -action: 动作（必填，ACCEPT/DROP/REJECT）
        -chain: 链（INPUT/OUTPUT/FORWARD，默认INPUT）
        -protocol: 协议（tcp/udp/all，默认all）
        -port: 端口（可选，如80，仅协议为tcp/udp时有效）
        -action_type: 操作类型（add/delete，默认add）
        -save: 是否保存规则（True/False，默认False）
        -host: 远程主机（默认localhost）
        -port: SSH端口（默认22）
    
    返回:
        -success: 操作是否成功
        -message: 结果描述
        -data: 规则详情
    """ if get_language() else """
    Add/remove iptables rules to restrict or allow specific IP access
    
    Parameters:
        -ip: Target IP address (required, supports CIDR like 192.168.1.0/24)
        -action: Action (required, ACCEPT/DROP/REJECT)
        -chain: Chain (INPUT/OUTPUT/FORWARD, default INPUT)
        -protocol: Protocol (tcp/udp/all, default all)
        -port: Port (optional, e.g., 80, only valid for tcp/udp protocols)
        -action_type: Operation type (add/delete, default add)
        -save: Whether to save rules (True/False, default False)
        -host: Remote host (default localhost)
        -ssh_port: SSH port (default 22)
    
    Returns:
        -success: Operation success status
        -message: Result description
        -data: Rule details
    """
)
def manage_ip_rule(
    ip: str,
    action: str,
    chain: str = "INPUT",
    protocol: str = "all",
    port: int = 0,
    action_type: str = "add",
    save: bool = False,
    host: str = "localhost",
    ssh_port: int = 22
) -> Dict:
    is_zh = get_language()
    result = {
        "success": False,
        "message": "",
        "data": {
            "ip": ip,
            "action": action,
            "chain": chain,
            "protocol": protocol
        }
    }

    # 参数校验
    ip_pattern = re.compile(r'^(\d+\.){3}\d+(/\d+)?$')
    if not ip_pattern.match(ip):
        result["message"] = "无效的IP地址格式（支持IPv4和CIDR）" if is_zh else "Invalid IP address format (supports IPv4 and CIDR)"
        return result
        
    valid_actions = ["ACCEPT", "DROP", "REJECT"]
    if action.upper() not in valid_actions:
        result["message"] = f"动作必须是{valid_actions}之一" if is_zh else f"Action must be one of {valid_actions}"
        return result
        
    valid_chains = ["INPUT", "OUTPUT", "FORWARD"]
    if chain.upper() not in valid_chains:
        result["message"] = f"链必须是{valid_chains}之一" if is_zh else f"Chain must be one of {valid_chains}"
        return result
        
    if protocol.lower() not in ["tcp", "udp", "all"]:
        result["message"] = "协议必须是tcp、udp或all" if is_zh else "Protocol must be tcp, udp or all"
        return result
        
    if port != 0 and not (1 <= port <= 65535):
        result["message"] = "端口号必须在1-65535范围内" if is_zh else "Port number must be in 1-65535 range"
        return result
        
    if action_type.lower() not in ["add", "delete"]:
        result["message"] = "操作类型必须是add或delete" if is_zh else "Action type must be add or delete"
        return result

    # 构建iptables命令
    chain = chain.upper()
    action = action.upper()
    protocol_param = f"-p {protocol}" if protocol != "all" else ""
    port_param = f"--dport {port}" if port != 0 and protocol != "all" else ""
    action_cmd = "-A" if action_type.lower() == "add" else "-D"
    
    command = f"iptables {action_cmd} {chain} {protocol_param} {port_param} -s {ip} -j {action}"
    command = re.sub(r'\s+', ' ', command).strip()  # 移除多余空格

    # 执行命令
    if host in ["localhost", "127.0.0.1"]:
        # 本地操作：直接执行命令
        exec_result = execute_local_command(command)
    else:
        # 远程操作：先获取认证信息，再传入执行函数
        auth = get_remote_auth(host)
        if not auth:
            result["message"] = f"未找到远程主机{host}的认证配置" if is_zh else f"Authentication config for {host} not found"
            return result
        auth["port"] = ssh_port
        # 直接调用远程执行函数，明确传入auth和command
        exec_result = execute_remote_command(auth, command)
    if exec_result["success"]:
        # 保存规则
        save_result = {"success": True}
        if save:
            save_cmd = "iptables-save > /etc/sysconfig/iptables" if host in ["localhost", "127.0.0.1"] else None
            if save_cmd:
                save_result = execute_local_command(save_cmd)
            else:
                save_result = execute_remote_command(auth, "iptables-save > /etc/sysconfig/iptables")
                
        if save_result["success"] or not save:
            result["success"] = True
            result["message"] = f"成功{action_type}规则：{action}来自{ip}的{protocol}流量" + (f"（端口{port}）" if port else "") + ("，已保存" if save else "") if is_zh else f"Successfully {action_type} rule: {action} {protocol} traffic from {ip}" + (f" (port {port})" if port else "") + (", saved" if save else "")
        else:
            result["message"] = f"规则{action_type}成功但保存失败：{save_result['error']}" if is_zh else f"Rule {action_type} succeeded but save failed: {save_result['error']}"
    else:
        result["message"] = f"{action_type}规则失败：{exec_result['error']}" if is_zh else f"Failed to {action_type} rule: {exec_result['error']}"

    return result


@mcp.tool(
    name="configure_port_forward" if get_language() else "configure_port_forward",
    description="""
    配置iptables端口转发规则（DNAT）
    
    参数:
        -src_port: 源端口（必填）
        -dst_ip: 目标IP（必填）
        -dst_port: 目标端口（必填）
        -protocol: 协议（tcp/udp，默认tcp）
        -action: 操作（add/remove，默认add）
        -save: 是否保存规则（True/False，默认False）
        -host: 远程主机（默认localhost）
        -port: SSH端口（默认22）
    
    返回:
        -success: 操作是否成功
        -message: 结果描述
        -data: 转发规则详情
    """ if get_language() else """
    Configure iptables port forwarding rules (DNAT)
    
    Parameters:
        -src_port: Source port (required)
        -dst_ip: Destination IP (required)
        -dst_port: Destination port (required)
        -protocol: Protocol (tcp/udp, default tcp)
        -action: Operation (add/remove, default add)
        -save: Whether to save rules (True/False, default False)
        -host: Remote host (default localhost)
        -ssh_port: SSH port (default 22)
    
    Returns:
        -success: Operation success status
        -message: Result description
        -data: Forwarding rule details
    """
)
def configure_port_forward(
    src_port: int,
    dst_ip: str,
    dst_port: int,
    protocol: str = "tcp",
    action: str = "add",
    save: bool = False,
    host: str = "localhost",
    ssh_port: int = 22
) -> Dict:
    is_zh = get_language()
    result = {
        "success": False,
        "message": "",
        "data": {
            "src_port": src_port,
            "dst_ip": dst_ip,
            "dst_port": dst_port,
            "protocol": protocol
        }
    }

    # 参数校验
    if not (1 <= src_port <= 65535 and 1 <= dst_port <= 65535):
        result["message"] = "端口号必须在1-65535范围内" if is_zh else "Port number must be in 1-65535 range"
        return result
        
    if not re.match(r'^\d+\.\d+\.\d+\.\d+$', dst_ip):
        result["message"] = "目标IP地址格式无效" if is_zh else "Invalid destination IP address format"
        return result
        
    if protocol.lower() not in ["tcp", "udp"]:
        result["message"] = "协议必须是tcp或udp" if is_zh else "Protocol must be tcp or udp"
        return result
        
    if action.lower() not in ["add", "remove"]:
        result["message"] = "操作类型必须是add或remove" if is_zh else "Action must be add or remove"
        return result

    # 构建端口转发命令（需要在nat表中配置）
    action_cmd = "-A" if action.lower() == "add" else "-D"
    commands = [
        # 启用IP转发（临时生效）
        "echo 1 > /proc/sys/net/ipv4/ip_forward",
        # 添加/删除NAT规则
        f"iptables -t nat {action_cmd} PREROUTING -p {protocol} --dport {src_port} -j DNAT --to-destination {dst_ip}:{dst_port}",
        # 添加转发规则
        f"iptables {action_cmd} FORWARD -p {protocol} --dport {dst_port} -d {dst_ip} -j ACCEPT"
    ]

    # 执行命令
    exec_results = []
    if host in ["localhost", "127.0.0.1"]:
        for cmd in commands:
            res = execute_local_command(cmd)
            exec_results.append(res)
            if not res["success"]:
                break
    else:
        auth = get_remote_auth(host)
        if not auth:
            result["message"] = f"未找到远程主机{host}的认证配置" if is_zh else f"Authentication config for {host} not found"
            return result
        auth["port"] = ssh_port
        
        for cmd in commands:
            res = execute_remote_command(auth, cmd)
            exec_results.append(res)
            if not res["success"]:
                break

    # 检查执行结果
    if all(res["success"] for res in exec_results):
        # 保存规则
        save_result = {"success": True}
        if save:
            save_cmd = "iptables-save > /etc/sysconfig/iptables"
            if host in ["localhost", "127.0.0.1"]:
                save_result = execute_local_command(save_cmd)
            else:
                save_result = execute_remote_command(auth, save_cmd)
                
            # 持久化IP转发设置
            sysctl_cmd = "echo 'net.ipv4.ip_forward = 1' >> /etc/sysctl.conf && sysctl -p"
            if host in ["localhost", "127.0.0.1"]:
                execute_local_command(sysctl_cmd)
            else:
                execute_remote_command(auth, sysctl_cmd)
                
        if save_result["success"] or not save:
            result["success"] = True
            result["message"] = f"成功{action}端口转发：{src_port}/{protocol} -> {dst_ip}:{dst_port}" + ("，已保存" if save else "") if is_zh else f"Successfully {action} port forwarding: {src_port}/{protocol} -> {dst_ip}:{dst_port}" + (", saved" if save else "")
        else:
            result["message"] = f"转发规则{action}成功但保存失败：{save_result['error']}" if is_zh else f"Forwarding rule {action} succeeded but save failed: {save_result['error']}"
    else:
        error_msg = [res["error"] for res in exec_results if not res["success"]]
        result["message"] = f"{action}转发规则失败：{'; '.join(error_msg)}" if is_zh else f"Failed to {action} forwarding rule: {'; '.join(error_msg)}"

    return result


@mcp.tool(
    name="list_iptables_rules" if get_language() else "list_iptables_rules",
    description="""
    列出当前所有iptables规则
    
    参数:
        -table: 表（filter/nat/mangle/raw，默认filter）
        -chain: 链（可选，如INPUT，不填则显示所有）
        -host: 远程主机（默认localhost）
        -port: SSH端口（默认22）
    
    返回:
        -success: 操作是否成功
        -message: 结果描述
        -data: 规则列表
    """ if get_language() else """
    List all current iptables rules
    
    Parameters:
        -table: Table (filter/nat/mangle/raw, default filter)
        -chain: Chain (optional, e.g., INPUT, all chains if not specified)
        -host: Remote host (default localhost)
        -ssh_port: SSH port (default 22)
    
    Returns:
        -success: Operation success status
        -message: Result description
        -data: Rule list
    """
)
def list_iptables_rules(
    table: str = "filter",
    chain: str = "",
    host: str = "localhost",
    ssh_port: int = 22
) -> Dict:
    is_zh = get_language()
    result = {
        "success": False,
        "message": "",
        "data": {
            "host": host,
            "table": table,
            "chain": chain,
            "rule_count": 0,
            "rules": []
        }
    }

    # 参数校验
    valid_tables = ["filter", "nat", "mangle", "raw"]
    if table.lower() not in valid_tables:
        result["message"] = f"表必须是{valid_tables}之一" if is_zh else f"Table must be one of {valid_tables}"
        return result

    # 构建查询命令
    table_param = f"-t {table}" if table else ""
    chain_param = chain if chain else ""
    command = f"iptables {table_param} -L {chain_param} -n --line-numbers"
    command = re.sub(r'\s+', ' ', command).strip()

    # 执行命令
    if host in ["localhost", "127.0.0.1"]:
        exec_result = execute_local_command(command)
    else:
        auth = get_remote_auth(host)
        if not auth:
            result["message"] = f"未找到远程主机{host}的认证配置" if is_zh else f"Authentication config for {host} not found"
            return result
        auth["port"] = ssh_port
        exec_result = execute_remote_command(auth, command)

    if exec_result["success"]:
        # 根据表类型选择解析函数
        if table.lower() == "nat":
            rules = parse_nat_rules(exec_result["output"])
        else:
            rules = parse_iptables_rules(exec_result["output"])
            
        result["data"]["rules"] = rules
        result["data"]["rule_count"] = len(rules)
        result["success"] = True
        result["message"] = f"成功获取{table}表{chain if chain else '所有'}链的规则，共{len(rules)}条" if is_zh else f"Successfully obtained rules for {table} table {chain if chain else 'all'} chains, total {len(rules)} rules"
    else:
        result["message"] = f"获取规则失败：{exec_result['error']}" if is_zh else f"Failed to get rules: {exec_result['error']}"

    return result


@mcp.tool(
    name="enable_ip_forward" if get_language() else "enable_ip_forward",
    description="""
    启用/禁用系统IP转发功能
    
    参数:
        -enable: 是否启用（True/False，必填）
        -persistent: 是否持久化（重启生效，默认True）
        -host: 远程主机（默认localhost）
        -port: SSH端口（默认22）
    
    返回:
        -success: 操作是否成功
        -message: 结果描述
        -data: 配置状态
    """ if get_language() else """
    Enable/disable system IP forwarding
    
    Parameters:
        -enable: Whether to enable (True/False, required)
        -persistent: Whether to persist (survive reboot, default True)
        -host: Remote host (default localhost)
        -ssh_port: SSH port (default 22)
    
    Returns:
        -success: Operation success status
        -message: Result description
        -data: Configuration status
    """
)
def enable_ip_forward(
    enable: bool,
    persistent: bool = True,
    host: str = "localhost",
    ssh_port: int = 22
) -> Dict:
    is_zh = get_language()
    result = {
        "success": False,
        "message": "",
        "data": {
            "enabled": enable,
            "persistent": persistent,
            "host": host
        }
    }

    # 构建命令
    value = "1" if enable else "0"
    commands = [
        # 临时生效
        f"echo {value} > /proc/sys/net/ipv4/ip_forward"
    ]
    
    # 持久化配置
    if persistent:
        commands.extend([
            # 删除现有配置
            "sed -i '/net.ipv4.ip_forward/d' /etc/sysctl.conf",
            # 添加新配置
            f"echo 'net.ipv4.ip_forward = {value}' >> /etc/sysctl.conf",
            # 生效配置
            "sysctl -p"
        ])

    # 执行命令
    exec_results = []
    if host in ["localhost", "127.0.0.1"]:
        for cmd in commands:
            res = execute_local_command(cmd)
            exec_results.append(res)
            if not res["success"]:
                break
    else:
        auth = get_remote_auth(host)
        if not auth:
            result["message"] = f"未找到远程主机{host}的认证配置" if is_zh else f"Authentication config for {host} not found"
            return result
        auth["port"] = ssh_port
        
        for cmd in commands:
            res = execute_remote_command(auth, cmd)
            exec_results.append(res)
            if not res["success"]:
                break

    if all(res["success"] for res in exec_results):
        result["success"] = True
        result["message"] = f"成功{'' if enable else '禁用'}IP转发功能" + ("（持久化）" if persistent else "") if is_zh else f"Successfully {'enabled' if enable else 'disabled'} IP forwarding" + (" (persistent)" if persistent else "")
    else:
        error_msg = [res["error"] for res in exec_results if not res["success"]]
        result["message"] = f"{'' if enable else '禁用'}IP转发失败：{'; '.join(error_msg)}" if is_zh else f"Failed to {'enable' if enable else 'disable'} IP forwarding: {'; '.join(error_msg)}"

    return result

if __name__ == "__main__":
    mcp.run(transport="sse")