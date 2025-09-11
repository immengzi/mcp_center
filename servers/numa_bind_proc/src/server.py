from typing import Union, Dict, Any
import paramiko
import subprocess
from mcp.server import FastMCP
from config.public.base_config_loader import LanguageEnum
from config.private.numa_bind_proc.config_loader import NumaBindProcConfig

mcp = FastMCP("NUMA Bind Proc MCP Server", host="0.0.0.0", port=NumaBindProcConfig().get_config().private_config.port)

@mcp.tool(
    name="numa_bind_proc_tool"
    if NumaBindProcConfig().get_config().public_config.language == LanguageEnum.ZH
    else "numa_bind_proc_tool",
    description='''
    使用 numactl 命令在指定的 NUMA 节点和内存节点上运行程序。
    
    输入参数：
    - host: 远程主机 IP 或名称（可选）
    - numa_node: 指定的 NUMA 节点编号（整数）
    - memory_node: 指定的内存节点编号（整数）
    - program_path: 要运行的程序路径（必须）

    返回值：
    - stdout: 程序的标准输出
    - stderr: 程序的标准错误
    - exit_code: 程序的退出状态码
    '''
    if NumaBindProcConfig().get_config().public_config.language == LanguageEnum.ZH
    else 
    '''
    Run a program on a specified NUMA node and memory node using the numactl command.

    Input parameters:
    - host: Remote host IP or name (optional)
    - numa_node: The NUMA node number (integer)
    - memory_node: The memory node number (integer)
    - program_path: Path to the program to execute (required)

    Return values:
    - stdout: Standard output of the program
    - stderr: Standard error of the program
    - exit_code: Exit code of the program
    '''
)
def numa_bind_proc_tool(
    host: Union[str, None] = None,
    numa_node: int = 0,
    memory_node: int = 0,
    program_path: str = ""
) -> Dict[str, Any]:
    """
    使用 numactl 命令在本地或远程主机上绑定 NUMA 和内存节点并运行程序
    """
    if not program_path:
        if NumaBindProcConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise ValueError("必须提供程序路径")
        else:
            raise ValueError("Program path must be provided")

    def execute_local():
        """本地执行 numactl 命令"""
        command = f"numactl -N {numa_node} -m {memory_node} {program_path}"
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode
        }

    def execute_remote():
        """远程执行 numactl 命令"""
        config = NumaBindProcConfig().get_config()
        username = config.private_config.ssh_username
        key_file = config.private_config.ssh_key_path
        port = config.private_config.ssh_port or 22

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            client.connect(host, port=port, username=username, key_filename=key_file, timeout=10)
            command = f"numactl -N {numa_node} -m {memory_node} {program_path}"
            stdin, stdout, stderr = client.exec_command(command)
            stdout_text = stdout.read().decode('utf-8')
            stderr_text = stderr.read().decode('utf-8')
            exit_code = stdout.channel.recv_exit_status()
            return {
                "stdout": stdout_text,
                "stderr": stderr_text,
                "exit_code": exit_code
            }
        finally:
            client.close()

    try:
        if host is None:
            return execute_local()
        else:
            return execute_remote()

    except subprocess.CalledProcessError as e:
        if NumaBindProcConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise RuntimeError(f"本地 numactl 执行失败: {e.stderr}")
        else:
            raise RuntimeError(f"Local numactl execution failed: {e.stderr}")
    except paramiko.AuthenticationException:
        if NumaBindProcConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise RuntimeError("SSH 认证失败，请检查用户名或密钥")
        else:
            raise RuntimeError("SSH authentication failed, please check the username or key")
    except paramiko.SSHException as e:
        if NumaBindProcConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise RuntimeError(f"SSH 连接错误: {e}")
        else:
            raise RuntimeError(f"SSH connection error: {e}")
    except Exception as e:
        if NumaBindProcConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise RuntimeError(f"运行程序失败: {str(e)}")
        else:
            raise RuntimeError(f"Failed to run program: {str(e)}")


if __name__ == "__main__":
    # 启动 MCP 服务
    mcp.run(transport='sse')