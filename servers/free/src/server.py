from typing import Union, Dict, Any
import paramiko
import subprocess
from mcp.server import FastMCP
from config.public.base_config_loader import LanguageEnum
from config.private.free.config_loader import FreeConfig
mcp = FastMCP("Free MCP Server", host="0.0.0.0", port=FreeConfig().get_config().private_config.port)


@mcp.tool(
    name="free_collect_tool"
    if FreeConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "free_collect_tool",
    description='''
    使用free命令快速摸底远端机器或者本机内存整体状态
    1. 输入值如下：
        - host: 远程主机名称或IP地址，若不提供则表示获取本机的内存使用情况
    2. 返回值为包含内存使用情况的字典，包含以下键
        - total: 系统内存总量（单位MB）
        - used: 系统已使用内存量（单位MB）
        - free: 空闲的物理内存（单位MB）
        - available: 系统可分配给新应用程序的内存量（单位MB）
    '''
    if FreeConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    '''
    Use the `free` command to quickly assess the overall memory status of a remote machine or the local machine.
    1. Input values are as follows:
        - host: The name or IP address of the remote host. If not provided, it indicates that the memory usage of the local machine will be retrieved.
    2. The return value is a dictionary containing memory usage information, with the following keys:
        - total: Total system memory (in MB)
        - used: Memory used by the system (in MB)
        - free: Free physical memory (in MB)
        - available: Memory available for allocation to new applications (in MB)
    '''

)
def free_collect_tool(host: Union[str, None] = None) -> Dict[str, Any]:
    """使用free命令获取机器内存整体状态"""
    if host is None:
        try:
            command = ['free', '-m']
            result = subprocess.run(command, capture_output=True, text=True)
            lines = result.stdout.split('\n')
            if len(lines) < 2:
                if FreeConfig().get_config().public_config.language == LanguageEnum.ZH:
                    raise ValueError(f"{command} 命令输出格式不正确，缺少内存信息行")
                else:
                    raise ValueError(f"The output format of the {command} is incorrect, missing the memory information line.")
            parts = lines[1].split()
            if len(parts) < 7:
                if FreeConfig().get_config().public_config.language == LanguageEnum.ZH:
                    raise ValueError(f"{command} 命令输出字段不足，无法提取所需内存信息")
                else:
                    raise ValueError(f"The output fields of the {command} are insufficient, unable to extract the required memory information.")
            memory_info = {
                'total': int(parts[1]),
                'used': int(parts[2]),
                'free': int(parts[3]),
                'available': int(parts[6])
            }
            return memory_info
        except Exception as e:
            if FreeConfig().get_config().public_config.language == LanguageEnum.ZH:
                raise RuntimeError(f"获取 {command} 输出信息时发生未知错误: {str(e)}") from e
            else:
                raise RuntimeError(f"An unknown error occurred while retrieving the output information for {command} : {str(e)}") from e
    else:
        for host_config in FreeConfig().get_config().public_config.remote_hosts:
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
                    command = "free -m"
                    stdin, stdout, stderr = ssh.exec_command(command, timeout=10)
                    error = stderr.read().decode().strip()
                    output = stdout.read().decode().strip()
                    if error:
                        raise ValueError(f"Command {command} error: {error}")

                    if not output:
                        raise ValueError("未能获取内存信息")

                    lines = output.strip().split('\n')
                    if len(lines) < 2:
                        if FreeConfig().get_config().public_config.language == LanguageEnum.ZH:
                            raise ValueError(f"{command} 命令输出格式不正确，缺少内存信息行")
                        else:
                            raise ValueError(f"The output format of the {command} is incorrect, missing the memory information line.")
                    parts = lines[1].split()
                    if len(parts) < 7:
                        if FreeConfig().get_config().public_config.language == LanguageEnum.ZH:
                            raise ValueError(f"{command} 命令输出字段不足，无法提取所需内存信息")
                        else:
                            raise ValueError(f"The output fields of the {command} are insufficient, unable to extract the required memory information.")
                    memory_info = {
                        'total': int(parts[1]),
                        'used': int(parts[2]),
                        'free': int(parts[3]),
                        'available': int(parts[6])
                    }
                    return memory_info
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
        if FreeConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise ValueError(f"未找到远程主机: {host}")
        else:
            raise ValueError(f"Remote host not found: {host}")


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='sse')
