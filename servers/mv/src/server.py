from typing import Union
import paramiko
import subprocess
from mcp.server import FastMCP
from config.public.base_config_loader import LanguageEnum
from config.private.mv.config_loader import MvConfig
mcp = FastMCP("Mv MCP Server", host="0.0.0.0", port=MvConfig().get_config().private_config.port)


@mcp.tool(
    name="mv_collect_tool"
    if MvConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "mv_collect_tool",
    description='''
    使用mv命令进行移动或重命名文件/目录
    1. 输入值如下：
        - host: 远程主机名称或IP地址，若不提供则对本机进行操作
        - source: 源文件或目录
        - target: 目标文件或目录
    2. 返回值为布尔值，表示mv操作是否成功
    '''
    if MvConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    '''
    Use the mv command to move or rename files/directories
    1. Input values are as follows:
        - host: The name or IP address of the remote host; if not provided, the operation is performed on the local machine
        - source: The source file or directory
        - target: The target file or directory
    2. The return value is a boolean indicating whether the mv operation was successful
    '''

)
def mv_collect_tool(host: Union[str, None] = None, source: str = None, target: str = None) -> bool:
    """使用mv命令进行移动或重命名文件/目录"""
    if host is None:
        try:
            command = ['mv']
            if not source or not target:
                raise ValueError(f"{command} 命令下源文件/目录和目标文件/目录不能为空")
            command.append(source)
            command.append(target)
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
        for host_config in MvConfig().get_config().public_config.remote_hosts:
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
                    command = 'mv'
                    if not source or not target:
                        raise ValueError(f"{command} 命令下源文件/目录和目标文件/目录不能为空")
                    command += f' {source}'
                    command += f' {target}'
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
                    raise ValueError(f"远程执行 {command} 失败: {str(e)}")
                finally:
                    # 确保SSH连接关闭
                    if ssh is not None:
                        try:
                            ssh.close()
                        except Exception:
                            pass
        if MvConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise ValueError(f"未找到远程主机: {host}")
        else:
            raise ValueError(f"Remote host not found: {host}")


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='sse')
