import re
import subprocess
from typing import Dict, List, Optional

import paramiko

from config.private.nload.config_loader import NloadConfig
from config.public.base_config_loader import LanguageEnum


def get_language() -> bool:
    """获取语言配置：True=中文，False=英文"""
    return NloadConfig().get_config().public_config.language == LanguageEnum.ZH


def get_remote_auth(host: str) -> Optional[Dict]:
    """从配置获取远程主机认证信息（使用配置类对象属性访问）"""
    remote_hosts = NloadConfig().get_config().public_config.remote_hosts
    for host_config in remote_hosts:
        # 匹配主机IP或主机名
        if host in [host_config.host, host_config.name]:
            # 返回配置类对象中的认证信息
            return {
                "host": host_config.host,      # 主机IP
                "port": host_config.port,      # SSH端口（配置类中已定义默认值）
                "username": host_config.username,  # 用户名
                "password": host_config.password   # 密码（从配置中获取）
            }
    return None


def execute_remote_command(auth: Dict, command: str) -> Dict:
    """执行远程命令并返回结果（适配nload非交互模式输出）"""
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
            password=auth["password"],  # 使用配置中获取的密码
            timeout=15,
            banner_timeout=10
        )
        
        stdin, stdout, stderr = ssh_conn.exec_command(command, timeout=20)
        result["output"] = stdout.read().decode("utf-8", errors="replace").strip()
        result["error"] = stderr.read().decode("utf-8", errors="replace").strip()
        
        if not result["error"] or "Curr:" in result["output"]:
            result["success"] = True
            
    except Exception as e:
        result["error"] = str(e)
    finally:
        if ssh_conn and ssh_conn.get_transport() and ssh_conn.get_transport().is_active(): # type: ignore
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
        if "Curr:" in e.output:
            result["output"] = e.output.strip()
            result["success"] = True
        else:
            result["error"] = e.output.strip()
    except subprocess.TimeoutExpired:
        result["error"] = "命令执行超时（nload监控未完成）" if get_language() else "Command timeout (nload monitoring incomplete)"
    except Exception as e:
        result["error"] = str(e)
    
    return result


def get_local_network_interfaces() -> List[str]:
    """获取本地所有网络网卡名称"""
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


def parse_nload_output(output: str, iface: str) -> Dict:
    """解析nload输出结果，提取带宽监控数据"""
    bandwidth_data = {
        "interface": iface,
        "incoming": {
            "current": 0.0,
            "average": 0.0,
            "maximum": 0.0,
            "total": 0.0,
            "unit": "Mbps"
        },
        "outgoing": {
            "current": 0.0,
            "average": 0.0,
            "maximum": 0.0,
            "total": 0.0,
            "unit": "Mbps"
        }
    }
    
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines:
        return bandwidth_data
    
    incoming_pattern = re.compile(
        r'Incoming\s+Curr:\s+(\d+\.?\d*)\s*(\w+/s)\s+'
        r'Avg:\s+(\d+\.?\d*)\s*\w+/s\s+'
        r'Max:\s+(\d+\.?\d*)\s*\w+/s\s+'
        r'Total:\s+(\d+\.?\d*)\s*(\w+)'
    )
    outgoing_pattern = re.compile(
        r'Outgoing\s+Curr:\s+(\d+\.?\d*)\s*(\w+/s)\s+'
        r'Avg:\s+(\d+\.?\d*)\s*\w+/s\s+'
        r'Max:\s+(\d+\.?\d*)\s*\w+/s\s+'
        r'Total:\s+(\d+\.?\d*)\s*(\w+)'
    )
    
    for line in lines:
        in_match = incoming_pattern.search(line)
        if in_match:
            curr_val, curr_unit, avg_val, max_val, total_val, total_unit = in_match.groups()
            multiplier = 1 if curr_unit == "Mbit/s" else 0.001 if curr_unit == "Kbit/s" else 1000
            bandwidth_data["incoming"] = {
                "current": round(float(curr_val) * multiplier, 3),
                "average": round(float(avg_val) * multiplier, 3),
                "maximum": round(float(max_val) * multiplier, 3),
                "total": float(total_val),
                "unit": "Mbps" if curr_unit.endswith('bit/s') else total_unit
            }
        
        out_match = outgoing_pattern.search(line)
        if out_match:
            curr_val, curr_unit, avg_val, max_val, total_val, total_unit = out_match.groups()
            multiplier = 1 if curr_unit == "Mbit/s" else 0.001 if curr_unit == "Kbit/s" else 1000
            bandwidth_data["outgoing"] = {
                "current": round(float(curr_val) * multiplier, 3),
                "average": round(float(avg_val) * multiplier, 3),
                "maximum": round(float(max_val) * multiplier, 3),
                "total": float(total_val),
                "unit": "Mbps" if curr_unit.endswith('bit/s') else total_unit
            }
    
    return bandwidth_data

