from typing import Any, Union, List, Dict
import re
import paramiko
import subprocess
from mcp.server import FastMCP
from config.public.base_config_loader import LanguageEnum
from config.private.strace_syscall.config_loader import StraceSyscallConfig

cfg = StraceSyscallConfig().get_config()
mcp = FastMCP(
    "Strace Syscall MCP Server",
    host="0.0.0.0",
    port=cfg.private_config.port
)

@mcp.tool(
    name="strace_syscall"
    if cfg.public_config.language == LanguageEnum.ZH
    else "strace_syscall",
    description='''
    采集指定进程的系统调用统计信息
    参数:
        - host: 可选，远程主机地址
        - pid: 目标进程ID
        - timeout: 采集超时时间，默认10秒
    返回:
        List[Dict] 每个字典包含:
            - syscall: 系统调用名称
            - total_time: 总耗时（秒）
            - call_count: 调用次数
            - avg_time: 平均耗时（微秒）
            - error_count: 错误次数
    '''
    if cfg.public_config.language == LanguageEnum.ZH
    else '''
    Collect system call statistics for a process
    Args:
        - host: Optional remote host
        - pid: Target process ID
        - timeout: Collection timeout in seconds (default 10)
    Returns:
        List[Dict] with keys:
            - syscall: system call name
            - total_time: total seconds
            - call_count: number of calls
            - avg_time: average microseconds
            - error_count: error count
    '''
)
def strace_syscall(host: Union[str, None] = None, pid: int = 0, timeout: int = 10) -> List[Dict[str, Any]]:
    if not pid:
        raise ValueError("PID is required")

    def _parse_strace_output(output: str) -> List[Dict[str, Any]]:
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
                    'syscall': syscall,
                    'total_time': float(seconds),
                    'call_count': int(calls),
                    'avg_time': int(usecs_call),
                    'error_count': int(errors) if errors else 0
                })
        return results

    if host:
        # 查找远程主机配置
        target_host = None
        for h in cfg.public_config.remote_hosts:
            if host.strip() in (h.name, h.host):
                target_host = h
                break
        if not target_host:
            msg = f"未找到远程主机: {host}" if cfg.public_config.language == LanguageEnum.ZH else f"Remote host not found: {host}"
            raise ValueError(msg)

        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=target_host.host,
                port=getattr(target_host, "port", 22),
                username=getattr(target_host, "username", None),
                password=getattr(target_host, "password", None),
                key_filename=getattr(target_host, "ssh_key_path", None),
                timeout=10
            )
            cmd = f"timeout {timeout} strace -p {pid} -c"
            stdin, stdout, stderr = ssh.exec_command(cmd)
            stdout_output = stdout.read().decode()
            stderr_output = stderr.read().decode()
            ssh.close()

            combined_output = stdout_output + stderr_output
            parsed_results = _parse_strace_output(combined_output)
            if parsed_results:
                return parsed_results
            else:
                raise RuntimeError("Strace failed on remote host or no data collected")
        except paramiko.AuthenticationException:
            msg = "SSH认证失败，请检查用户名或密钥" if cfg.public_config.language == LanguageEnum.ZH else "SSH authentication failed, check username/key"
            raise RuntimeError(msg)
        except paramiko.SSHException as e:
            msg = f"SSH连接错误: {e}" if cfg.public_config.language == LanguageEnum.ZH else f"SSH connection error: {e}"
            raise RuntimeError(msg)
    else:
        # 本地执行
        try:
            result = subprocess.run(
                ["timeout", str(timeout), "strace", "-p", str(pid), "-c"],
                capture_output=True,
                text=True,
                check=False
            )
            combined_output = result.stdout + result.stderr
            parsed_results = _parse_strace_output(combined_output)
            if parsed_results:
                return parsed_results
            else:
                raise RuntimeError("Strace failed locally or no data collected")
        except Exception as e:
            msg = f"Strace本地执行失败: {e}" if cfg.public_config.language == LanguageEnum.ZH else f"Strace local execution failed: {e}"
            raise RuntimeError(msg)


if __name__ == "__main__":
    mcp.run(transport="sse")
