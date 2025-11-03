from typing import Union
import paramiko
import subprocess
from mcp.server import FastMCP
from config.public.base_config_loader import LanguageEnum
from config.private.echo.config_loader import EchoConfig

mcp = FastMCP("Echo MCP Server", host="0.0.0.0", port=EchoConfig().get_config().private_config.port)

@mcp.tool(
    name="echo_write_to_file_tool"
    if EchoConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "echo_write_to_file_tool",
    description='''
    使用echo命令将文本写入文件
    1. 输入值如下：
        - host: 远程主机名称或IP地址，若不提供则表示在本机执行
        - text: 要写入的文本内容
        - file: 要写入的文件路径
        - options: echo选项（可选），如"-n"不输出换行符等
        - mode: 写入模式，"w"表示覆盖写入，"a"表示追加写入，默认为"w"
    2. 返回值为布尔值，表示写入操作是否成功
    '''
    if EchoConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    '''
    Use the echo command to write text to a file
    1. Input values are as follows:
        - host: The name or IP address of the remote host; if not provided, it indicates execution on the local machine
        - text: The text content to write
        - file: The file path to write to
        - options: echo options (optional), such as "-n" to suppress the trailing newline
        - mode: Write mode, "w" for overwrite, "a" for append, default is "w"
    2. The return value is a boolean indicating whether the write operation was successful
    '''

)
def echo_write_to_file_tool(host: Union[str, None] = None, text: str = None, file: str = None, options: Union[str, None] = None, mode: str = "w") -> bool:
    """使用echo命令将文本写入文件"""
    if host is None:
        try:
            # 构建echo命令
            command = ['echo']
            if options:
                command.extend(options.split())
            command.append(text)
            
            # 添加重定向
            if mode == "a":
                command.append(f">>{file}")
            else:
                command.append(f">{file}")
            
            # 将命令列表转换为字符串以便执行
            command_str = ' '.join(command)
            
            # 使用shell执行命令
            result = subprocess.run(command_str, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                return True
            else:
                # 错误处理
                error_msg = result.stderr.strip()
                if EchoConfig().get_config().public_config.language == LanguageEnum.ZH:
                    raise RuntimeError(f"执行echo命令时发生错误: {error_msg}")
                else:
                    raise RuntimeError(f"Error executing echo command: {error_msg}")
        except Exception as e:
            if EchoConfig().get_config().public_config.language == LanguageEnum.ZH:
                raise RuntimeError(f"执行echo命令时发生未知错误: {str(e)}") from e
            else:
                raise RuntimeError(f"An unknown error occurred while executing echo command: {str(e)}") from e
    else:
        for host_config in EchoConfig().get_config().public_config.remote_hosts:
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
                    
                    # 构建远程echo命令
                    echo_command = f'echo'
                    if options:
                        echo_command += f' {options}'
                    # 转义文本中的特殊字符
                    escaped_text = text.replace("'", "'\"'\"'")
                    echo_command += f" '{escaped_text}'"
                    
                    # 添加重定向
                    if mode == "a":
                        echo_command += f" >> {file}"
                    else:
                        echo_command += f" > {file}"
                    
                    stdin, stdout, stderr = ssh.exec_command(echo_command, timeout=30)
                    error = stderr.read().decode().strip()
                    
                    if error:
                        raise ValueError(f"执行命令 {echo_command} 错误：{error}")
                    
                    return True
                except paramiko.AuthenticationException:
                    raise ValueError("SSH认证失败，请检查用户名和密码")
                except paramiko.SSHException as e:
                    raise ValueError(f"SSH连接错误: {str(e)}")
                except Exception as e:
                    raise ValueError(f"远程执行 {echo_command} 失败: {str(e)}")
                finally:
                    # 确保SSH连接关闭
                    if ssh is not None:
                        try:
                            ssh.close()
                        except Exception:
                            pass
        if EchoConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise ValueError(f"未找到远程主机: {host}")
        else:
            raise ValueError(f"Remote host not found: {host}")


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='sse')