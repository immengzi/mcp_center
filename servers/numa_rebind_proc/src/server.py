import subprocess
from typing import Any, Dict, Optional

import paramiko
from mcp.server import FastMCP

from config.private.numa_rebind_proc.config_loader import NumaRebindProcConfig
from config.public.base_config_loader import LanguageEnum

# 初始化配置
config = NumaRebindProcConfig()

mcp = FastMCP(
    "NUMA Rebind MCP Server",
    host="0.0.0.0",
    port=config.get_config().private_config.port
)


@mcp.tool(
    name="numa_rebind_proc_tool"
    if config.get_config().public_config.language == LanguageEnum.ZH
    else "numa_rebind_proc_tool",
    description="""
    修改已运行进程的 NUMA 内存绑定。使用 migratepages 工具将进程的内存从一个 NUMA 节点迁移到另一个节点。
    参数：
        pid: 进程 ID
        from_node: 当前内存所在的 NUMA 节点编号
        to_node: 目标 NUMA 节点编号
        host: 可选，远程主机名称（使用public_config.toml中配置的name字段）；留空则本机执行。
    返回：
        dict {
            "status": str,       # 操作状态（success / error）
            "message": str,      # 操作结果信息
            "output": str,       # 命令的原始输出（如有）
            "host": str          # 主机标识（本机为"localhost"）
        }
    """
    if config.get_config().public_config.language == LanguageEnum.ZH
    else """
    Rebind the NUMA memory of a running process. Use the migratepages tool to migrate memory from one NUMA node to another.
    Args:
        pid: Process ID
        from_node: Current NUMA node number where memory is located
        to_node: Target NUMA node number
        host: Optional remote host name (configured in public_config.toml); executes locally if omitted.
    Returns:
        dict {
            "status": str,       # Operation status (success / error)
            "message": str,      # Result information
            "output": str,       # Raw output of the command (if any)
            "host": str          # Host identifier ("localhost" for local)
        }
    """
)
def numa_rebind_proc_tool(
    pid: int,
    from_node: int,
    to_node: int,
    host: Optional[str] = None
) -> Dict[str, Any]:
    """
    使用 migratepages 工具将进程的内存从一个 NUMA 节点迁移到另一个节点
    
    Args:
        pid: 进程 ID
        from_node: 源 NUMA 节点编号
        to_node: 目标 NUMA 节点编号
        host: 远程主机名称（public_config.toml 中的 name），None 表示本机
        
    Returns:
        包含执行结果的字典
    """
    cfg = config.get_config()
    is_zh = cfg.public_config.language == LanguageEnum.ZH
    
    # 本地执行
    if not host or host.strip().lower() in ("", "localhost"):
        return _execute_local_migratepages(pid, from_node, to_node, is_zh)
    
    # 远程执行
    return _execute_remote_migratepages_workflow(
        host.strip(), pid, from_node, to_node, cfg, is_zh
    )


def _execute_local_migratepages(
    pid: int, from_node: int, to_node: int, is_zh: bool
) -> Dict[str, Any]:
    """执行本地 migratepages 命令"""
    command = ["sudo", "migratepages", str(pid), str(from_node), str(to_node)]
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
        return {
            "status": "success",
            "message": f"Memory for PID {pid} has been migrated from node {from_node} to node {to_node}.",
            "output": result.stdout,
            "host": "localhost"
        }
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() or "Command execution failed."
        msg = f"迁移失败: {error_msg}" if is_zh else f"Migration failed: {error_msg}"
        raise RuntimeError(msg) from e
    except FileNotFoundError as e:
        msg = (
            "未找到 migratepages 工具，请安装 numactl 包。" if is_zh
            else "migratepages tool not found. Please install the numactl package."
        )
        raise RuntimeError(msg) from e


def _execute_remote_migratepages_workflow(
    host_name: str, pid: int, from_node: int, to_node: int, cfg, is_zh: bool
) -> Dict[str, Any]:
    """远程执行工作流"""
    target_host = _find_remote_host(host_name, cfg.public_config.remote_hosts, is_zh)
    
    try:
        result = _execute_remote_migratepages(
            target_host, pid, from_node, to_node, is_zh
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


def _execute_remote_migratepages(
    host_config, pid: int, from_node: int, to_node: int, is_zh: bool
) -> Dict[str, Any]:
    """在远程主机执行 migratepages"""
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
        
        command = f"sudo migratepages {pid} {from_node} {to_node}"
        stdin, stdout, stderr = client.exec_command(command)
        stdin.close()
        
        stdout_text = stdout.read().decode('utf-8')
        stderr_text = stderr.read().decode('utf-8')
        exit_code = stdout.channel.recv_exit_status()
        
        status = "success" if exit_code == 0 else "error"
        message = (
            f"Memory for PID {pid} migrated" if exit_code == 0
            else f"Migration failed with exit code {exit_code}"
        )
        
        return {
            "status": status,
            "message": message,
            "output": stdout_text + stderr_text
        }
    except paramiko.AuthenticationException as e:
        msg = "SSH认证失败" if is_zh else "SSH auth failed"
        raise ConnectionError(msg) from e
    finally:
        client.close()


if __name__ == "__main__":
    mcp.run(transport='sse')