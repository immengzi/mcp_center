from typing import Union
import paramiko
import subprocess
from mcp.server import FastMCP
from config.public.base_config_loader import LanguageEnum
from config.private.swapoff.config_loader import SwapoffConfig
mcp = FastMCP("Swapoff MCP Server", host="0.0.0.0", port=SwapoffConfig().get_config().private_config.port)


@mcp.tool(
    name="swapoff_disabling_swap_tool"
    if SwapoffConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "swapoff_disabling_swap_tool",
    description='''
    使用swapoff命令停用指定swap空间
    1. 输入值如下：
        - host: 远程主机名称或IP地址，若不提供则表示对本机的swap空间进行停用
        - name: 停用的swap空间路径，或者-a停用所有swap空间
    2. 返回值为布尔值，表示停用指定swap空间是否成功
    '''
    if SwapoffConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    '''
    Use the `swapoff` command to disable the specified swap space.
    1. Input values are as follows:
        - `host`: The name or IP address of the remote host. If not provided, it indicates that the swap space on the local machine will be disabled.
        - `name`: The path of the swap space to be disabled, or `-a` to disable all swap spaces.
    2. The return value is a boolean indicating whether the specified swap space was successfully disabled.
    '''
)
def swapoff_disabling_swap_tool(host: Union[str, None] = None, name: str = None) -> bool:
    """使用swapoff停用指定swap空间"""
    if host is None:
        if not name:
            if SwapoffConfig().get_config().public_config.language == LanguageEnum.ZH:
                raise ValueError("停用swap空间的路径不能为空")
            else:
                raise ValueError("The path for disabling swap space cannot be empty.")
        try:
            command = ['swapoff']
            command.append(name)
            result = subprocess.run(command, capture_output=True, text=True)
            returncode = result.returncode
            if returncode == 0:
                return True
            else:
                return False
        except subprocess.CalledProcessError as e:
            if SwapoffConfig().get_config().public_config.language == LanguageEnum.ZH:
                raise RuntimeError(f"执行 {command} 命令失败: {e.stderr}") from e
            else:
                raise RuntimeError(f"Failed to execute the free command: {e.stderr}") from e
        except Exception as e:
            if SwapoffConfig().get_config().public_config.language == LanguageEnum.ZH:
                raise RuntimeError(f"执行 {command} 命令时发生未知错误: {str(e)}") from e
            else:
                raise RuntimeError(f"An unknown error occurred while obtaining memory information: {str(e)}") from e
    else:
        for host_config in SwapoffConfig().get_config().public_config.remote_hosts:
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
                    if not name:
                        if SwapoffConfig().get_config().public_config.language == LanguageEnum.ZH:
                            raise ValueError("停用swap空间的路径不能为空")
                        else:
                            raise ValueError("The path for disabling swap space cannot be empty.")
                    command = 'swapoff'
                    command += f' {name}'
                    stdin, stdout, stderr = ssh.exec_command(command, timeout=20)
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
        if SwapoffConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise ValueError(f"未找到远程主机: {host}")
        else:
            raise ValueError(f"Remote host not found: {host}")


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='sse')
