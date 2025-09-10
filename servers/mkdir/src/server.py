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
    name="mkdir_collect_tool"
    if TopConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "mkdir_collect_tool",
    description='''
    使用mkdir命令进行目录创建、支持批量创建、设置权限、递归创建多级目录
    1. 输入值如下：
        - host: 远程主机名称或IP地址，若不提供则对本机进行操作
        - args: mkdir后跟的参数列表
    2. 返回值为布尔值，表示mkdir操作是否成功
    '''
    if TopConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    '''
    Using the mkdir command for quick file initialization, batch creation, and file timestamp calibration and simulation
    1. Input values are as follows:
        - host: The name or IP address of the remote host; if not provided, operations will be performed on the local machine
        - args: The list of parameters following mkdir
    2. The return value is a boolean indicating whether the mkdir operation was successful
    '''

)
def mkdir_collect_tool(host: Union[str, None] = None, args: List[str] = []) -> bool:
    """使用mkdir命令基于名称、尺寸、日期和权限在指定目录下查找文件"""
    if host is None:
        try:
            command = ['mkdir']
            if args == []:
                raise ValueError(f"{command} 命令参数列表不能为空")
            command.extend([arg for arg in args if arg is not None])
            # print(f"Running command: {' '.join(command)}")

            result = subprocess.run(command, capture_output=True, text=True)
            returncode = result.returncode
            if returncode == 0:
                return True
            else:
                return False
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
                    command = 'mkdir'
                    if args == []:
                        raise ValueError(f"{command} 命令参数列表不能为空")
                    command += ''.join(f' {arg}' for arg in args if arg is not None)
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
