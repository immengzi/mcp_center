import subprocess
from typing import Any, Dict, Optional

import paramiko
from mcp.server import FastMCP

from config.private.numa_bind_proc.config_loader import NumaBindProcConfig
from config.public.base_config_loader import LanguageEnum

# 初始化配置
config = NumaBindProcConfig()

mcp = FastMCP(
    "NUMA Bind MCP Server",
    host="0.0.0.0",
    port=config.get_config().private_config.port
)


@mcp.tool(
    name="numa_bind_proc_tool"
    if config.get_config().public_config.language == LanguageEnum.ZH
    else "numa_bind_proc_tool",
    description="""
    使用 numactl 命令在指定的 NUMA 节点和内存节点上运行程序。
    参数：
        numa_node: 指定的 NUMA 节点编号（整数）
        memory_node: 指定的内存节点编号（整数）
        program_path: 要运行的程序路径（必须）
        host: 可选，远程主机名称（使用public_config.toml中配置的name字段）；留空则本机执行。
    返回：
        dict {
            "stdout": str,       # 程序的标准输出
            "stderr": str,       # 程序的标准错误
            "exit_code": int,    # 程序的退出状态码
            "host": str          # 主机标识（本机为"localhost"）
        }
    """
    if config.get_config().public_config.language == LanguageEnum.ZH
    else """
    Run a program on a specified NUMA node and memory node using the numactl command.
    Args:
        numa_node: The NUMA node number (integer)
        memory_node: The memory node number (integer)
        program_path: Path to the program to execute (required)
        host: Optional remote host name (configured in public_config.toml); executes locally if omitted.
    Returns:
        dict {
            "stdout": str,       # Standard output of the program
            "stderr": str,       # Standard error of the program
            "exit_code": int,    # Exit code of the program
            "host": str          # Host identifier ("localhost" for local)
        }
    """
)
def numa_bind_proc_tool(
    numa_node: int = 0,
    memory_node: int = 0,
    program_path: str = "",
    host: Optional[str] = None
) -> Dict[str, Any]:
    """
    使用 numactl 命令在本地或远程主机上绑定 NUMA 和内存节点并运行程序
    
    Args:
        numa_node: NUMA 节点编号
        memory_node: 内存节点编号
        program_path: 程序路径
        host: 远程主机名称（public_config.toml 中的 name），None 表示本机
        
    Returns:
        包含执行结果的字典
    """
    cfg = config.get_config()
    is_zh = cfg.public_config.language == LanguageEnum.ZH
    
    if not program_path:
        msg = "必须提供程序路径" if is_zh else "Program path must be provided"
        raise ValueError(msg)
    
    # 本地执行
    if not host or host.strip().lower() in ("", "localhost"):
        return _execute_local_numactl(numa_node, memory_node, program_path, is_zh)
    
    # 远程执行
    return _execute_remote_numactl_workflow(
        host.strip(), numa_node, memory_node, program_path, cfg, is_zh
    )


def _execute_local_numactl(
    numa_node: int, memory_node: int, program_path: str, is_zh: bool
) -> Dict[str, Any]:
    """执行本地 numactl 命令"""
    command = f"numactl -N {numa_node} -m {memory_node} {program_path}"
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            check=False
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
            "host": "localhost"
        }
    except Exception as e:
        msg = f"本地 numactl 执行失败: {str(e)}" if is_zh else f"Local numactl execution failed: {str(e)}"
        raise RuntimeError(msg) from e


def _execute_remote_numactl_workflow(
    host_name: str, numa_node: int, memory_node: int, 
    program_path: str, cfg, is_zh: bool
) -> Dict[str, Any]:
    """远程执行工作流"""
    target_host = _find_remote_host(host_name, cfg.public_config.remote_hosts, is_zh)
    
    try:
        result = _execute_remote_numactl(
            target_host, numa_node, memory_node, program_path, is_zh
        )
        result["host"] = target_host.name
        return result
    except Exception as e:
        msg = (
            f"远程执行失败 [{target_host.name}]: {str(e)}" if is_zh
            else f"Remote execution failed [{target_host.name}]: {str(e)}"
        )
        raise RuntimeError(msg) from e


def _find_remote_host(host_name: str, remote_hosts: list, is_zh: bool):
    """查找远程主机配置"""
    for host in remote_hosts:
        if host.name == host_name or host.host == host_name:
            return host
    
    available = ", ".join([h.name for h in remote_hosts])
    msg = (
        f"未找到远程主机: {host_name}，可用: {available}" if is_zh
        else f"Host not found: {host_name}, available: {available}"
    )
    raise ValueError(msg)


def _execute_remote_numactl(
    host_config, numa_node: int, memory_node: int, 
    program_path: str, is_zh: bool
) -> Dict[str, Any]:
    """在远程主机执行 numactl"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        client.connect(
            hostname=host_config.host,
            port=host_config.port,
            username=host_config.username,
            password=host_config.password,
            timeout=10
        )
        
        command = f"numactl -N {numa_node} -m {memory_node} {program_path}"
        stdin, stdout, stderr = client.exec_command(command)
        stdin.close()
        
        stdout_text = stdout.read().decode('utf-8')
        stderr_text = stderr.read().decode('utf-8')
        exit_code = stdout.channel.recv_exit_status()
        
        return {
            "stdout": stdout_text,
            "stderr": stderr_text,
            "exit_code": exit_code
        }
    except paramiko.AuthenticationException as e:
        msg = "SSH认证失败" if is_zh else "SSH auth failed"
        raise ConnectionError(msg) from e
    finally:
        client.close()


if __name__ == "__main__":
    mcp.run(transport='sse')