from typing import Any, Union, List, Dict
import re
import paramiko
import subprocess
from mcp.server import FastMCP
from config.public.base_config_loader import LanguageEnum
from config.private.strace_syscall.config_loader import StraceSyscallConfig

mcp = FastMCP("Strace Syscall MCP Server", host="0.0.0.0", port=StraceSyscallConfig().get_config().private_config.port)

@mcp.tool(
    name="strace_syscall"
    if StraceSyscallConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "strace_syscall",
    description='''
    采集指定进程的系统调用统计信息
    1. 输入参数：
        - host: 远程主机地址（可选）
        - pid: 目标进程ID
        - timeout: 采集超时时间（默认10秒）
    2. 返回字段：
        - syscall: 系统调用名称
        - total_time: 总耗时（秒）
        - call_count: 调用次数
        - avg_time: 平均耗时（微秒）
        - error_count: 错误次数
    '''
    if StraceSyscallConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    '''
    Collect system call statistics for a specific process
    1. Input parameters:
        - host: Remote host address (optional)
        - pid: Target process ID
        - timeout: Collection timeout (default 10s)
    2. Return fields:
        - syscall: System call name
        - total_time: Total time (seconds)
        - call_count: Call count
        - avg_time: Average time (microseconds)
        - error_count: Error count
    '''
)
def strace_syscall(host: Union[str, None] = None, pid: int = 0, timeout: int = 10) -> List[Dict[str, Any]]:
    """采集系统调用统计信息"""
    if not pid:
        raise ValueError("PID is required")

    def _parse_strace_output(output: str) -> List[Dict]:
        lines = output.strip().split('\n')
        # 过滤表头、分隔线和进程信息行
        data_lines = [
            line for line in lines 
            if line.strip() and 
            not any(line.startswith(prefix) for prefix in 
                   ('% time', '------', 'strace: Process'))
        ]
        
        results = []
        for line in data_lines:
            # 使用更灵活的正则表达式匹配
            match = re.match(
                r'^\s*([\d.]+)\s+([\d.]+)\s+(\d+)\s+(\d+)\s+(\d*)\s*(\w+)\s*$', 
                line
            )
            if match:
                percent_time, seconds, usecs_call, calls, errors, syscall = match.groups()
                # 跳过"total"行
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
        # 远程执行逻辑
        for host_config in StraceSyscallConfig().get_config().public_config.remote_hosts:
            if host == host_config.name or host == host_config.host:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(
                    hostname=host_config.host,
                    port=host_config.port,
                    username=host_config.username,
                    password=host_config.password
                )
                stdin, stdout, stderr = ssh.exec_command(f"timeout {timeout} strace -p {pid} -c")
                stdout_output = stdout.read().decode()
                stderr_output = stderr.read().decode()
                combined_output = stdout_output + stderr_output
                # print("Remote Combined Output:", combined_output)  # 调试输出

                # 解析输出并检查是否有有效数据
                parsed_results = _parse_strace_output(combined_output)
                if parsed_results:
                    return parsed_results
                else:
                    raise RuntimeError("Strace failed on remote host or no data collected")
    else:
        # 本地执行逻辑
        try:
            result = subprocess.run(
                ["timeout", str(timeout), "strace", "-p", str(pid), "-c"],
                capture_output=True,
                text=True,
                check=False  # 不抛出异常，确保捕获所有输出
            )
            # 合并 stdout 和 stderr
            combined_output = result.stdout + result.stderr
            # print("Combined Output:", combined_output)  # 调试输出
            
            # 解析输出并检查是否有有效数据
            parsed_results = _parse_strace_output(combined_output)
            if parsed_results:
                return parsed_results
            else:
                raise RuntimeError("Strace failed locally or no data collected")
        except Exception as e:
            print("Exception:", str(e))
            raise RuntimeError(f"Strace failed locally: {e}")

    if StraceSyscallConfig().get_config().public_config.language == LanguageEnum.ZH:
        raise ValueError(f"未找到远程主机: {host}")
    else:
        raise ValueError(f"Remote host not found: {host}")

if __name__ == "__main__":
    mcp.run(transport='sse')