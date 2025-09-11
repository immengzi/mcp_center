from typing import Dict, Any, Optional, List
import subprocess
import tempfile
import re
import os
import paramiko
from mcp.server import FastMCP
from config.public.base_config_loader import LanguageEnum
from config.private.hotspot_trace.config_loader import HotspotTrace

cfg = HotspotTrace().get_config()
mcp = FastMCP(
    "Perf-Top Tool MCP Server",
    host="0.0.0.0",
    port=cfg.private_config.port
)

@mcp.tool(
    name="hotspot_trace_tool"
    if cfg.public_config.language == LanguageEnum.ZH
    else "hotspot_trace_tool",
    description="""
    通过 `perf record -g` 采集指定进程的函数调用栈耗时。
    参数：
        pid : 目标进程 PID
        host : 可选，远程主机 IP/域名；留空则采集本机。
    返回：
        dict {
            "top_functions": List[{
                "function": str,
                "self_percent": float,   # 自身耗时占比
                "total_percent": float,  # 总耗时占比（含子函数）
                "call_stack": List[str]  # 调用栈（从最外层到当前函数）
            }]
        }
    """
    if cfg.public_config.language == LanguageEnum.ZH
    else """
    Collect function call stack and CPU time via `perf record -g`.
    Args:
        pid : Target process PID
        host : Optional remote IP/hostname; analyse local if omitted.
    Returns:
        dict {
            "top_functions": List[{
                "function": str,
                "self_percent": float,
                "total_percent": float,
                "call_stack": List[str]
            }]
        }
    """
)
def hotspot_trace_tool(pid: int, host: Optional[str] = None) -> Dict[str, Any]:
    """采集并解析 perf record 的调用栈耗时"""
    record_cmd = [
        "perf", "record", "-g", "--call-graph", "dwarf",
        "-F", "997", "-p", str(pid), "--", "sleep", "30"
    ]

    if host is None:
        with tempfile.TemporaryDirectory() as tmp:
            perf_data = os.path.join(tmp, "perf.data")
            subprocess.run(
                record_cmd,
                stderr=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                check=True
            )
            report_output = subprocess.run(
                ["perf", "report", "--no-children", "--stdio"],
                capture_output=True,
                text=True,
                check=True
            ).stdout
            return _parse_report(report_output)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=host,
        port=cfg.private_config.ssh_port or 22,
        username=cfg.private_config.ssh_username,
        key_filename=cfg.private_config.ssh_key_path,
        timeout=10
    )
    try:
        stdin, stdout, stderr = client.exec_command(" ".join(record_cmd))
        stdin.close()
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            raise RuntimeError(f"Remote perf record failed, exit={exit_code}")

        stdin, stdout, stderr = client.exec_command(
            "perf report --no-children --stdio"
        )
        stdin.close()
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            raise RuntimeError(f"Remote perf report failed, exit={exit_code}")

        report_output = stdout.read().decode()
        return _parse_report(report_output)
    finally:
        client.close()

def _parse_report(raw: str) -> Dict[str, Any]:
    line_pattern = re.compile(
        r"^\s*(\d+\.\d+)%\s+(\S+)\s+(\S+)\s+\[\.?\]?\s+(\S+)(?:\+0x[0-9a-f]+)?",
        re.MULTILINE
    )
    functions = []
    for percent, _, _, symbol in line_pattern.findall(raw):
        if len(functions) >= 10:
            break
        functions.append({
            "function": symbol,
            "self_percent": float(percent),
            "total_percent": float(percent),
            "call_stack": [symbol]
        })

    return {
        "top_functions": functions
    }

if __name__ == "__main__":
    mcp.run(transport="sse")