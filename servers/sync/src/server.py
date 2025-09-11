from typing import Union, List, Dict
import platform
import os
import paramiko
import yaml
import datetime
import subprocess
from typing import Any, Dict
import psutil
import tempfile
from datetime import datetime
from mcp.server import FastMCP
from config.public.base_config_loader import LanguageEnum
from config.private.sync.config_loader import SyncConfig
mcp = FastMCP("Sync MCP Server", host="0.0.0.0", port=SyncConfig().get_config().private_config.port)


@mcp.tool(
    name="sync_refresh_data_tool"
    if SyncConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "sync_refresh_data_tool",
    description='''
    使用sync命令将缓存的数据写入磁盘中
    1. 输入值如下：
        - host: 远程主机名称或IP地址，若不提供则表示刷新本机缓存数据
    2. 返回值为布尔值，表示缓存数据是否刷新成功
    '''
    if SyncConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    '''
    Use the sync command to write cached data to the disk.
    1. The input values are as follows:
        - host: The name or IP address of the remote host. If not provided, it indicates refreshing the local cache data.
    2. The return value is a boolean indicating whether the cache data was successfully refreshed.
    '''
)
def sync_refresh_data_tool(host: Union[str, None] = None) -> bool:
    """使用sync命令将缓存的数据写入磁盘"""
    if host is None:
        try:
            command = ['sync']
            result = subprocess.run(command, capture_output=True, text=True)
            returncode = result.returncode
            if returncode == 0:
                return True
            else:
                return False
        except subprocess.CalledProcessError as e:
            if SyncConfig().get_config().public_config.language == LanguageEnum.ZH:
                raise RuntimeError(f"执行 {command} 命令失败: {e.stderr}")
            else:
                raise RuntimeError(f"Command {command} execution failed: {e.stderr}")
        except Exception as e:
            if SyncConfig().get_config().public_config.language == LanguageEnum.ZH:
                raise RuntimeError(f"执行 {command} 命令时发生未知错误: {str(e)}")
            else:
                raise RuntimeError(f"An unknown error occurred while executing the {command} command: {str(e)}")
    else:
        for host_config in SyncConfig().get_config().public_config.remote_hosts:
            if host == host_config.name or host == host_config.host:
                try:
                    # 建立SSH连接
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh.connect(
                        hostname=host_config.host,
                        port=host_config.port,
                        username=host_config.username,
                        password=host_config.password
                    )
                    command = 'sync'
                    stdin, stdout, stderr = ssh.exec_command(command, timeout = 20)
                    error = stderr.read().decode().strip()

                    if error:
                        return False
                    else:
                        return True
                except paramiko.AuthenticationException:
                    raise ValueError("SSH认证失败，请检查用户名和密码")
                except paramiko.SSHException as e:
                    raise ValueError(f"SSH连接错误: {str(e)}")
                except Exception as e:
                    raise ValueError(f"远程执行 {command} 失败: {str(e)}")
                finally:
                    # 确保SSH连接关闭
                    if ssh is not None:
                        try:
                            ssh.close()
                        except Exception:
                            pass
        if SyncConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise ValueError(f"未找到远程主机: {host}")
        else:
            raise ValueError(f"Remote host not found: {host}")


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='sse')
