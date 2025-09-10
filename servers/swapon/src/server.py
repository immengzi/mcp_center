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
    name="swapon_collect_tool"
    if TopConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "swapon_collect_tool",
    description='''
    使用swapon命令查看当前swap设备状态
    1. 输入值如下：
        - host: 远程主机名称或IP地址，若不提供则表示获取本机的swap设备状态
    2. 返回值为包含进程信息的字典列表，每个字典包含以下键
        - name: swap空间对应的设备或文件路径
        - type: swap空间的类型
        - size: swap空间的总大小
        - used: 当前已使用的swap空间量
        - prio: swap空间的优先级
    '''
    if TopConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    '''
    Use the `swapon` command to check the current status of swap devices.
    1. The input values are as follows:
        - host: The name or IP address of the remote host. If not provided, it indicates that the swap device status of the local machine will be retrieved.
    2. The return value is a list of dictionaries containing process information, with each dictionary including the following keys:
        - name: The device or file path corresponding to the swap space.
        - type: The type of the swap space.
        - size: The total size of the swap space.
        - used: The amount of swap space currently in use.
        - prio: The priority of the swap space.
    '''

)
def swapon_collect_tool(host: Union[str, None] = None) -> List[Dict[str, Any]]:
    """使用swapon获取当前swap设备状态"""
    if host is None:
        try:
            command = ['swapon']
            result = subprocess.run(command, capture_output=True, text=True)
            lines = result.stdout.split('\n')
            swap_devices = []
            if len(lines) < 2:
                # 该机器没有swap设备
                return swap_devices
            for line in lines[1:-1]:
                parts = line.split()
                swap_devices.append({
                    "name": parts[0],
                    "type": parts[1],
                    "size": parts[2],
                    "used": parts[3],
                    "prio": parts[4]
                })
            return swap_devices
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"执行 {command} 命令失败: {e.stderr}") from e
        except Exception as e:
            raise RuntimeError(f"执行 {command} 命令时发生未知错误: {str(e)}") from e
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
                    command = 'swapon'
                    stdin, stdout, stderr = ssh.exec_command(command, timeout = 20)
                    error = stderr.read().decode().strip()
                    output = stdout.read().decode().strip()

                    if error:
                        raise ValueError(f"Command {command} error: {error}")

                    if not output:
                        raise ValueError("未能获取swap设备信息")

                    lines = output.split('\n')
                    swap_devices = []
                    if len(lines) < 2:
                        # print("该机器没有swap设备")
                        return swap_devices
                    for line in lines[1:]:
                        if not line.strip():
                            continue
                        parts = line.split()
                        print(parts)
                        if len(parts) < 5:
                            continue
                        swap_devices.append({
                            "name": parts[0],
                            "type": parts[1],
                            "size": parts[2],
                            "used": parts[3],
                            "prio": parts[4]
                        })
                    return swap_devices
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
