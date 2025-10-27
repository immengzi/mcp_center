from asyncio.log import logger
import paramiko
import os
from typing import Dict, Optional, Tuple
from config.private.file_transfer.config_loader import FileTransferConfig
from config.public.base_config_loader import LanguageEnum

def get_language() -> bool:
    """获取语言配置：True=中文，False=英文"""
    return FileTransferConfig().get_config().public_config.language == LanguageEnum.ZH


def get_remote_config(host: str) -> Optional[Dict]:
    """从配置文件获取远程主机完整配置（仅包含host, port, username, password）"""
    remote_hosts = FileTransferConfig().get_config().public_config.remote_hosts
    for host_config in remote_hosts:
        if host == host_config.host or host == host_config.name:
            return {
                "host": host_config.host,
                "port": host_config.port or 22,
                "username": host_config.username,
                "password": host_config.password
            }
    return None


def validate_local_path(path: str, is_directory: bool = False) -> Tuple[bool, str]:
    """验证本地路径有效性"""
    is_zh = get_language()
    if not path:
        return False, "路径不能为空" if is_zh else "Path cannot be empty"
    
    # 检查路径是否存在
    if os.path.exists(path):
        if is_directory and not os.path.isdir(path):
            return False, f"路径{path}不是目录" if is_zh else f"Path {path} is not a directory"
        if not is_directory and not os.path.isfile(path):
            return False, f"路径{path}不是文件" if is_zh else f"Path {path} is not a file"
        return True, ""
    
    # 检查父目录是否可写（用于新建文件/目录）
    parent_dir = os.path.dirname(path) if not is_directory else path
    parent_dir = parent_dir or "."
    
    if not os.path.exists(parent_dir):
        return False, f"父目录{parent_dir}不存在" if is_zh else f"Parent directory {parent_dir} does not exist"
    if not os.access(parent_dir, os.W_OK):
        return False, f"没有权限写入目录{parent_dir}" if is_zh else f"No permission to write to directory {parent_dir}"
    
    return True, ""


def create_ssh_connection(host: str) -> Optional[paramiko.SSHClient]:
    """创建SSH连接（仅从配置文件获取认证信息）"""
    # 获取配置
    config = get_remote_config(host)
    if not config:
        logger.error(f"未找到主机{host}的配置信息")
        return None
        
    # 验证配置完整性
    required_fields = ["username", "password"]
    for field in required_fields:
        if not config.get(field):
            logger.error(f"主机{host}的配置缺少{field}")
            return None

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=config["host"],
            port=config["port"],
            username=config["username"],
            password=config["password"],
            banner_timeout=10
        )
        return ssh
    except paramiko.AuthenticationException:
        logger.error(f"主机{host}认证失败：用户名或密码错误")
    except Exception as e:
        logger.error(f"连接主机{host}失败：{str(e)}")
    return None