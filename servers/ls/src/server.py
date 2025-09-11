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
from config.private.ls.config_loader import LsConfig
mcp = FastMCP("Ls MCP Server", host="0.0.0.0", port=LsConfig().get_config().private_config.port)


@mcp.tool(
    name="ls_collect_tool"
    if LsConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "ls_collect_tool",
    description='''
    使用ls命令列出目录内容
    1. 输入值如下：
        - host: 远程主机名称或IP地址，若不提供则对本机进行操作
        - file: 目标文件/目录
    2. 返回值为目标目录内容的列表
    '''
    if LsConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    '''
    Use the `ls` command to list the contents of a directory
    1. Input values are as follows:
        - host: The name or IP address of the remote host; if not provided, the operation is performed on the local machine.
        - file: The target file/directory.
    2. The return value is a list of the contents of the target directory
    '''

)
def ls_collect_tool(host: Union[str, None] = None, file: str = './') -> List[Dict[str, Any]]:
    """使用ls命令列出目录内容"""
    if host is None:
        try:
            command = ['ls']
            command.append(file)

            result = subprocess.run(command, capture_output=True, text=True)
            lines = result.stdout.split('\n')
            file_list = []
            for line in lines:
                file_list.append({
                    "name": line
                })
            return file_list
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"执行 {command} 命令失败: {e.stderr}") from e
        except Exception as e:
            raise RuntimeError(f"执行 {command} 命令发生未知错误: {str(e)}") from e
    else:
        for host_config in LsConfig().get_config().public_config.remote_hosts:
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
                    command = 'ls'
                    command += f' {file}'
                    stdin, stdout, stderr = ssh.exec_command(command, timeout = 20)
                    error = stderr.read().decode().strip()
                    output = stdout.read().decode().strip()
                    lines = output.split('\n')
                    file_list = []
                    for line in lines:
                        file_list.append({
                            "name": line
                        })
                    return file_list
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
        if LsConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise ValueError(f"未找到远程主机: {host}")
        else:
            raise ValueError(f"Remote host not found: {host}")


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='sse')
