import re
import subprocess
from typing import Any, Dict, List, Optional

import paramiko
from mcp.server import FastMCP

from config.private.strace_syscall.config_loader import StraceSyscallConfig
from config.public.base_config_loader import LanguageEnum

# 初始化配置
config = StraceSyscallConfig()

mcp = FastMCP(
    "Strace Syscall MCP Server",
    host="0.0.0.0",
    port=config.get_config().private_config.port
)


@mcp.tool(
    name="strace_syscall"
    if config.get_config().public_config.language == LanguageEnum.ZH
    else "strace_syscall",
    description="""
    采集指定进程的系统调用统计信息。
    参数：
        pid: 目标进程ID
        timeout: 采集超时时间，默认10秒
        host: 可选，远程主机名称（使用public_config.toml中配置的name字段）；留空则本机执行。
    返回：
        dict {
            "syscalls": list,  # 系统调用列表
            "host": str        # 主机标识（本机为"localhost"）
        }
    """
    if config.get_config().public_config.language == LanguageEnum.ZH
    else """
    Collect system call statistics for a process.
    Args:
        pid: Target process ID
        timeout: Collection timeout in seconds (default 10)
        host: Optional remote host name (configured in public_config.toml); executes locally if omitted.
    Returns:
        dict {
            "syscalls": list,  # List of system calls
            "host": str        # Host identifier ("localhost" for local)
        }
    """
)
def strace_syscall(pid: int, timeout: int = 10, host: Optional[str] = None) -> Dict[str, Any]:
    """
    采集指定进程的系统调用统计信息
    
    Args:
        pid: 进程 ID
        timeout: 采集超时时间（秒）
        host: 远程主机名称（public_config.toml 中的 name），None 表示本机
        
    Returns:
        包含系统调用统计信息的字典
    """
    cfg = config.get_config()
    is_zh = cfg.public_config.language == LanguageEnum.ZH
    
    if not pid:
        msg = "PID 不能为空" if is_zh else "PID is required"
        raise ValueError(msg)
    
    # 本地执行
    if not host or host.strip().lower() in ("", "localhost"):
        return _execute_local_strace(pid, timeout, is_zh)
    
    # 远程执行
    return _execute_remote_strace_workflow(host.strip(), pid, timeout, cfg, is_zh)


def _execute_local_strace(pid: int, timeout: int, is_zh: bool) -> Dict[str, Any]:
    """执行本地 strace"""
    try:
        strace_output = _run_local_strace(pid, timeout, is_zh)
        syscalls = _parse_strace_output(strace_output)
        return {
            "syscalls": syscalls,
            "host": "localhost"
        }
    except Exception as e:
        msg = f"本地 strace 执行失败: {str(e)}" if is_zh else f"Local strace failed: {str(e)}"
        raise RuntimeError(msg) from e


def _execute_remote_strace_workflow(
    host_name: str, pid: int, timeout: int, cfg, is_zh: bool
) -> Dict[str, Any]:
    """远程执行工作流"""
    target_host = _find_remote_host(host_name, cfg.public_config.remote_hosts, is_zh)
    
    try:
        strace_output = _execute_remote_strace(target_host, pid, timeout, is_zh)
        syscalls = _parse_strace_output(strace_output)
        return {
            "syscalls": syscalls,
            "host": target_host.name
        }
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


def _run_local_strace(pid: int, timeout: int, is_zh: bool) -> str:
    """运行本地 strace"""
    cmd = ["strace", "-c", "-p", str(pid)]
    
    try:
        # strace 输出到 stderr
        result = subprocess.run(
            cmd,
            stderr=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            text=True,
            timeout=timeout,
            check=False
        )
        return result.stderr
    except subprocess.TimeoutExpired:
        # Timeout is expected, strace runs until timeout
        pass
    except subprocess.CalledProcessError as e:
        msg = f"strace 执行失败: {e.stderr}" if is_zh else f"strace execution failed: {e.stderr}"
        raise RuntimeError(msg) from e
    
    # Try again with timeout parameter
    try:
        result = subprocess.run(
            cmd,
            stderr=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            text=True,
            timeout=timeout + 1,
            check=False
        )
        return result.stderr
    except Exception as e:
        msg = f"strace 执行失败: {str(e)}" if is_zh else f"strace execution failed: {str(e)}"
        raise RuntimeError(msg) from e


def _execute_remote_strace(host_config, pid: int, timeout: int, is_zh: bool) -> str:
    """在远程主机执行 strace"""
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
        
        # Run strace with timeout
        cmd = f"timeout {timeout} strace -c -p {pid} 2>&1 || true"
        stdin, stdout, stderr = client.exec_command(cmd)
        stdin.close()
        
        output = stdout.read().decode('utf-8')
        return output
    except paramiko.AuthenticationException as e:
        msg = "SSH认证失败" if is_zh else "SSH auth failed"
        raise ConnectionError(msg) from e
    finally:
        client.close()


def _parse_strace_output(output: str) -> List[Dict[str, Any]]:
    """解析 strace 输出"""
    lines = output.strip().split("\n")
    data_lines = [
        line for line in lines
        if line.strip() and not any(line.startswith(prefix) for prefix in ('% time', '------', 'strace: Process'))
    ]
    
    results = []
    for line in data_lines:
        match = re.match(
            r'^\s*([\d.]+)\s+([\d.]+)\s+(\d+)\s+(\d+)\s+(\d*)\s*(\w+)\s*$',
            line
        )
        if match:
            percent_time, seconds, usecs_call, calls, errors, syscall = match.groups()
            if syscall == 'total':
                continue
            results.append({
                "syscall": syscall,
                "total_time": float(seconds),
                "call_count": int(calls),
                "avg_time": int(usecs_call) if usecs_call else 0,
                "error_count": int(errors) if errors else 0,
                "percent_time": float(percent_time)
            })
    
    return results


if __name__ == "__main__":
    mcp.run(transport='sse')
