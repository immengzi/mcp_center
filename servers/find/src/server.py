from typing import Union, List, Dict
import paramiko
import subprocess
from typing import Any
from mcp.server import FastMCP
from config.public.base_config_loader import LanguageEnum
from config.private.find.config_loader import FindConfig
mcp = FastMCP("Find MCP Server", host="0.0.0.0", port=FindConfig().get_config().private_config.port)


@mcp.tool(
    name="find_with_name_tool"
    if FindConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "find_with_name_tool",
    description='''
    使用find命令基于名称在指定目录下查找文件
    1. 输入值如下：
        - host: 远程主机名称或IP地址，若不提供则对本机文件进行查找
        - path: 指定查找的目录
        - name: 要找的文件名
    2. 返回值为包含相应信息的字典列表，每个字典包含以下键
        - file: 符合查找要求的具体文件路径
    '''
    if FindConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    '''
    Use the find command to search for files by name in a specified directory.
    1. Input values are as follows:
        - host: The name or IP address of the remote host; if not provided, the local file will be searched.
        - path: The directory to be searched.
        - name: The filename to be found.
    2. The return value is a list of dictionaries containing the relevant information, with each dictionary including the following keys:
        - file: The specific file path that meets the search criteria.
    '''

)
def find_with_name_tool(host: Union[str, None] = None, path: str = None, name: str = None) -> List[Dict[str, Any]]:
    """使用find命令基于名称在指定目录下查找文件"""
    if host is None:
        try:
            command = ['find']
            if not path or not name:
                if FindConfig().get_config().public_config.language == LanguageEnum.ZH:
                    raise ValueError(f"{command} 命令查找路径不能为空")
                else:
                    raise ValueError(f"{command} command search path cannot be empty")
            command.append(path)
            command.append('-name')
            command.append(name)
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
            if FindConfig().get_config().public_config.language == LanguageEnum.ZH:
                raise RuntimeError(f"执行 {command} 命令失败: {e.stderr}")
            else:
                raise RuntimeError(f"Command {command} execution failed: {e.stderr}")
        except Exception as e:
            if FindConfig().get_config().public_config.language == LanguageEnum.ZH:
                raise RuntimeError(f"执行 {command} 命令发生未知错误: {str(e)}") from e
            else:
                raise RuntimeError(f"An unknown error occurred while obtaining memory information: {str(e)}") from e
    else:
        for host_config in FindConfig().get_config().public_config.remote_hosts:
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
                    command = 'find'
                    if not path or not name:
                        if FindConfig().get_config().public_config.language == LanguageEnum.ZH:
                            raise ValueError(f"{command} 命令查找路径不能为空")
                        else:
                            raise ValueError(f"{command} command search path cannot be empty")
                    command += f' {path} -name {name}'
                    stdin, stdout, stderr = ssh.exec_command(command)
                    error = stderr.read().decode().strip()
                    output = stdout.read().decode().strip()

                    if error:
                        if VmstatConfig().get_config().public_config.language == LanguageEnum.ZH:
                            raise ValueError(f"命令 {command} 错误：{error}")
                        else:
                            raise ValueError(f"Command {command} error: {error}")
                    
                    lines = output.split('\n')
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
                    raise ValueError(f"远程执行 {command} 失败: {str(e)}")
                finally:
                    # 确保SSH连接关闭
                    if ssh is not None:
                        try:
                            ssh.close()
                        except Exception:
                            pass
        if FindConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise ValueError(f"未找到远程主机: {host}")
        else:
            raise ValueError(f"Remote host not found: {host}")

@mcp.tool(
    name="find_with_date_tool"
    if FindConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "find_with_date_tool",
    description='''
    使用find命令基于修改时间在指定目录下查找文件
    1. 输入值如下：
        - host: 远程主机名称或IP地址，若不提供则对本机文件进行查找
        - path: 指定查找的目录
        - time: 要找的时间范围
    2. 返回值为包含相应信息的字典列表，每个字典包含以下键
        - file: 符合查找要求的具体文件路径
    '''
    if FindConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    '''
    Use the find command to search for files in a specified directory based on modification time.
    1. Input values are as follows:
        - host: The name or IP address of the remote host; if not provided, the local file will be searched.
        - path: The directory to be searched.
        - time: The time range to be searched.
    2. The return value is a list of dictionaries containing the corresponding information, with each dictionary including the following keys:
        - file: The specific file path that meets the search criteria.
    '''

)
def find_with_date_tool(host: Union[str, None] = None, path: str = None, time: str = None) -> List[Dict[str, Any]]:
    """使用find命令基于名称在指定目录下查找文件"""
    if host is None:
        try:
            command = ['find']
            if not path or not time:
                raise ValueError(f"{command} 命令查找路径不能为空")
            command.append(path)
            command.append('-mtime')
            command.append(time)
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
        for host_config in FindConfig().get_config().public_config.remote_hosts:
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
                    command = 'find'
                    if not path or not time:
                        raise ValueError(f"{command} 命令查找路径不能为空")
                    command += f' {path} -mtime {time}'
                    stdin, stdout, stderr = ssh.exec_command(command)
                    error = stderr.read().decode().strip()
                    output = stdout.read().decode().strip()

                    if error:
                        raise ValueError(f"Command {command} error: {error}")
                    # 没有找到相应文件
                    # if not output:
                    #     raise ValueError("未能获取信息")
                    
                    lines = output.split('\n')
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
                    raise ValueError(f"远程执行 {command} 失败: {str(e)}")
                finally:
                    # 确保SSH连接关闭
                    if ssh is not None:
                        try:
                            ssh.close()
                        except Exception:
                            pass
        if FindConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise ValueError(f"未找到远程主机: {host}")
        else:
            raise ValueError(f"Remote host not found: {host}")

@mcp.tool(
    name="find_with_size_tool"
    if FindConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "find_with_size_tool",
    description='''
    使用find命令基于文件大小在指定目录下查找文件
    1. 输入值如下：
        - host: 远程主机名称或IP地址，若不提供则对本机文件进行查找
        - path: 指定查找的目录
        - size: 要找的文件尺寸范围
    2. 返回值为包含相应信息的字典列表，每个字典包含以下键
        - file: 符合查找要求的具体文件路径
    '''
    if FindConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    '''
    Use the find command to search for files in a specified directory based on file size.
    1. Input values are as follows:
        - host: The name or IP address of the remote host; if not provided, the local file will be searched.
        - path: The directory to be searched.
        - name: The filename to be found.
    2. The return value is a list of dictionaries containing the relevant information, with each dictionary including the following keys:
        - file: The specific file path that meets the search criteria.
    '''

)
def find_with_size_tool(host: Union[str, None] = None, path: str = None, size: str = None) -> List[Dict[str, Any]]:
    """使用find命令基于文件大小在指定目录下查找文件"""
    if host is None:
        try:
            command = ['find']
            if not path or not size:
                raise ValueError(f"{command} 命令查找路径不能为空")
            command.append(path)
            command.append('-size')
            command.append(size)
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
        for host_config in FindConfig().get_config().public_config.remote_hosts:
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
                    command = 'find'
                    if not path or not size:
                        raise ValueError(f"{command} 命令查找路径不能为空")
                    command += f' {path} -size {size}'
                    stdin, stdout, stderr = ssh.exec_command(command)
                    error = stderr.read().decode().strip()
                    output = stdout.read().decode().strip()

                    if error:
                        raise ValueError(f"Command {command} error: {error}")
                    # 没有找到相应文件
                    # if not output:
                    #     raise ValueError("未能获取信息")
                    
                    lines = output.split('\n')
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
                    raise ValueError(f"远程执行 {command} 失败: {str(e)}")
                finally:
                    # 确保SSH连接关闭
                    if ssh is not None:
                        try:
                            ssh.close()
                        except Exception:
                            pass
        if FindConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise ValueError(f"未找到远程主机: {host}")
        else:
            raise ValueError(f"Remote host not found: {host}")


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='sse')
