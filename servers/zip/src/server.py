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
from config.private.zip.config_loader import ZipConfig

mcp = FastMCP("Zip MCP Server", host="0.0.0.0", port=ZipConfig().get_config().private_config.port)
@mcp.tool(
    name="zip_extract_file_tool",
    description='''
    使用unzip命令解压zip文件
    1. 输入值如下：
        - host: 远程主机名称或IP地址，若不提供则表示对本机文件进行修改
        - file: 压缩包文件路径
        - extract_path: 指定解压目录
    2. 返回值为布尔值，表示解压操作是否成功
    '''
)
def zip_extract_file_tool(host: Union[str, None] = None, file: str = None, extract_path: str = None) -> bool:
    """使用unzip命令解压zip文件"""
    if host is None:
        if not file:
            if ZipConfig().get_config().public_config.language == LanguageEnum.ZH:
                raise ValueError("zip要解压缩的目标文件不能为空")
            else:
                raise ValueError("The target file for unzip cannot be empty")
        try:
            command = ['unzip', file]
            if extract_path:
                command.extend(['-d', extract_path])
            result = subprocess.run(command, capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            if ZipConfig().get_config().public_config.language == LanguageEnum.ZH:
                raise RuntimeError(f"执行 {command} 命令时发生未知错误: {str(e)}") from e
            else:
                raise RuntimeError(f"An unknown error occurred while executing the {command} command: {str(e)}") from e
    else:
        for host_config in ZipConfig().get_config().public_config.remote_hosts:
            if host == host_config.name or host == host_config.host:
                try:
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh.connect(
                        hostname=host_config.host,
                        port=host_config.port,
                        username=host_config.username,
                        password=host_config.password
                    )
                    if not file:
                        if ZipConfig().get_config().public_config.language == LanguageEnum.ZH:
                            raise ValueError("zip要解压的目标文件不能为空")
                        else:
                            raise ValueError("The target file for unzip cannot be empty")
                    if extract_path:
                        command = f'unzip {file} -d {extract_path}'
                    else:
                        command = f'unzip {file}'
                    stdin, stdout, stderr = ssh.exec_command(command, timeout=20)
                    error = stderr.read().decode().strip()
                    return not error
                except Exception as e:
                    raise ValueError(f"远程执行 {command} 失败: {str(e)}")
                finally:
                    if ssh is not None:
                        try:
                            ssh.close()
                        except Exception:
                            pass
        raise ValueError(f"未找到远程主机: {host}")

@mcp.tool(
    name="zip_compress_file_tool",
    description='''
    使用zip命令压缩文件或目录
    1. 输入值如下：
        - host: 远程主机名称或IP地址，若不提供则表示对本机文件进行压缩
        - source_path: 需要压缩的文件或目录路径
        - archive_path: 压缩包输出路径
    2. 返回值为布尔值，表示压缩操作是否成功
    '''
)
def zip_compress_file_tool(host: Union[str, None] = None, source_path: str = None, archive_path: str = None) -> bool:
    """使用zip命令压缩文件或目录"""
    if host is None:
        if not source_path or not archive_path:
            if ZipConfig().get_config().public_config.language == LanguageEnum.ZH:
                raise ValueError("zip要压缩的源文件/目录及输出路径不能为空")
            else:
                raise ValueError("The source file/directory and archive path for zip cannot be empty")
        try:
            command = ['zip', '-r', archive_path, source_path]
            result = subprocess.run(command, capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            if ZipConfig().get_config().public_config.language == LanguageEnum.ZH:
                raise RuntimeError(f"执行 {command} 命令时发生未知错误: {str(e)}") from e
            else:
                raise RuntimeError(f"An unknown error occurred while executing the {command} command: {str(e)}") from e
    else:
        for host_config in ZipConfig().get_config().public_config.remote_hosts:
            if host == host_config.name or host == host_config.host:
                try:
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh.connect(
                        hostname=host_config.host,
                        port=host_config.port,
                        username=host_config.username,
                        password=host_config.password
                    )
                    if not source_path or not archive_path:
                        if ZipConfig().get_config().public_config.language == LanguageEnum.ZH:
                            raise ValueError("zip要压缩的源文件/目录及输出路径不能为空")
                        else:
                            raise ValueError("The source file/directory and archive path for zip cannot be empty")
                    command = f'zip -r {archive_path} {source_path}'
                    stdin, stdout, stderr = ssh.exec_command(command, timeout=20)
                    error = stderr.read().decode().strip()
                    return not error
                except Exception as e:
                    raise ValueError(f"远程执行 {command} 失败: {str(e)}")
                finally:
                    if ssh is not None:
                        try:
                            ssh.close()
                        except Exception:
                            pass
        raise ValueError(f"未找到远程主机: {host}")

if __name__ == "__main__":
    mcp.run(transport='sse')