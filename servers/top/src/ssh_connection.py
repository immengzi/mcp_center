"""SSH连接管理（上下文管理器实现）"""
import paramiko
from typing import Optional, Tuple,Union
from config.public.base_config_loader import LanguageEnum
from config.private.top.config_loader import TopCommandConfig

class SSHConnection:
    """SSH连接管理类：自动处理连接建立与关闭，避免资源泄露"""
    
    def __init__(self, ip: str, port: int = 22, username: str = "root", 
                 password: Optional[str] = None, ssh_key: Optional[str] = None):
        self.ip = ip
        self.port = port
        self.username = username
        self.password = password
        self.ssh_key = ssh_key
        self.conn = None
        
    def __enter__(self) -> Tuple[bool, Union[paramiko.SSHClient, str]]:
        """上下文管理器：获取连接"""
        try:
            self.conn = paramiko.SSHClient()
            self.conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # 优先使用密钥认证
            if self.ssh_key:
                self.conn.connect(
                    hostname=self.ip,
                    port=self.port,
                    username=self.username,
                    key_filename=self.ssh_key,
                    timeout=10
                )
            elif self.password:
                self.conn.connect(
                    hostname=self.ip,
                    port=self.port,
                    username=self.username,
                    password=self.password,
                    timeout=10
                )
            else:
                return False, "缺少认证信息（密钥或密码）"if TopCommandConfig().get_config().public_config.language == LanguageEnum.ZH else "Missing authentication information (key or password)"
                
            return True, self.conn
            
        except Exception as e:
            return False, f"SSH连接失败：{str(e)}"if TopCommandConfig().get_config().public_config.language == LanguageEnum.ZH else f"SSH connection failed: {str(e)}"
            
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器：自动关闭连接"""
        if self.conn:
            self.conn.close()