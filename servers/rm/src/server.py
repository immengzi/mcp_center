from typing import Union
import os
import paramiko
import subprocess
from mcp.server import FastMCP
from config.public.base_config_loader import LanguageEnum
from config.private.rm.config_loader import RmConfig
mcp = FastMCP("Rm MCP Server", host="0.0.0.0", port=RmConfig().get_config().private_config.port)


@mcp.tool(
    name="rm_collect_tool"
    if RmConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "rm_collect_tool",
    description='''
    使用rm命令对文件或文件夹进行删除
    1. 输入值如下：
        - host: 远程主机名称或IP地址，若不提供则对本机进行操作
        - path: 要进行删除的文件或文件夹路径
    2. 返回值为布尔值，表示rm操作是否成功
    '''
    if RmConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    '''
    Use the rm command to delete files or folders
    1. Input values are as follows:
        - host: The name or IP address of the remote host; if not provided, the operation is performed on the local machine
        - path: The path of the file or folder to be deleted
    2. The return value is a boolean indicating whether the rm operation was successful
    '''

)
def rm_collect_tool(host: Union[str, None] = None, path: str = None) -> bool:
    """使用rm命令对文件或文件夹进行删除"""
    ALLOWED_PREFIXES = ('/tmp', '/home/user/trash')  # 仅允许删除这些前缀的路径，白名单
    if host is None:
        try:
            command = ['rm']
            command.append('-rf')
            if not path:
                raise ValueError(f"{command} 命令，删除的文件或文件夹路径不能为空")
            abs_path = os.path.abspath(path)
            print(abs_path)
            if not any(abs_path.startswith(prefix) for prefix in ALLOWED_PREFIXES):
                raise ValueError(f"路径 {abs_path} 不在允许删除的范围内")
            command.append(path)
            print(command)
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
        for host_config in RmConfig().get_config().public_config.remote_hosts:
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
                    command = 'rm -rf'
                    if not path:
                        raise ValueError(f"{command} 命令，删除的文件或文件夹路径不能为空")
                    abs_path = os.path.abspath(path)
                    print(abs_path)
                    if not any(abs_path.startswith(prefix) for prefix in ALLOWED_PREFIXES):
                        raise ValueError(f"路径 {abs_path} 不在允许删除的范围内")
                    command += f' {path}'
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
        if RmConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise ValueError(f"未找到远程主机: {host}")
        else:
            raise ValueError(f"Remote host not found: {host}")


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='sse')
