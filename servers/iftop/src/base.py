import re
import subprocess
from typing import Dict, List, Optional, Tuple

import paramiko
from config.private.iftop.config_loader import IftopConfig
from config.public.base_config_loader import LanguageEnum


def get_language() -> bool:
    """获取语言配置：True=中文，False=英文"""
    return IftopConfig().get_config().public_config.language == LanguageEnum.ZH


def get_remote_auth(host: str) -> Optional[Dict]:
    """从配置获取远程主机认证信息（使用配置类对象属性访问）"""
    remote_hosts = IftopConfig().get_config().public_config.remote_hosts
    for host_config in remote_hosts:
        # 假设remote_hosts中每个元素是配置类对象，包含host/name/port/username/password属性
        if host in [host_config.host, host_config.name]:
            # 返回标准连接字典，确保键与后续使用一致
            return {
                "host": host_config.host,  # 主机IP/地址
                "port": host_config.port,  # SSH端口，默认22（在配置类中定义）
                "username": host_config.username,  # 用户名
                "password": host_config.password   # 密码
            }
    return None


def execute_remote_command(auth: Dict, command: str) -> Dict:
    """执行远程命令并返回结果（适配iftop非交互模式输出）"""
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
        
        # iftop需指定非交互模式（-t）和采样次数（-s），避免阻塞
        stdin, stdout, stderr = ssh_conn.exec_command(command, timeout=20)
        result["output"] = stdout.read().decode("utf-8", errors="replace").strip()
        result["error"] = stderr.read().decode("utf-8", errors="replace").strip()
        
        if not result["error"] or "interface:" in result["error"]:  # 忽略部分非关键报错
            result["success"] = True
            
    except Exception as e:
        result["error"] = str(e)
    finally:
        if ssh_conn:
            if ssh_conn.get_transport() and ssh_conn.get_transport().is_active(): # type: ignore
                ssh_conn.close()
    
    return result


def execute_local_command(command: str) -> Dict:
    """执行本地命令并返回结果"""
    result = {
        "success": False,
        "output": "",
        "error": ""
    }
    
    try:
        # 执行iftop非交互命令，超时控制
        output = subprocess.check_output(
            command,
            shell=True,
            text=True,
            stderr=subprocess.STDOUT,
            timeout=20
        )
        result["output"] = output.strip()
        result["success"] = True
    except subprocess.CalledProcessError as e:
        # iftop返回非0但有有效输出时，仍视为成功（部分版本特性）
        if "TX:" in e.output or "RX:" in e.output:
            result["output"] = e.output.strip()
            result["success"] = True
        else:
            result["error"] = e.output.strip()
    except subprocess.TimeoutExpired:
        result["error"] = "命令执行超时（iftop采样未完成）" if get_language() else "Command timeout (iftop sampling incomplete)"
    except Exception as e:
        result["error"] = str(e)
    
    return result


def get_local_network_interfaces() -> List[str]:
    """获取本地所有网络网卡名称（用于参数校验）"""
    try:
        output = subprocess.check_output(
            "ip link show | grep '^[0-9]' | awk '{print $2}' | sed 's/://'",
            shell=True,
            text=True
        )
        return [iface.strip() for iface in output.splitlines() if iface.strip()]
    except Exception:
        return []


def get_remote_network_interfaces(auth: Dict) -> List[str]:
    """获取远程主机所有网络网卡名称"""
    try:
        command = "ip link show | grep '^[0-9]' | awk '{print $2}' | sed 's/://'"
        result = execute_remote_command(auth, command)
        if result["success"]:
            return [iface.strip() for iface in result["output"].splitlines() if iface.strip()]
        return []
    except Exception:
        return []


def parse_iftop_output(output: str, iface: str) -> Tuple[Dict, List[Dict]]:
    """
    解析iftop输出结果
    返回：(网卡总流量统计, Top N连接流量列表)
    """
    total_stats = {
        "interface": iface,
        "tx_total": 0.0,  # 总发送流量（MB）
        "rx_total": 0.0,  # 总接收流量（MB）
        "tx_rate_avg": 0.0,  # 平均发送速率（Mbps）
        "rx_rate_avg": 0.0   # 平均接收速率（Mbps）
    }
    top_connections = []
    
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines:
        return total_stats, top_connections
    
    # 1. 提取总流量统计（通常在输出末尾）
    total_pattern = re.compile(
        r'Total send:\s+(\d+\.?\d*)\s+(\w+).*Total receive:\s+(\d+\.?\d*)\s+(\w+)'
    )
    rate_pattern = re.compile(
        r'Avg send rate:\s+(\d+\.?\d*)\s+(\w+).*Avg receive rate:\s+(\d+\.?\d*)\s+(\w+)'
    )
    
    for line in lines:
        total_match = total_pattern.search(line)
        if total_match:
            tx_val, tx_unit, rx_val, rx_unit = total_match.groups()
            # 统一转换为MB
            total_stats["tx_total"] = float(tx_val) * (1 if tx_unit == "MB" else 0.001)
            total_stats["rx_total"] = float(rx_val) * (1 if rx_unit == "MB" else 0.001)
        
        rate_match = rate_pattern.search(line)
        if rate_match:
            tx_rate_val, tx_rate_unit, rx_rate_val, rx_rate_unit = rate_match.groups()
            # 统一转换为Mbps
            total_stats["tx_rate_avg"] = float(tx_rate_val) * (1 if tx_rate_unit == "Mbps" else 1000)
            total_stats["rx_rate_avg"] = float(rx_rate_val) * (1 if rx_rate_unit == "Mbps" else 1000)
    
    # 2. 提取Top连接（包含IP和流量速率）
    conn_pattern = re.compile(
        r'(\d+\.\d+\.\d+\.\d+:\d+)\s+<->\s+(\d+\.\d+\.\d+\.\d+:\d+)\s+'
        r'(\d+\.?\d*\s+\w+\/s)\s+(\d+\.?\d*\s+\w+\/s)\s+(\d+\.?\d*\s+\w+\/s)'
    )
    for line in lines:
        conn_match = conn_pattern.search(line)
        if conn_match:
            src_ip, dst_ip, rx1, rx5, rx10 = conn_match.groups()
            # 取5秒平均速率作为参考
            rx5_val, rx5_unit = rx5.split()
            rx5_val = float(rx5_val)
            # 统一转换为Kbps
            if rx5_unit == "Mbps":
                rx5_val *= 1000
            elif rx5_unit == "B/s":
                rx5_val /= 8  # 简化单位转换
            
            top_connections.append({
                "source": src_ip,
                "destination": dst_ip,
                "rx_rate_5s": round(rx5_val, 2),
                "rx_rate_unit": "Kbps"
            })
    
    # 取Top 10连接（按速率降序）
    top_connections = sorted(
        top_connections,
        key=lambda x: x["rx_rate_5s"],
        reverse=True
    )[:10]
    
    return total_stats, top_connections