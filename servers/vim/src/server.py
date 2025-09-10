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
    name="vim_collect_tool"
    if TopConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "vim_collect_tool",
    description='''
    使用vim命令对文件进行修改，仅支持非交互式的文件编辑
    1. 输入值如下：
        - host: 远程主机名称或IP地址，若不提供则对本机进行操作
        - name: 要进行编辑的文件路径
        - op: 要执行的操作
    2. 返回值为布尔值，表示vim操作是否成功
    '''
    if TopConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    '''
    Use the vim command to modify files, supporting only non-interactive file editing.
    1. Input values are as follows:
        - host: The name or IP address of the remote host; if not provided, operations are performed on the local machine.
        - name: The file path to be edited
        - op: The operation to be performed
    2. The return value is a boolean indicating whether the vim operation was successful.
    '''

)
def vim_collect_tool(host: Union[str, None] = None, name: str = None, op: str = None) -> bool:
    """使用vim命令对文件进行修改"""
    if host is None:
        try:
            command = ["vim"]
            if not name or not op:
                raise ValueError(f"{command} 命令，修改的文件名和文件内容不能为空")
            command.append(name)
            command.append("-c")
            command.append(op)
            command.append("-c")
            command.append("wq")
            result = subprocess.run(command, check=True)
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
                    command = "vim"
                    if not name or not op:
                        raise ValueError(f"{command} 命令，修改的文件名和文件内容不能为空")
                    command += f" {name}"
                    command += " -c"
                    command += f" {op}"
                    command += " -c"
                    command += " wq"
                    stdin, stdout, stderr = ssh.exec_command(command)
                    print(command)
                    error = stderr.read().decode().strip()

                    if error:
                        print(f"执行失败，错误信息: {error}")  # 打印错误详情
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
