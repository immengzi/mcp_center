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
from config.private.fallocate.config_loader import FallocateConfig
mcp = FastMCP("Fallocate MCP Server", host="0.0.0.0", port=FallocateConfig().get_config().private_config.port)


@mcp.tool(
    name="fallocate_create_file_tool"
    if FallocateConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "fallocate_create_file_tool",
    description='''
    使用fallocate命令临时创建并启用swap文件
    1. 输入值如下：
        - host: 远程主机名称或IP地址，若不提供则表示在本机临时创建并启用swap文件
        - name: swap空间对应的设备或文件路径
        - size: 创建的swap空间大小
    2. 返回值为布尔值，表示创建启用swap文件是否成功
    '''
    if FallocateConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    '''
    Use the fallocate command to temporarily create and enable a swap file.
    1. Input values as follows:
        - host: The name or IP address of the remote host. If not provided, it indicates that the swap file will be temporarily created and enabled on the local machine.
        - name: The device or file path corresponding to the swap space.
        - size: The size of the swap space to be created.
    2. The return value is a boolean indicating whether the creation and enabling of the swap file was successful.
    '''
)
def fallocate_create_file_tool(host: Union[str, None] = None, name: str = None, size: str = None) -> bool:
    """使用fallocate命令临时创建并启用swap文件"""
    if host is None:
        if not name or not size:
            if FallocateConfig().get_config().public_config.language == LanguageEnum.ZH:
                raise ValueError("临时创建swap文件的文件路径或大小不能为空")
            else:
                raise ValueError("The file path or size for temporarily creating a swap file cannot be empty.")
        try:
            cmd_fallocate = ['fallocate']
            cmd_fallocate.append('-l')
            cmd_fallocate.append(size)
            cmd_fallocate.append(name)
            result = subprocess.run(cmd_fallocate, capture_output=True, text=True)
            returncode = result.returncode
            if returncode != 0:
                return False
        except subprocess.CalledProcessError as e:
            if FallocateConfig().get_config().public_config.language == LanguageEnum.ZH:
                raise RuntimeError(f"执行 {cmd_fallocate} 命令失败: {e.stderr}") from e
            else:
                raise RuntimeError(f"Failed to execute the free command: {e.stderr}") from e
        except Exception as e:
            if FallocateConfig().get_config().public_config.language == LanguageEnum.ZH:
                raise RuntimeError(f"执行 {cmd_fallocate} 命令时发生未知错误: {str(e)}") from e
            else:
                raise RuntimeError(f"An unknown error occurred while obtaining memory information: {str(e)}") from e
        
        try:
            cmd_chmod = ['chmod']
            cmd_chmod.append('600')
            cmd_chmod.append(name)
            result = subprocess.run(cmd_chmod, capture_output=True, text=True)
            returncode = result.returncode
            if returncode != 0:
                return False
        except subprocess.CalledProcessError as e:
            if FallocateConfig().get_config().public_config.language == LanguageEnum.ZH:
                raise RuntimeError(f"执行 {cmd_fallocate} 命令失败: {e.stderr}") from e
            else:
                raise RuntimeError(f"Failed to execute the free command: {e.stderr}") from e
        except Exception as e:
            if FallocateConfig().get_config().public_config.language == LanguageEnum.ZH:
                raise RuntimeError(f"执行 {cmd_fallocate} 命令时发生未知错误: {str(e)}") from e
            else:
                raise RuntimeError(f"An unknown error occurred while obtaining memory information: {str(e)}") from e

        try:
            cmd_mkswap = ['mkswap']
            cmd_mkswap.append(name)
            result = subprocess.run(cmd_mkswap, capture_output=True, text=True)
            returncode = result.returncode
            if returncode != 0:
                return False
        except subprocess.CalledProcessError as e:
            if FallocateConfig().get_config().public_config.language == LanguageEnum.ZH:
                raise RuntimeError(f"执行 {cmd_fallocate} 命令失败: {e.stderr}") from e
            else:
                raise RuntimeError(f"Failed to execute the free command: {e.stderr}") from e
        except Exception as e:
            if FallocateConfig().get_config().public_config.language == LanguageEnum.ZH:
                raise RuntimeError(f"执行 {cmd_fallocate} 命令时发生未知错误: {str(e)}") from e
            else:
                raise RuntimeError(f"An unknown error occurred while obtaining memory information: {str(e)}") from e

        try:
            cmd_swapon = ['swapon']
            cmd_swapon.append(name)
            result = subprocess.run(cmd_swapon, capture_output=True, text=True)
            returncode = result.returncode
            if returncode != 0:
                return False
        except subprocess.CalledProcessError as e:
            if FallocateConfig().get_config().public_config.language == LanguageEnum.ZH:
                raise RuntimeError(f"执行 {cmd_fallocate} 命令失败: {e.stderr}") from e
            else:
                raise RuntimeError(f"Failed to execute the free command: {e.stderr}") from e
        except Exception as e:
            if FallocateConfig().get_config().public_config.language == LanguageEnum.ZH:
                raise RuntimeError(f"执行 {cmd_fallocate} 命令时发生未知错误: {str(e)}") from e
            else:
                raise RuntimeError(f"An unknown error occurred while obtaining memory information: {str(e)}") from e

        return True
    else:
        for host_config in FallocateConfig().get_config().public_config.remote_hosts:
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

                    if not name or not size:
                        if FallocateConfig().get_config().public_config.language == LanguageEnum.ZH:
                            raise ValueError("临时创建swap文件的文件路径或大小不能为空")
                        else:
                            raise ValueError("The file path or size for temporarily creating a swap file cannot be empty.")

                    cmd_fallocate = 'fallocate'
                    cmd_fallocate += ' -l'
                    cmd_fallocate += f' {size}'
                    cmd_fallocate += f' {name}'
                    stdin, stdout, stderr = ssh.exec_command(cmd_fallocate, timeout = 20)
                    error = stderr.read().decode().strip()
                    if error:
                        return False
                    
                    cmd_chmod = 'chmod'
                    cmd_chmod += ' 600'
                    cmd_chmod += f' {name}'
                    stdin, stdout, stderr = ssh.exec_command(cmd_chmod, timeout = 20)
                    error = stderr.read().decode().strip()
                    if error:
                        return False

                    cmd_mkswap = 'mkswap'
                    cmd_mkswap += f' {name}'
                    stdin, stdout, stderr = ssh.exec_command(cmd_mkswap, timeout = 20)
                    error = stderr.read().decode().strip()
                    if error:
                        return False
                    
                    cmd_swapon = 'swapon'
                    cmd_swapon += f' {name}'
                    stdin, stdout, stderr = ssh.exec_command(cmd_swapon, timeout = 20)
                    error = stderr.read().decode().strip()
                    if error:
                        return False
                    
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
        if FallocateConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise ValueError(f"未找到远程主机: {host}")
        else:
            raise ValueError(f"Remote host not found: {host}")


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='sse')
