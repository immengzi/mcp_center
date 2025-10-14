import paramiko
import subprocess
import re
from typing import Dict, Optional, List
from config.public.base_config_loader import LanguageEnum
from config.private.tshark.config_loader import TsharkConfig

def get_language() -> bool:
    """获取语言配置：True=中文，False=英文"""
    return TsharkConfig().get_config().public_config.language == LanguageEnum.ZH


def get_remote_auth(host: str) -> Optional[Dict]:
    """从配置获取远程主机认证信息（遵循原有配置类逻辑）"""
    remote_hosts = TsharkConfig().get_config().public_config.remote_hosts
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
    """执行远程命令（适配tshark输出解析）"""
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
        stdin, stdout, stderr = ssh_conn.exec_command(command, timeout=60)
        result["output"] = stdout.read().decode("utf-8", errors="replace").strip()
        result["error"] = stderr.read().decode("utf-8", errors="replace").strip()
        # tshark抓包成功时可能无错误输出
        result["success"] = len(result["error"]) == 0 or "Capturing" in result["output"]

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
            timeout=60
        )
        result["output"] = output.strip()
        result["success"] = True
    except subprocess.CalledProcessError as e:
        result["error"] = e.output.strip()
    except subprocess.TimeoutExpired:
        result["error"] = "命令执行超时（tshark抓包未完成）" if get_language() else "Command timeout (tshark capture incomplete)"
    except Exception as e:
        result["error"] = str(e)

    return result


def parse_tshark_capture(output: str) -> List[Dict]:
    """解析tshark抓包输出结果"""
    packets = []
    # tshark -T fields 输出格式：序号 时间 源IP 目的IP 源端口 目的端口 协议 长度 信息
    lines = output.splitlines()
    
    for line in lines:
        if not line.strip() or line.startswith("#"):
            continue
            
        parts = line.strip().split("\t")
        if len(parts) < 9:
            continue
            
        packet_id, timestamp, src_ip, dst_ip, src_port, dst_port, proto, length, info = parts
        
        packets.append({
            "packet_id": int(packet_id) if packet_id.isdigit() else 0,
            "timestamp": timestamp,
            "src_ip": src_ip,
            "dst_ip": dst_ip,
            "src_port": src_port if src_port else "-",
            "dst_port": dst_port if dst_port else "-",
            "protocol": proto.upper(),
            "length": int(length) if length.isdigit() else 0,
            "info": info
        })
    
    return packets


def parse_tshark_protocol_stats(output: str) -> Dict:
    """解析tshark协议统计信息"""
    stats = {
        "total_packets": 0,
        "protocols": {}
    }
    
    # 提取总数据包数
    total_match = re.search(r'Total packets:\s+(\d+)', output)
    if total_match:
        stats["total_packets"] = int(total_match.group(1))
    
    # 提取各协议统计
    proto_lines = re.findall(r'(\w+)\s+\d+\s+\d+\.\d+%', output)
    for proto in proto_lines:
        if proto in stats["protocols"]:
            stats["protocols"][proto] += 1
        else:
            stats["protocols"][proto] = 1
    
    return stats