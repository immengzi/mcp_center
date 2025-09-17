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
from config.private.sed.config_loader import SedConfig

mcp = FastMCP("Sed MCP Server", host="0.0.0.0", port=SedConfig().get_config().private_config.port)


@mcp.tool(
    name="sed_text_replace_tool"
    if SedConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "sed_text_replace_tool",
    description='''
    使用sed命令进行文本替换操作
    1. 输入值如下：
        - host: 远程主机名称或IP地址，若不提供则表示对本机文件进行操作
        - options: sed选项（可选），如"-i"直接修改文件等
        - pattern: 要替换的模式（支持正则表达式）
        - replacement: 替换后的文本
        - file: 要操作的文件路径
    2. 返回值为布尔值，表示操作是否成功
    '''
    if SedConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    '''
    Use the sed command to perform text replacement operations
    1. Input values are as follows:
        - host: The name or IP address of the remote host; if not provided, it indicates operating on a local file
        - options: sed options (optional), such as "-i" to modify the file directly
        - pattern: The pattern to replace (supports regular expressions)
        - replacement: The text to replace with
        - file: The file path to operate on
    2. The return value is a boolean indicating whether the operation was successful
    '''

)
def sed_text_replace_tool(host: Union[str, None] = None, options: Union[str, None] = None, pattern: str = None, replacement: str = None, file: str = None) -> bool:
    """使用sed命令进行文本替换操作"""
    if host is None:
        try:
            # 构建sed命令
            command = ['sed']
            if options:
                command.extend(options.split())
            # 转义替换文本中的特殊字符
            escaped_pattern = pattern.replace('/', r'\/')
            escaped_replacement = replacement.replace('/', r'\/')
            command.append(f's/{escaped_pattern}/{escaped_replacement}/g')
            command.append(file)
            
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode == 0:
                return True
            else:
                # 错误处理
                error_msg = result.stderr.strip()
                if SedConfig().get_config().public_config.language == LanguageEnum.ZH:
                    raise RuntimeError(f"执行sed命令时发生错误: {error_msg}")
                else:
                    raise RuntimeError(f"Error executing sed command: {error_msg}")
        except Exception as e:
            if SedConfig().get_config().public_config.language == LanguageEnum.ZH:
                raise RuntimeError(f"执行sed命令时发生未知错误: {str(e)}") from e
            else:
                raise RuntimeError(f"An unknown error occurred while executing sed command: {str(e)}") from e
    else:
        for host_config in SedConfig().get_config().public_config.remote_hosts:
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
                    
                    # 构建远程sed命令
                    sed_command = f'sed'
                    if options:
                        sed_command += f' {options}'
                    # 转义替换文本中的特殊字符
                    escaped_pattern = pattern.replace("'", "'\"'\"'")
                    escaped_replacement = replacement.replace("'", "'\"'\"'")
                    sed_command += f" 's/{escaped_pattern}/{escaped_replacement}/g' {file}"
                    
                    stdin, stdout, stderr = ssh.exec_command(sed_command, timeout=30)
                    error = stderr.read().decode().strip()
                    result = stdout.read().decode().strip()
                    
                    if error and "No such file or directory" in error:
                        if SedConfig().get_config().public_config.language == LanguageEnum.ZH:
                            raise ValueError(f"文件不存在: {file}")
                        else:
                            raise ValueError(f"File not found: {file}")
                    elif error:
                        raise ValueError(f"执行命令 {sed_command} 错误：{error}")
                    
                    return True
                except paramiko.AuthenticationException:
                    raise ValueError("SSH认证失败，请检查用户名和密码")
                except paramiko.SSHException as e:
                    raise ValueError(f"SSH连接错误: {str(e)}")
                except Exception as e:
                    raise ValueError(f"远程执行 {sed_command} 失败: {str(e)}")
                finally:
                    # 确保SSH连接关闭
                    if ssh is not None:
                        try:
                            ssh.close()
                        except Exception:
                            pass
        if SedConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise ValueError(f"未找到远程主机: {host}")
        else:
            raise ValueError(f"Remote host not found: {host}")


@mcp.tool(
    name="sed_text_delete_tool"
    if SedConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "sed_text_delete_tool",
    description='''
    使用sed命令删除文件中的文本行
    1. 输入值如下：
        - host: 远程主机名称或IP地址，若不提供则表示对本机文件进行操作
        - options: sed选项（可选），如"-i"直接修改文件等
        - pattern: 要删除的行的模式（支持正则表达式）
        - file: 要操作的文件路径
    2. 返回值为布尔值，表示操作是否成功
    '''
    if SedConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    '''
    Use the sed command to delete text lines from a file
    1. Input values are as follows:
        - host: The name or IP address of the remote host; if not provided, it indicates operating on a local file
        - options: sed options (optional), such as "-i" to modify the file directly
        - pattern: The pattern of lines to delete (supports regular expressions)
        - file: The file path to operate on
    2. The return value is a boolean indicating whether the operation was successful
    '''

)
def sed_text_delete_tool(host: Union[str, None] = None, options: Union[str, None] = None, pattern: str = None, file: str = None) -> bool:
    """使用sed命令删除文件中的文本行"""
    if host is None:
        try:
            # 构建sed命令
            command = ['sed']
            if options:
                command.extend(options.split())
            command.append(f'/{pattern}/d')
            command.append(file)
            
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode == 0:
                return True
            else:
                # 错误处理
                error_msg = result.stderr.strip()
                if SedConfig().get_config().public_config.language == LanguageEnum.ZH:
                    raise RuntimeError(f"执行sed命令时发生错误: {error_msg}")
                else:
                    raise RuntimeError(f"Error executing sed command: {error_msg}")
        except Exception as e:
            if SedConfig().get_config().public_config.language == LanguageEnum.ZH:
                raise RuntimeError(f"执行sed命令时发生未知错误: {str(e)}") from e
            else:
                raise RuntimeError(f"An unknown error occurred while executing sed command: {str(e)}") from e
    else:
        for host_config in SedConfig().get_config().public_config.remote_hosts:
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
                    
                    # 构建远程sed命令
                    sed_command = f'sed'
                    if options:
                        sed_command += f' {options}'
                    # 转义模式中的特殊字符
                    escaped_pattern = pattern.replace("'", "'\"'\"'")
                    sed_command += f" '/{escaped_pattern}/d' {file}"
                    
                    stdin, stdout, stderr = ssh.exec_command(sed_command, timeout=30)
                    error = stderr.read().decode().strip()
                    result = stdout.read().decode().strip()
                    
                    if error and "No such file or directory" in error:
                        if SedConfig().get_config().public_config.language == LanguageEnum.ZH:
                            raise ValueError(f"文件不存在: {file}")
                        else:
                            raise ValueError(f"File not found: {file}")
                    elif error:
                        raise ValueError(f"执行命令 {sed_command} 错误：{error}")
                    
                    return True
                except paramiko.AuthenticationException:
                    raise ValueError("SSH认证失败，请检查用户名和密码")
                except paramiko.SSHException as e:
                    raise ValueError(f"SSH连接错误: {str(e)}")
                except Exception as e:
                    raise ValueError(f"远程执行 {sed_command} 失败: {str(e)}")
                finally:
                    # 确保SSH连接关闭
                    if ssh is not None:
                        try:
                            ssh.close()
                        except Exception:
                            pass
        if SedConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise ValueError(f"未找到远程主机: {host}")
        else:
            raise ValueError(f"Remote host not found: {host}")


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='sse')