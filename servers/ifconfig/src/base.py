import paramiko
import subprocess
import re
from typing import Dict, Optional, List
from config.private.ifconfig.config_loader import IfconfigConfig
from config.public.base_config_loader import LanguageEnum
def get_language() -> bool:
    """获取语言配置：True=中文，False=英文"""
    return IfconfigConfig().get_config().public_config.language == LanguageEnum.ZH


def get_remote_auth(host: str) -> Optional[Dict]:
    """从配置获取远程主机认证信息（遵循原有配置类逻辑）"""
    remote_hosts = IfconfigConfig().get_config().public_config.remote_hosts
    for host_config in remote_hosts:
        if host in [host_config.host, host_config.name]:
            return {
                "host": host_config.host,
                "port": host_config.port,
                "username": host_config.username,
                "password": host_config.password
            }
    return None


def execute_remote_command(auth: Dict, command: str) -> Dict:
    """执行远程命令（适配ifconfig输出解析）"""
    result = {
        "success": False,
        "output": "",
        "error": ""
    }
    ssh_conn: Optional[paramiko.SSHClient] = None

    try:
        ssh_conn = paramiko.SSHClient()
        ssh_conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_conn.connect(
            hostname=auth["host"],
            port=auth["port"],
            username=auth["username"],
            password=auth["password"],
            timeout=15,
            banner_timeout=10
        )
        stdin, stdout, stderr = ssh_conn.exec_command(command, timeout=30)
        result["output"] = stdout.read().decode("utf-8", errors="replace").strip()
        result["error"] = stderr.read().decode("utf-8", errors="replace").strip()
        result["success"] = len(result["error"]) == 0

    except Exception as e:
        result["error"] = str(e)
    finally:
        if ssh_conn and ssh_conn.get_transport() and ssh_conn.get_transport().is_active(): # type: ignore
            ssh_conn.close()

    return result


def execute_local_command(command: str) -> Dict:
    """执行本地命令"""
    result = {
        "success": False,
        "output": "",
        "error": ""
    }

    try:
        output = subprocess.check_output(
            command,
            shell=True,
            text=True,
            stderr=subprocess.STDOUT,
            timeout=30
        )
        result["output"] = output.strip()
        result["success"] = True
    except subprocess.CalledProcessError as e:
        result["error"] = e.output.strip()
    except subprocess.TimeoutExpired:
        result["error"] = "命令执行超时（ifconfig查询未完成）" if get_language() else "Command timeout (ifconfig query incomplete)"
    except Exception as e:
        result["error"] = str(e)

    return result


def parse_ifconfig_output(output: str) -> List[Dict]:
    """解析ifconfig输出结果，提取网络接口信息"""
    interfaces = []
    # 分割不同网卡的输出（以空行或新网卡名开头为分隔）
    interface_blocks = re.split(r'\n(?=\w+)', output)
    
    for block in interface_blocks:
        if not block.strip():
            continue
            
        # 提取网卡名称
        name_match = re.match(r'^(\w+)\s', block)
        if not name_match:
            continue
        iface_name = name_match.group(1)
        
        # 提取MAC地址
        mac_match = re.search(r'ether\s+([0-9a-f:]+)', block, re.IGNORECASE)
        mac_address = mac_match.group(1) if mac_match else ""
        
        # 提取IPv4地址和子网掩码
        ipv4_match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)\s+netmask\s+(\d+\.\d+\.\d+\.\d+)', block, re.IGNORECASE)
        ipv4_address = ipv4_match.group(1) if ipv4_match else ""
        subnet_mask = ipv4_match.group(2) if ipv4_match else ""
        
        # 提取广播地址
        broadcast_match = re.search(r'broadcast\s+(\d+\.\d+\.\d+\.\d+)', block, re.IGNORECASE)
        broadcast_address = broadcast_match.group(1) if broadcast_match else ""
        
        # 提取IPv6地址
        ipv6_match = re.search(r'inet6\s+([0-9a-f:]+)', block, re.IGNORECASE)
        ipv6_address = ipv6_match.group(1) if ipv6_match else ""
        
        # 提取MTU值
        mtu_match = re.search(r'mtu\s+(\d+)', block, re.IGNORECASE)
        mtu = int(mtu_match.group(1)) if mtu_match else 0
        
        # 提取状态（UP/DOWN）
        status_match = re.search(r'(UP|DOWN|RUNNING)', block, re.IGNORECASE)
        status = status_match.group(1).upper() if status_match else ""
        
        # 提取接收/发送统计
        rx_bytes_match = re.search(r'RX packets.*?bytes\s+(\d+)', block, re.IGNORECASE | re.DOTALL)
        tx_bytes_match = re.search(r'TX packets.*?bytes\s+(\d+)', block, re.IGNORECASE | re.DOTALL)
        rx_packets_match = re.search(r'RX packets\s+(\d+)', block, re.IGNORECASE)
        tx_packets_match = re.search(r'TX packets\s+(\d+)', block, re.IGNORECASE)
        
        interfaces.append({
            "name": iface_name,
            "status": status,
            "mac_address": mac_address,
            "ipv4": {
                "address": ipv4_address,
                "subnet_mask": subnet_mask,
                "broadcast": broadcast_address
            },
            "ipv6": {
                "address": ipv6_address
            },
            "mtu": mtu,
            "statistics": {
                "rx_bytes": int(rx_bytes_match.group(1)) if rx_bytes_match else 0,
                "tx_bytes": int(tx_bytes_match.group(1)) if tx_bytes_match else 0,
                "rx_packets": int(rx_packets_match.group(1)) if rx_packets_match else 0,
                "tx_packets": int(tx_packets_match.group(1)) if tx_packets_match else 0
            }
        })
    
    return interfaces

