import paramiko
import subprocess
import re
from typing import Dict, Optional, List
from config.public.base_config_loader import LanguageEnum
from config.private.nmap.config_loader import NmapConfig

def get_language() -> bool:
    """获取语言配置：True=中文，False=英文"""
    return NmapConfig().get_config().public_config.language == LanguageEnum.ZH


def get_remote_auth(host: str) -> Optional[Dict]:
    """从配置获取远程主机认证信息"""
    remote_hosts = NmapConfig().get_config().public_config.remote_hosts
    for host_config in remote_hosts:
        if host in [host_config.host, host_config.name]:
            return {
                "host": host_config.host,
                "port": host_config.port,
                "username": host_config.username,
                "password": host_config.password,
                "nmap_path": "/usr/bin"  # Nmap工具路径
            }
    return None


def validate_target(target: str) -> bool:
    """验证目标IP/网段格式是否合法"""
    # 支持格式：单个IP (192.168.1.1)、CIDR网段 (192.168.1.0/24)、IP范围 (192.168.1.1-100)
    ip_pattern = r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$'
    cidr_pattern = r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})/(\d{1,2})$'
    range_pattern = r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})-(\d{1,3})$'
    
    if re.match(ip_pattern, target) or re.match(cidr_pattern, target) or re.match(range_pattern, target):
        # 验证每个IP段是否在0-255范围内
        parts = re.split(r'[./-]', target)
        for part in parts:
            if part.isdigit() and not (0 <= int(part) <= 255):
                return False
        # 验证CIDR前缀是否在0-32范围内
        if '/' in target:
            cidr = target.split('/')[1]
            if not (0 <= int(cidr) <= 32):
                return False
        return True
    return False


def parse_scan_results(output: str) -> List[Dict]:
    """解析Nmap扫描结果为结构化数据"""
    results = []
    if not output:
        return results
    
    # 匹配主机信息（如：Nmap scan report for 192.168.1.1）
    host_pattern = re.compile(r'Nmap scan report for ([\d.]+)')
    # 匹配主机状态（如：Host is up (0.00123s latency)）
    status_pattern = re.compile(r'Host is (up|down) ?(?:\((.*?)\))?')
    # 匹配开放端口（如：80/tcp open  http）
    port_pattern = re.compile(r'(\d+/tcp)\s+(\w+)\s+(\w+)\s*(.*)')
    
    current_host = None
    current_ports = []
    current_status = "unknown"
    current_status_details = ""
    for line in output.splitlines():
        host_match = host_pattern.search(line)
        if host_match:
            # 若已有正在处理的主机，先将其添加到结果列表
            if current_host:
                results.append({
                    "ip": current_host,
                    "status": current_status,
                    "status_details": current_status_details,
                    "open_ports": current_ports
                })
            
            current_host = host_match.group(1)
            current_ports = []
            current_status = "unknown"
            current_status_details = ""
            continue
        
        if current_host:
            status_match = status_pattern.search(line)
            if status_match:
                current_status = status_match.group(1)
                current_status_details = status_match.group(2) or ""
            
            port_match = port_pattern.search(line)
            if port_match:
                port_info = port_match.group(1).split('/')[0]
                port_state = port_match.group(2)
                port_service = port_match.group(3)
                port_extra = port_match.group(4)
                
                current_ports.append({
                    "port": port_info,
                    "state": port_state,
                    "service": port_service,
                    "details": port_extra
                })
    
    # 添加最后一个主机
    if current_host:
        results.append({
            "ip": current_host,
            "status": current_status,
            "status_details": current_status_details,
            "open_ports": current_ports
        })
    
    return results


def execute_remote_command(auth: Dict, command: str) -> Dict:
    """执行远程Nmap命令（通过SSH）"""
    result = {
        "success": False,
        "output": "",
        "error": ""
    }
    ssh_conn: Optional[paramiko.SSHClient] = None

    try:
        ssh_conn = paramiko.SSHClient()
        ssh_conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # 优先使用密钥认证
        if auth.get("key_path") and auth["key_path"]:
            private_key = paramiko.RSAKey.from_private_key_file(auth["key_path"])
            ssh_conn.connect(
                hostname=auth["host"],
                port=auth["port"],
                username=auth["username"],
                pkey=private_key,
                timeout=15,
                banner_timeout=10
            )
        else:
            # 密码认证
            ssh_conn.connect(
                hostname=auth["host"],
                port=auth["port"],
                username=auth["username"],
                password=auth["password"],
                timeout=15,
                banner_timeout=10
            )
        
        # 添加Nmap路径到环境变量
        command = f"export PATH={auth['nmap_path']}:$PATH && {command}"
        # Nmap扫描可能耗时较长，设置较长超时
        stdin, stdout, stderr = ssh_conn.exec_command(command, timeout=300)
        result["output"] = stdout.read().decode("utf-8", errors="replace").strip()
        result["error"] = stderr.read().decode("utf-8", errors="replace").strip()
        
        # 判断成功：无错误输出或包含Nmap扫描特征
        result["success"] = len(result["error"]) == 0 or "Nmap done" in result["output"]

    except Exception as e:
        result["error"] = str(e)
    finally:
        if ssh_conn and ssh_conn.get_transport() and ssh_conn.get_transport().is_active(): # type: ignore
            ssh_conn.close()

    return result


def execute_local_command(command: str) -> Dict:
    """执行本地Nmap命令"""
    result = {
        "success": False,
        "output": "",
        "error": ""
    }

    try:
        # 添加Nmap路径到环境变量（默认路径）
        nmap_path = "/usr/bin"
        command = f"export PATH={nmap_path}:$PATH && {command}"
        
        # Nmap扫描可能耗时较长，设置较长超时
        output = subprocess.check_output(
            command,
            shell=True,
            text=True,
            stderr=subprocess.STDOUT,
            timeout=300
        )
        result["output"] = output.strip()
        result["success"] = True
    except subprocess.CalledProcessError as e:
        result["error"] = e.output.strip()
    except subprocess.TimeoutExpired:
        result["error"] = "命令执行超时（Nmap扫描未完成）" if get_language() else "Command timeout (Nmap scan incomplete)"
    except Exception as e:
        result["error"] = str(e)

    return result

