"""公共基础层：封装所有维度都需要的复用逻辑"""
import paramiko
from datetime import datetime
from typing import Dict, Optional, Tuple
from config.private.top.config_loader import TopCommandConfig

def get_timestamp() -> str:
    """生成统一格式的时间戳"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def create_base_result(ip: str) -> Dict:
    """创建基础结果结构（所有维度通用）"""
    return {
        "server_info": {
            "ip": ip,
            "status": "unknown",
            "timestamp": get_timestamp()
        },
        "metrics": {},
        "error": ""
    }


def execute_command(ssh_conn: paramiko.SSHClient, command: str) -> Tuple[bool, str, str]:
    """执行SSH命令并返回结果"""
    try:
        stdin, stdout, stderr = ssh_conn.exec_command(command, timeout=15)
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        
        if error:
            return False, "", error
        return True, output, ""
    except Exception as e:
        return False, "", f"命令执行失败：{str(e)}"if TopCommandConfig().get_config(
                        ).public_config.language == LanguageEnum.ZH else f"Command execution failed: {str(e)}"
    

def get_server_auth(ip: str, remote_hosts: list) -> Optional[Dict]:
    """
    修复：将返回值改为字典类型（而非自定义对象），避免属性访问报红
    获取服务器认证信息：匹配IP/主机名对应的连接配置
    """
    for host_config in remote_hosts:
        # 假设remote_hosts中每个元素是字典，包含"host"/"hostname"/"port"/"username"/"password"键
        if ip in [host_config.host, host_config.name]:
            # 返回标准连接字典，确保键与后续使用一致
            return {
                "host": host_config.host,  # 默认为目标IP
                "port": host_config.port,  # 默认为SSH默认端口22
                "username": host_config.username,
                "password": host_config.password
            }
    return None
