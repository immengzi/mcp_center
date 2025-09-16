from typing import Dict, Any, Union
import subprocess
import paramiko
from mcp.server import FastMCP
from config.public.base_config_loader import LanguageEnum
from config.private.numa_rebind.config_loader import NumaRebindConfig

mcp = FastMCP("NUMA Rebind MCP Server", host="0.0.0.0", port=NumaRebindConfig().get_config().private_config.port)

@mcp.tool(
    name="numa_rebind_tool"
    if NumaRebindConfig().get_config().public_config.language == LanguageEnum.ZH
    else "numa_rebind_tool",
    description='''
    修改已运行进程的 NUMA 内存绑定。使用 migratepages 工具将进程的内存从一个 NUMA 节点迁移到另一个节点。
    
    1. 输入参数：
        - pid: 进程 ID
        - from_node: 当前内存所在的 NUMA 节点编号
        - to_node: 目标 NUMA 节点编号
        - host: 远程主机 IP 或名称（可选）
    
    2. 返回值：
        - status: 操作状态（success / error）
        - message: 操作结果信息
        - output: 命令的原始输出（如有）
    '''
    if NumaRebindConfig().get_config().public_config.language == LanguageEnum.ZH
    else 
    '''
    Rebind the NUMA memory of a running process. Use the migratepages tool to migrate memory from one NUMA node to another.

    1. Input parameters:
        - pid: Process ID
        - from_node: Current NUMA node number where memory is located
        - to_node: Target NUMA node number
        - host: Remote host IP or name (optional)
    
    2. Return value:
        - status: Operation status (success / error)
        - message: Result information
        - output: Raw output of the command (if any)
    '''
)
def numa_rebind_tool(
    pid: int,
    from_node: int,
    to_node: int,
    host: Union[str, None] = None
) -> Dict[str, Any]:
    """
    使用 migratepages 工具将进程的内存从一个 NUMA 节点迁移到另一个节点。
    """
    def execute_local():
        command = ["sudo", "migratepages", str(pid), str(from_node), str(to_node)]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return {
            "status": "success",
            "message": f"Memory for PID {pid} has been migrated from node {from_node} to node {to_node}.",
            "output": result.stdout
        }

    def execute_remote(target_host):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        ssh_username = target_host.username
        ssh_password = getattr(target_host, "password", None)
        ssh_key_file = getattr(target_host, "ssh_key_path", None)
        ssh_port = getattr(target_host, "port", 22)

        try:
            if ssh_key_file:
                client.connect(target_host.host, port=ssh_port, username=ssh_username, key_filename=ssh_key_file, timeout=10)
            else:
                client.connect(target_host.host, port=ssh_port, username=ssh_username, password=ssh_password, timeout=10)

            command = f"sudo migratepages {pid} {from_node} {to_node}"
            stdin, stdout, stderr = client.exec_command(command)
            stdout_text = stdout.read().decode('utf-8')
            stderr_text = stderr.read().decode('utf-8')
            exit_code = stdout.channel.recv_exit_status()

            status = "success" if exit_code == 0 else "error"
            message = f"Memory for PID {pid} migrated" if exit_code == 0 else f"Migration failed with exit code {exit_code}"

            return {
                "status": status,
                "message": message,
                "output": stdout_text + stderr_text
            }
        finally:
            client.close()

    try:
        if host is None:
            return execute_local()
        else:
            config = NumaRebindConfig().get_config()
            target_host = next(
                (h for h in config.public_config.remote_hosts if h.name == host or h.host == host),
                None
            )
            if not target_host:
                raise RuntimeError(f"未找到主机 {host} 的配置")
            return execute_remote(target_host)

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() or "Command execution failed."
        if NumaRebindConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise RuntimeError(f"迁移失败: {error_msg}")
        else:
            raise RuntimeError(f"Migration failed: {error_msg}")
    except FileNotFoundError:
        if NumaRebindConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise RuntimeError("未找到 migratepages 工具，请安装 numactl 包。")
        else:
            raise RuntimeError("migratepages tool not found. Please install the numactl package.")
    except paramiko.AuthenticationException:
        if NumaRebindConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise RuntimeError("SSH 认证失败，请检查用户名或密钥")
        else:
            raise RuntimeError("SSH authentication failed, please check the username or key")
    except paramiko.SSHException as e:
        if NumaRebindConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise RuntimeError(f"SSH 连接错误: {e}")
        else:
            raise RuntimeError(f"SSH connection error: {e}")
    except Exception as e:
        if NumaRebindConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise RuntimeError(f"运行程序失败: {str(e)}")
        else:
            raise RuntimeError(f"Failed to run program: {str(e)}")


if __name__ == "__main__":
    mcp.run(transport='sse')