"""公共基础层：封装所有维度都需要的复用逻辑"""
import paramiko
from datetime import datetime
from typing import Dict, Optional, Tuple

from config.private.top.config_loader import TopCommandConfig
from config.public.base_config_loader import LanguageEnum, RemoteConfigModel

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
    

def get_server_auth(ip: str, host_configs : list[RemoteConfigModel]) -> Optional[RemoteConfigModel] :
    """获取指定服务器的认证信息，支持本地服务器特殊处理"""
    if ip in ("127.0.0.1", "localhost") or ip is None:
        return None
    for host_config in host_configs:
        
        if ip == host_config.name or ip == host_config.host:
            return host_config
        
    raise ValueError(f"服务器 {ip} 未在配置文件中定义"if TopCommandConfig().get_config(
                        ).public_config.language == LanguageEnum.ZH else f"Server {ip} is not defined in the configuration file")
        
        