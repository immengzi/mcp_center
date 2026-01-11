import os
import re
import shlex
import subprocess
import tempfile
from typing import Any, Dict, Optional

import paramiko
from mcp.server import FastMCP

from config.private.hotspot_trace.config_loader import HotspotTraceConfig
from config.public.base_config_loader import LanguageEnum

# 初始化配置
config = HotspotTraceConfig()

mcp = FastMCP(
    "Hotspot Trace Tool MCP Server",
    host="0.0.0.0",
    port=config.get_config().private_config.port
)


@mcp.tool(
    name="hotspot_trace_tool"
    if config.get_config().public_config.language == LanguageEnum.ZH
    else "hotspot_trace_tool",
    description="""
    通过 perf record 和 perf report 分析系统或指定进程的 CPU 性能瓶颈。
    参数：
        pid: 要分析的进程ID，若不提供则分析整个系统
        host: 可选，远程主机名称（使用public_config.toml中配置的name字段）；留空则本机执行。
    返回：
        dict {
            "total_samples": int,        # 总样本数
            "event_count": int,          # 事件计数（如 cycles）
            "hot_functions": list,       # 热点函数列表（按 Overhead 百分比排序）
            "host": str                  # 主机标识（本机为"localhost"）
        }
    """
    if config.get_config().public_config.language == LanguageEnum.ZH
    else """
    Analyze CPU performance bottlenecks of the system or a specific process using perf record and perf report.
    Args:
        pid: Target process ID. If not provided, analyzes the entire system.
        host: Optional remote host name (configured in public_config.toml); executes locally if omitted.
    Returns:
        dict {
            "total_samples": int,        # Total number of samples
            "event_count": int,          # Event count (e.g., cycles)
            "hot_functions": list,       # List of hot functions sorted by Overhead percentage
            "host": str                  # Host identifier ("localhost" for local)
        }
    """
)
def hotspot_trace_tool(pid: Optional[int] = None, host: Optional[str] = None) -> Dict[str, Any]:
    """
    分析系统或指定进程的 CPU 性能瓶颈
    
    Args:
        pid: 进程 ID，None 表示分析整个系统
        host: 远程主机名称（public_config.toml 中的 name），None 表示本机
        
    Returns:
        包含性能分析结果的字典
    """
    cfg = config.get_config()
    is_zh = cfg.public_config.language == LanguageEnum.ZH
    
    # 本地执行
    if not host or host.strip().lower() in ("", "localhost"):
        return _execute_local_hotspot_trace(pid, is_zh)
    
    # 远程执行
    return _execute_remote_hotspot_trace_workflow(host.strip(), pid, cfg, is_zh)


def _execute_local_hotspot_trace(pid: Optional[int], is_zh: bool) -> Dict[str, Any]:
    """执行本地性能分析"""
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            perf_data_path = os.path.join(tmpdir, "perf.data")
            
            # 执行 perf record
            _run_local_perf_record(perf_data_path, pid, is_zh)
            
            # 执行 perf report
            report_output = _run_local_perf_report(perf_data_path, is_zh)
            
            # 解析结果
            result = _parse_perf_report(report_output)
            result["host"] = "localhost"
            return result
    except Exception as e:
        msg = f"本地性能分析失败: {str(e)}" if is_zh else f"Local performance analysis failed: {str(e)}"
        raise RuntimeError(msg) from e


def _execute_remote_hotspot_trace_workflow(
    host_name: str, pid: Optional[int], cfg, is_zh: bool
) -> Dict[str, Any]:
    """远程执行工作流"""
    target_host = _find_remote_host(host_name, cfg.public_config.remote_hosts, is_zh)
    
    try:
        # 执行远程性能分析
        report_output = _execute_remote_hotspot_trace(target_host, pid, is_zh)
        
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


def _run_local_perf_record(perf_data_path: str, pid: Optional[int], is_zh: bool) -> None:
    """运行本地 perf record"""
    perf_record_cmd = ["perf", "record", "-o", perf_data_path]
    if pid:
        perf_record_cmd.extend(["-p", str(pid)])
    else:
        perf_record_cmd.append("-a")
    perf_record_cmd.extend(["sleep", "10"])
    
    try:
        subprocess.run(perf_record_cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        msg = f"perf record 失败: {e.stderr.decode()}" if is_zh else f"perf record failed: {e.stderr.decode()}"
        raise RuntimeError(msg) from e


def _run_local_perf_report(perf_data_path: str, is_zh: bool) -> str:
    """运行本地 perf report"""
    perf_report_cmd = ["perf", "report", "--stdio", "-i", perf_data_path]
    
    try:
        result = subprocess.run(perf_report_cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        msg = f"perf report 失败: {e.stderr}" if is_zh else f"perf report failed: {e.stderr}"
        raise RuntimeError(msg) from e


def _execute_remote_hotspot_trace(host_config, pid: Optional[int], is_zh: bool) -> str:
    """在远程主机执行性能分析"""
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
        
        # 远程文件路径
        perf_data_remote = "/tmp/perf.data"
        
        # 清理旧文件
        client.exec_command(f"rm -f {shlex.quote(perf_data_remote)}")
        
        # 执行 perf record
        _run_remote_perf_record(client, perf_data_remote, pid, is_zh)
        
        # 执行 perf report
        report_output = _run_remote_perf_report(client, perf_data_remote, is_zh)
        
        return report_output
    except paramiko.AuthenticationException as e:
        msg = "SSH认证失败" if is_zh else "SSH auth failed"
        raise ConnectionError(msg) from e
    finally:
        client.close()


def _run_remote_perf_record(client, perf_data_path: str, pid: Optional[int], is_zh: bool) -> None:
    """运行远程 perf record"""
    perf_record_cmd = ["perf", "record", "-o", perf_data_path]
    if pid:
        perf_record_cmd.extend(["-p", str(pid)])
    else:
        perf_record_cmd.append("-a")
    perf_record_cmd.extend(["sleep", "10"])
    
    perf_record_remote_cmd = " ".join(shlex.quote(arg) for arg in perf_record_cmd)
    
    stdin, stdout, stderr = client.exec_command(perf_record_remote_cmd)
    stdin.close()
    
    exit_status = stdout.channel.recv_exit_status()
    err = stderr.read().decode("utf-8").strip()
    
    if exit_status != 0:
        msg = f"perf record 失败: {err}" if is_zh else f"perf record failed: {err}"
        raise RuntimeError(msg)


def _run_remote_perf_report(client, perf_data_path: str, is_zh: bool) -> str:
    """运行远程 perf report"""
    perf_report_cmd = ["perf", "report", "--stdio", "-i", perf_data_path]
    perf_report_remote_cmd = " ".join(shlex.quote(arg) for arg in perf_report_cmd)
    
    stdin, stdout, stderr = client.exec_command(perf_report_remote_cmd)
    stdin.close()
    
    output = stdout.read().decode("utf-8")
    err = stderr.read().decode("utf-8").strip()
    
    if err:
        msg = f"perf report 失败: {err}" if is_zh else f"perf report failed: {err}"
        raise RuntimeError(msg)
    
    return output


def _parse_perf_report(output: str, topk: int = 5) -> Dict[str, Any]:
    """解析 perf report 输出"""
    result = {"total_samples": 0, "event_count": 0, "hot_functions": []}
    
    # 解析总样本数
    m = re.search(r"^Samples:\s+([\dKMGT]+)\b", output, re.M)
    if m:
        result["total_samples"] = _parse_size(m.group(1))
    
    # 解析事件计数
    m = re.search(r"Event count \(approx\.\):\s+(\d+)", output)
    if m:
        result["event_count"] = int(m.group(1))
    
    # 解析热点函数
    header_hit = False
    for line in output.splitlines():
        if not line or line.startswith("#"):
            if "Overhead" in line:
                header_hit = True
            continue
        if header_hit:
            m = re.match(
                r"^\s*(?P<overhead>\d+(?:\.\d+)?)%\s+"
                r"(?P<command>\S+)\s+"
                r"(?P<so>\S+)\s+"
                r"(?P<sym_raw>\[([.\w])\]\s*.+)$",
                line
            )
            if not m:
                continue
            overhead = float(m.group("overhead"))
            command = m.group("command")
            so = m.group("so")
            sym_full = m.group("sym_raw").strip()
            sym_type, symbol = sym_full[1], sym_full[4:].strip()
            result["hot_functions"].append({
                "overhead": overhead,
                "command": command,
                "shared_object": so,
                "symbol": symbol,
                "symbol_type": sym_type
            })
    
    result["hot_functions"].sort(key=lambda x: x["overhead"], reverse=True)
    result["hot_functions"] = result["hot_functions"][:topk]
    return result


def _parse_size(size_str: str) -> int:
    """解析带单位的数字"""
    units = {"K": 1024, "M": 1024 ** 2, "G": 1024 ** 3, "T": 1024 ** 4}
    size_str = size_str.upper()
    for suffix, multi in units.items():
        if size_str.endswith(suffix):
            return int(float(size_str[:-1]) * multi)
    return int(size_str)


if __name__ == "__main__":
    mcp.run(transport='sse')
