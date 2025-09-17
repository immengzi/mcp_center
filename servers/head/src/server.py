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
from config.private.head.config_loader import HeadConfig
mcp = FastMCP("Head MCP Server", host="0.0.0.0", port=HeadConfig().get_config().private_config.port)


@mcp.tool(
    name="head_file_view_tool"
    if HeadConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "head_file_view_tool",
    description='''
    使用head命令快速查看文件开头部分内容
    1. 输入值如下：
        - host: 远程主机名称或IP地址，若不提供则表示查看本机指定文件内容
        - num: 想要查看的行数，不指定默认查看前10行
        - file: 要查看的文件
    2. 返回值为字符串，为返回的文件内容
    '''
    if HeadConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    '''
    Use the head command to quickly view the beginning part of a file
    1. The input values are as follows:
        - host: The name or IP address of the remote host. If not provided, it indicates viewing the content of a specified file on the local machine.
        - num: The number of lines you want to view. If not specified, the default is to view the first 10 lines.
        - file: The file you want to view.
    2. The return value is a string, which is the content of the file returned.
    '''

)
def head_file_view_tool(host: Union[str, None] = None, num: int = 10, file: str = None) -> str:
    """使用head命令快速查看文件开头部分内容"""
    if host is None:
        try:
            command = ['head', '-n', f'{num}', f'{file}']
            result = subprocess.run(command, capture_output=True, text=True)
            lines = result.stdout
            return lines
        except Exception as e:
            if HeadConfig().get_config().public_config.language == LanguageEnum.ZH:
                raise RuntimeError(f"获取 {command} 输出信息时发生未知错误: {str(e)}") from e
            else:
                raise RuntimeError(f"An unknown error occurred while retrieving the output information for {command} : {str(e)}") from e
    else:
        for host_config in HeadConfig().get_config().public_config.remote_hosts:
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
                    command = f'head -n {num} {file}'
                    stdin, stdout, stderr = ssh.exec_command(command, timeout=10)
                    error = stderr.read().decode().strip()
                    result = stdout.read().decode().strip()
                    if error:
                        raise ValueError(f"执行命令 {command} 错误：{error}")
                    return result
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
        if HeadConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise ValueError(f"未找到远程主机: {host}")
        else:
            raise ValueError(f"Remote host not found: {host}")


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='sse')
