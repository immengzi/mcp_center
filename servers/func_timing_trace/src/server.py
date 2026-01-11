import os
import re
import shlex
import subprocess
import tempfile
from typing import Any, Dict, List, Optional

import paramiko
from mcp.server import FastMCP

from config.private.func_timing_trace.config_loader import FuncTimingTraceConfig
from config.public.base_config_loader import LanguageEnum

# 初始化配置
config = FuncTimingTraceConfig()

mcp = FastMCP(
    "Function Timing Trace Tool MCP Server",
    host="0.0.0.0",
    port=config.get_config().private_config.port
)


@mcp.tool(
    name="func_timing_trace_tool"
    if config.get_config().public_config.language == LanguageEnum.ZH
    else "func_timing_trace_tool",
    description="""
    通过 `perf record -g` 采集指定进程的函数调用栈耗时。
    参数：
        pid: 目标进程 PID
        host: 可选，远程主机名称（使用public_config.toml中配置的name字段）；留空则本机执行。
    返回：
        dict {
            "top_functions": list,  # 热点函数列表
            "host": str             # 主机标识（本机为"localhost"）
        }
    """
    if config.get_config().public_config.language == LanguageEnum.ZH
    else """
    Collect function call stack and CPU time via `perf record -g`.
    Args:
        pid: Target process PID
        host: Optional remote host name (configured in public_config.toml); executes locally if omitted.
    Returns:
        dict {
            "top_functions": list,  # List of hot functions
            "host": str             # Host identifier ("localhost" for local)
        }
    """
)
def func_timing_trace_tool(pid: int, host: Optional[str] = None) -> Dict[str, Any]:
    """
    采集并解析 perf record 的调用栈耗时
    
    Args:
        pid: 进程 ID
        host: 远程主机名称（public_config.toml 中的 name），None 表示本机
        
    Returns:
        包含函数耗时分析结果的字典
    """
    cfg = config.get_config()
    is_zh = cfg.public_config.language == LanguageEnum.ZH
    
    # 本地执行
    if not host or host.strip().lower() in ("", "localhost"):
        return _execute_local_func_timing(pid, is_zh)
    
    # 远程执行
    return _execute_remote_func_timing_workflow(host.strip(), pid, cfg, is_zh)


def _execute_local_func_timing(pid: int, is_zh: bool) -> Dict[str, Any]:
    """执行本地函数耗时分析"""
    try:
        with tempfile.TemporaryDirectory() as tmp:
            perf_data_path = os.path.join(tmp, "perf.data")
            
            # 执行 perf record
            _run_local_perf_record(pid, perf_data_path, is_zh)
            
            # 执行 perf report
            report_output = _run_local_perf_report(perf_data_path, is_zh)
            
            # 解析结果
            result = _parse_perf_report(report_output)
            result["host"] = "localhost"
            return result
    except Exception as e:
        msg = f"本地函数耗时分析失败: {str(e)}" if is_zh else f"Local function timing failed: {str(e)}"
        raise RuntimeError(msg) from e


def _execute_remote_func_timing_workflow(
    host_name: str, pid: int, cfg, is_zh: bool
) -> Dict[str, Any]:
    """远程执行工作流"""
    target_host = _find_remote_host(host_name, cfg.public_config.remote_hosts, is_zh)
    
    try:
        # 执行远程函数耗时分析
        report_output = _execute_remote_func_timing(target_host, pid, is_zh)
        
        # 解析结果
        result = _parse_perf_report(report_output)
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


def _run_local_perf_record(pid: int, perf_data_path: str, is_zh: bool) -> None:
    """运行本地 perf record"""
    record_cmd = [
        "perf", "record", "-g", "--call-graph", "dwarf", "-F", "997",
        "-p", str(pid), "-o", perf_data_path, "--", "sleep", "30"
    ]
    
    try:
        subprocess.run(record_cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, check=True)
    except subprocess.CalledProcessError as e:
        msg = f"perf record 失败: {e.stderr.decode()}" if is_zh else f"perf record failed: {e.stderr.decode()}"
        raise RuntimeError(msg) from e


def _run_local_perf_report(perf_data_path: str, is_zh: bool) -> str:
    """运行本地 perf report"""
    report_cmd = ["perf", "report", "--no-children", "--stdio", "-i", perf_data_path]
    
    try:
        result = subprocess.run(report_cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        msg = f"perf report 失败: {e.stderr}" if is_zh else f"perf report failed: {e.stderr}"
        raise RuntimeError(msg) from e


def _execute_remote_func_timing(host_config, pid: int, is_zh: bool) -> str:
    """在远程主机执行函数耗时分析"""
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
        
        # 创建临时目录
        stdin, stdout, stderr = client.exec_command("mktemp -d")
        tmpdir = stdout.read().decode("utf-8").strip()
        perf_data_remote = os.path.join(tmpdir, "perf.data")
        
        # 执行 perf record
        _run_remote_perf_record(client, pid, perf_data_remote, is_zh)
        
        # 执行 perf report
        report_output = _run_remote_perf_report(client, perf_data_remote, is_zh)
        
        return report_output
    except paramiko.AuthenticationException as e:
        msg = "SSH认证失败" if is_zh else "SSH auth failed"
        raise ConnectionError(msg) from e
    finally:
        client.close()


def _run_remote_perf_record(client, pid: int, perf_data_path: str, is_zh: bool) -> None:
    """运行远程 perf record"""
    record_cmd = [
        "perf", "record", "-g", "--call-graph", "dwarf", "-F", "997",
        "-p", str(pid), "-o", perf_data_path, "--", "sleep", "30"
    ]
    record_cmd_str = " ".join(shlex.quote(arg) for arg in record_cmd)
    
    stdin, stdout, stderr = client.exec_command(record_cmd_str)
    stdin.close()
    
    exit_status = stdout.channel.recv_exit_status()
    if exit_status != 0:
        err = stderr.read().decode("utf-8").strip()
        msg = f"perf record 失败: {err}" if is_zh else f"perf record failed: {err}"
        raise RuntimeError(msg)


def _run_remote_perf_report(client, perf_data_path: str, is_zh: bool) -> str:
    """运行远程 perf report"""
    report_cmd = ["perf", "report", "--no-children", "--stdio", "-i", perf_data_path]
    report_cmd_str = " ".join(shlex.quote(arg) for arg in report_cmd)
    
    stdin, stdout, stderr = client.exec_command(report_cmd_str)
    stdin.close()
    
    stdout.channel.recv_exit_status()
    return stdout.read().decode("utf-8")


def _parse_perf_report(raw: str) -> Dict[str, Any]:
    """解析 perf report 输出"""
    line_pattern = re.compile(r"^\s*(\d+\.\d+)%.*?(\S+)", re.MULTILINE)
    functions = []
    for percent, symbol in line_pattern.findall(raw):
        if len(functions) >= 10:
            break
        functions.append({
            "function": symbol,
            "self_percent": float(percent),
            "total_percent": float(percent),
            "call_stack": [symbol]
        })
    return {"top_functions": functions}


if __name__ == "__main__":
    mcp.run(transport="sse")
