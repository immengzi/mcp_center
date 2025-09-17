from typing import Dict, Any, Optional, List
import subprocess
import tempfile
import re
import os
import shlex
import paramiko
from mcp.server import FastMCP
from config.public.base_config_loader import LanguageEnum
from config.private.perf_stat.config_loader import PerfStatConfig

mcp = FastMCP(
    "Perf-Top Tool MCP Server",
    host="0.0.0.0",
    port=PerfStatConfig().get_config().private_config.port
)

@mcp.tool(
    name="perf_top_tool"
    if PerfStatConfig().get_config().public_config.language == LanguageEnum.ZH
    else "perf_top_tool",
    description="""
    通过 `perf record -g` 采集指定进程的函数调用栈耗时。
    参数：
        pid : 目标进程 PID
        host : 可选，远程主机 IP/域名；留空则采集本机。
    返回：
        dict {
            "top_functions": List[{
                "function": str,
                "self_percent": float,
                "total_percent": float,
                "call_stack": List[str]
            }]
        }
    """
    if PerfStatConfig().get_config().public_config.language == LanguageEnum.ZH
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
def perf_top_tool(pid: int, host: Optional[str] = None) -> Dict[str, Any]:
    """采集并解析 perf record 的调用栈耗时"""
    record_cmd_base = [
        "perf", "record", "-g", "--call-graph", "dwarf", "-F", "997", "-p", str(pid)
    ]
    report_cmd = ["perf", "report", "--no-children", "--stdio"]

    def parse_report(raw: str) -> Dict[str, Any]:
        # 宽松正则，匹配 kernel 和用户态函数
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

    try:
        if host is None:
            with tempfile.TemporaryDirectory() as tmp:
                perf_data_path = os.path.join(tmp, "perf.data")
                # -o 放在 -- 之前
                record_cmd_local = record_cmd_base + ["-o", perf_data_path, "--", "sleep", "30"]

                subprocess.run(record_cmd_local, stderr=subprocess.PIPE, stdout=subprocess.PIPE, check=True)
                report_cmd_local = report_cmd + ["-i", perf_data_path]
                report_output = subprocess.run(report_cmd_local, capture_output=True, text=True, check=True).stdout
                return parse_report(report_output)

        else:
            # 远程执行
            config = PerfStatConfig().get_config()
            target_host = None
            for h in config.public_config.remote_hosts:
                if host.strip() == h.name or host.strip() == h.host:
                    target_host = h
                    break
            if not target_host:
                raise ValueError(f"未找到远程主机: {host}" if config.public_config.language == LanguageEnum.ZH
                                 else f"Remote host not found: {host}")

            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                hostname=target_host.host,
                port=getattr(target_host, 'port', 22),
                username=getattr(target_host, 'username', None),
                password=getattr(target_host, 'password', None),
                key_filename=getattr(target_host, 'ssh_key_path', None),
                timeout=10
            )

            stdin, stdout, stderr = client.exec_command("mktemp -d")
            tmpdir = stdout.read().decode("utf-8").strip()
            perf_data_remote = os.path.join(tmpdir, "perf.data")
            record_cmd_remote = record_cmd_base + ["-o", perf_data_remote, "--", "sleep", "30"]
            record_cmd_str = " ".join(shlex.quote(arg) for arg in record_cmd_remote)
            stdin, stdout, stderr = client.exec_command(record_cmd_str)
            stdout.channel.recv_exit_status()

            report_cmd_remote = report_cmd + ["-i", perf_data_remote]
            report_cmd_str = " ".join(shlex.quote(arg) for arg in report_cmd_remote)
            stdin, stdout, stderr = client.exec_command(report_cmd_str)
            stdout.channel.recv_exit_status()
            report_output = stdout.read().decode("utf-8")
            client.close()

            return parse_report(report_output)

    except subprocess.CalledProcessError as e:
        msg = e.stderr or e.stdout or str(e)
        raise RuntimeError(f"本地 perf 执行失败: {msg}" if PerfStatConfig().get_config().public_config.language == LanguageEnum.ZH
                           else f"Local perf execution failed: {msg}")
    except paramiko.AuthenticationException:
        raise RuntimeError("SSH 认证失败，请检查用户名或密钥" if PerfStatConfig().get_config().public_config.language == LanguageEnum.ZH
                           else "SSH authentication failed, please check the username or key")
    except paramiko.SSHException as e:
        raise RuntimeError(f"SSH 连接错误: {e}" if PerfStatConfig().get_config().public_config.language == LanguageEnum.ZH
                           else f"SSH connection error: {e}")
    except Exception as e:
        raise RuntimeError(f"性能分析失败: {str(e)}" if PerfStatConfig().get_config().public_config.language == LanguageEnum.ZH
                           else f"Performance analysis failed: {str(e)}")


if __name__ == "__main__":
    mcp.run(transport="sse")
