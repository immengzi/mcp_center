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
from config.private.top.config_loader import TopConfig
mcp = FastMCP("Perf_Svg MCP Server", host="0.0.0.0", port=TopConfig().get_config().private_config.port)


@mcp.tool(
    name="find_collect_tool"
    if TopConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "find_collect_tool",
    description='''
    使用find命令基于名称、尺寸、日期和权限在指定目录下查找文件
    1. 输入值如下：
        - host: 远程主机名称或IP地址，若不提供则对本机进行分析
        - path: 指定查找的目录
        - args: find后跟的限定参数列表
    2. 返回值为包含相应信息的字典列表，每个字典包含以下键
        - file: 符合查找要求的具体文件路径
    '''
    if TopConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    '''
    Use the `find` command to search for files in a specified directory based on name, size, date, and permissions.
    1. Input values are as follows:
        - `host`: The name or IP address of the remote host; if not provided, the analysis is performed on the local machine.
        - `path`: The directory to be searched.
        - `args`: The list of limiting parameters following `find`.
    2. The return value is a list of dictionaries containing the corresponding information, with each dictionary including the following keys:
        - `file`: The specific file path that meets the search criteria.
    '''

)
def find_collect_tool(host: Union[str, None] = None, path: str = None, args: List[str] = []) -> List[Dict[str, Any]]:
    """使用find命令基于名称、尺寸、日期和权限在指定目录下查找文件"""
    if host is None:
        try:
            command = ['find']
            if path is None:
                raise ValueError(f"{command} 命令查找路径不能为空")
            command.append(path)
            command.extend([arg for arg in args if arg is not None])

            result = subprocess.run(command, capture_output=True, text=True)
            lines = result.stdout.split('\n')
            files = []
            if lines != ['']:
                for line in lines:
                    files.append({
                        'file': line
                    })
            return files
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"执行 {command} 命令失败: {e.stderr}") from e
        except Exception as e:
            raise RuntimeError(f"执行 {command} 命令发生未知错误: {str(e)}") from e
    else:
        for host_config in TopConfig().get_config().public_config.remote_hosts:
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
                    command = ['find']
                    if path is None:
                        raise ValueError(f"{command} 命令查找路径不能为空")
                    command.append(path)
                    command.extend([arg for arg in args if arg is not None])
                    stdin, stdout, stderr = ssh.exec_command(command)
                    error = stderr.read().decode().strip()
                    output = stdout.read().decode().strip()

                    if error:
                        raise ValueError(f"Command {command} error: {error}")
                    # 没有找到相应文件
                    # if not output:
                    #     raise ValueError("未能获取信息")
                    
                    lines = output.stdout.split('\n')
                    files = []
                    if lines != ['']:
                        for line in lines:
                            files.append({
                                'file': line
                            })
                    return files
                except paramiko.AuthenticationException:
                    raise ValueError("SSH认证失败，请检查用户名和密码")
                except paramiko.SSHException as e:
                    raise ValueError(f"SSH连接错误: {str(e)}")
                except Exception as e:
                    raise ValueError(f"获取远程内存信息失败: {str(e)}")
                finally:
                    # 确保SSH连接关闭
                    if ssh is not None:
                        try:
                            ssh.close()
                        except Exception:
                            pass
        if TopConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise ValueError(f"未找到远程主机: {host}")
        else:
            raise ValueError(f"Remote host not found: {host}")


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='sse')
