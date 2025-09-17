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
from config.private.grep.config_loader import GrepConfig
mcp = FastMCP("Grep MCP Server", host="0.0.0.0", port=GrepConfig().get_config().private_config.port)


@mcp.tool(
    name="grep_search_tool"
    if GrepConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "grep_search_tool",
    description='''
    使用grep命令搜索文件内容
    1. 输入值如下：
        - host: 远程主机名称或IP地址，若不提供则表示搜索本机文件内容
        - options: grep选项（可选），如"-i"忽略大小写，"-n"显示行号等
        - pattern: 要搜索的模式（支持正则表达式）
        - file: 要搜索的文件路径
    2. 返回值为字符串，包含匹配的行
    '''
    if GrepConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    '''
    Use the grep command to search file contents
    1. Input values are as follows:
        - host: The name or IP address of the remote host; if not provided, it indicates searching the contents of a local file
        - options: grep options (optional), such as "-i" for case insensitive, "-n" for line numbers, etc.
        - pattern: The pattern to search for (supports regular expressions)
        - file: The file path to search
    2. The return value is a string containing the matching lines
    '''

)
def grep_search_tool(host: Union[str, None] = None, options: Union[str, None] = None, pattern: str = None, file: str = None) -> str:
    """使用grep命令搜索文件内容"""
    if host is None:
        try:
            # 构建grep命令
            command = ['grep']
            if options:
                command.extend(options.split())
            command.extend([pattern, file])
            
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout
            elif result.returncode == 1:
                # grep返回1表示没有找到匹配项
                if GrepConfig().get_config().public_config.language == LanguageEnum.ZH:
                    return f"在文件 {file} 中未找到模式 '{pattern}' 的匹配项"
                else:
                    return f"No matches found for pattern '{pattern}' in file {file}"
            else:
                # 其他错误
                error_msg = result.stderr.strip()
                if GrepConfig().get_config().public_config.language == LanguageEnum.ZH:
                    raise RuntimeError(f"执行grep命令时发生错误: {error_msg}")
                else:
                    raise RuntimeError(f"Error executing grep command: {error_msg}")
        except Exception as e:
            if GrepConfig().get_config().public_config.language == LanguageEnum.ZH:
                raise RuntimeError(f"执行grep命令时发生未知错误: {str(e)}") from e
            else:
                raise RuntimeError(f"An unknown error occurred while executing grep command: {str(e)}") from e
    else:
        for host_config in GrepConfig().get_config().public_config.remote_hosts:
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
                    
                    # 构建远程grep命令
                    grep_command = f'grep'
                    if options:
                        grep_command += f' {options}'
                    grep_command += f" '{pattern}' {file}"
                    
                    stdin, stdout, stderr = ssh.exec_command(grep_command, timeout=30)
                    error = stderr.read().decode().strip()
                    result = stdout.read().decode().strip()
                    
                    if error and "No such file or directory" in error:
                        if GrepConfig().get_config().public_config.language == LanguageEnum.ZH:
                            raise ValueError(f"文件不存在: {file}")
                        else:
                            raise ValueError(f"File not found: {file}")
                    elif error:
                        raise ValueError(f"执行命令 {grep_command} 错误：{error}")
                    
                    if not result:
                        if GrepConfig().get_config().public_config.language == LanguageEnum.ZH:
                            return f"在文件 {file} 中未找到模式 '{pattern}' 的匹配项"
                        else:
                            return f"No matches found for pattern '{pattern}' in file {file}"
                    
                    return result
                except paramiko.AuthenticationException:
                    raise ValueError("SSH认证失败，请检查用户名和密码")
                except paramiko.SSHException as e:
                    raise ValueError(f"SSH连接错误: {str(e)}")
                except Exception as e:
                    raise ValueError(f"远程执行 {grep_command} 失败: {str(e)}")
                finally:
                    # 确保SSH连接关闭
                    if ssh is not None:
                        try:
                            ssh.close()
                        except Exception:
                            pass
        if GrepConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise ValueError(f"未找到远程主机: {host}")
        else:
            raise ValueError(f"Remote host not found: {host}")


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='sse')
