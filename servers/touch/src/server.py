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
from config.private.touch.config_loader import TouchConfig
mcp = FastMCP("Touch MCP Server", host="0.0.0.0", port=TouchConfig().get_config().private_config.port)


@mcp.tool(
    name="touch_create_files_tool"
    if TouchConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "touch_create_files_tool",
    description='''
    使用touch命令进行文件快速初始化、批量创建
    1. 输入值如下：
        - host: 远程主机名称或IP地址，若不提供则对本机进行操作
        - file: 创建的文件名
    2. 返回值为布尔值，表示touch操作是否成功
    '''
    if TouchConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    '''
    Using the touch command for quick file initialization, batch creation, and file timestamp calibration and simulation
    1. Input values are as follows:
        - host: The name or IP address of the remote host; if not provided, operations will be performed on the local machine
        - args: The list of parameters following touch
    2. The return value is a boolean indicating whether the touch operation was successful
    '''

)
def touch_create_files_tool(host: Union[str, None] = None, file: str = None) -> bool:
    """使用touch命令进行文件快速初始化、批量创建"""
    if host is None:
        try:
            command = ['touch']
            if not file:
                if TouchConfig().get_config().public_config.language == LanguageEnum.ZH:
                    raise ValueError(f"{command} 命令参数列表不能为空")
                else:
                    raise ValueError(f"{command} command parameter list cannot be empty")
            command.append(file)

            result = subprocess.run(command, capture_output=True, text=True)
            returncode = result.returncode
            if returncode == 0:
                return True
            else:
                return False
        except subprocess.CalledProcessError as e:
            if TouchConfig().get_config().public_config.language == LanguageEnum.ZH:
                raise RuntimeError(f"执行 {command} 命令失败: {e.stderr}") from e
            else:
                raise RuntimeError(f"Failed to execute command: {e.stderr}") from e
        except Exception as e:
            if TouchConfig().get_config().public_config.language == LanguageEnum.ZH:
                raise RuntimeError(f"执行 {command} 命令发生未知错误: {str(e)}") from e
            else:
                raise RuntimeError(f"Command {command} execution encountered an unknown error: {str(e)}") from e
    else:
        for host_config in TouchConfig().get_config().public_config.remote_hosts:
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
                    command = 'touch'
                    if not file:
                        raise ValueError(f"{command} 命令参数列表不能为空")
                    command += f' {file}'
                    stdin, stdout, stderr = ssh.exec_command(command)
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
        if TouchConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise ValueError(f"未找到远程主机: {host}")
        else:
            raise ValueError(f"Remote host not found: {host}")

@mcp.tool(
    name="touch_timestamp_files_tool"
    if TouchConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "touch_timestamp_files_tool",
    description='''
    使用touch命令进行文件时间戳校准与模拟
    1. 输入值如下：
        - host: 远程主机名称或IP地址，若不提供则对本机进行操作
        - options: 更新访问时间\更新修改时间
        - file: 文件名
    2. 返回值为布尔值，表示touch操作是否成功
    '''
    if TouchConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    '''
    Using the touch command for quick file initialization, batch creation, and file timestamp calibration and simulation
    1. Input values are as follows:
        - host: The name or IP address of the remote host; if not provided, operations will be performed on the local machine
        - args: The list of parameters following touch
    2. The return value is a boolean indicating whether the touch operation was successful
    '''

)
def touch_timestamp_files_tool(host: Union[str, None] = None, options: str = None, file: str = None) -> bool:
    """使用touch命令进行文件时间戳校准与模拟"""
    if host is None:
        try:
            command = ['touch']
            if not options or not file:
                if TouchConfig().get_config().public_config.language == LanguageEnum.ZH:
                    raise ValueError(f"{command} 命令参数列表不能为空")
                else:
                    raise ValueError(f"{command} command parameter list cannot be empty")
            command.append(options)
            command.append(file)
            result = subprocess.run(command, capture_output=True, text=True)
            returncode = result.returncode
            if returncode == 0:
                return True
            else:
                return False
        except subprocess.CalledProcessError as e:
            if TouchConfig().get_config().public_config.language == LanguageEnum.ZH:
                raise RuntimeError(f"执行 {command} 命令失败: {e.stderr}") from e
            else:
                raise RuntimeError(f"Failed to execute command: {e.stderr}") from e
        except Exception as e:
            if TouchConfig().get_config().public_config.language == LanguageEnum.ZH:
                raise RuntimeError(f"执行 {command} 命令发生未知错误: {str(e)}") from e
            else:
                raise RuntimeError(f"Command {command} execution encountered an unknown error: {str(e)}") from e
    else:
        for host_config in TouchConfig().get_config().public_config.remote_hosts:
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
                    command = 'touch'
                    if not options or not file:
                        if TouchConfig().get_config().public_config.language == LanguageEnum.ZH:
                            raise ValueError(f"{command} 命令参数列表不能为空")
                        else:
                            raise ValueError(f"{command} command parameter list cannot be empty")
                    command += f' {options} {file}'
                    stdin, stdout, stderr = ssh.exec_command(command)
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
        if TouchConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise ValueError(f"未找到远程主机: {host}")
        else:
            raise ValueError(f"Remote host not found: {host}")


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='sse')
