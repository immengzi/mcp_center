from typing import Union, Dict, Any, List
import paramiko
import subprocess
import re
import os
import json
import tempfile
from mcp.server import FastMCP
from config.public.base_config_loader import LanguageEnum
from config.private.func_timing_trace.config_loader import FuncTimingTraceConfig

mcp = FastMCP("Perf Events Tool MCP Server", host="0.0.0.0", port=FuncTimingTraceConfig().get_config().private_config.port)

@mcp.tool(
    name="func_timing_trace_tool"
    if FuncTimingTraceConfig().get_config().public_config.language == LanguageEnum.ZH
    else "func_timing_trace_tool",
    description='''
    通过 perf record 和 perf report 分析系统或指定进程的 CPU 性能瓶颈
    1. 输入值如下：
        - host: 远程主机名称或IP地址，若不提供则表示获取本机信息
        - pid: 要分析的进程ID，若不提供则分析整个系统
    2. 返回值为包含性能分析结果的字典，包含以下键：
        - total_samples: 总样本数
        - event_count: 事件计数（如 cycles）
        - hot_functions: 热点函数列表（按 Children 百分比排序）
    '''
    if FuncTimingTraceConfig().get_config().public_config.language == LanguageEnum.ZH
    else 
    '''
    Analyze CPU performance bottlenecks of the system or a specific process using perf record and perf report
    1. Input values are as follows:
        - host: Remote host name or IP address. If not provided, retrieves local machine info.
        - pid: Target process ID. If not provided, analyzes the entire system.
    2. The return value is a dictionary containing performance analysis results, with the following keys:
        - total_samples: Total number of samples
        - event_count: Event count (e.g., cycles)
        - hot_functions: List of hot functions sorted by Children percentage
    '''
)
def func_timing_trace_tool(host: Union[str, None] = None, pid: Union[int, None] = None) -> Dict[str, Any]:
    """
    分析系统或指定进程的 CPU 性能瓶颈
    """
    def _parse_size(size_str: str) -> int:
        units = {"K": 1024, "M": 1024 ** 2, "G": 1024 ** 3, "T": 1024 ** 4}
        size_str = size_str.upper()
        for suffix, multi in units.items():
            if size_str.endswith(suffix):
                return int(float(size_str[:-1]) * multi)
        return int(size_str)

    def parse_perf_report(output: str, topk: int = 5) -> Dict[str, Any]:
        result = {"total_samples": 0, "event_count": 0, "hot_functions": []}

        m = re.search(r"^Samples:\s+([\dKMGT]+)\b", output, re.M)
        if m:
            result["total_samples"] = _parse_size(m.group(1))

        m = re.search(r"Event count \(approx\.\):\s+(\d+)", output)
        if m:
            result["event_count"] = int(m.group(1))

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

    try:
        perf_record_cmd = ["perf", "record"]
        if pid:
            perf_record_cmd.extend(["-p", str(pid)])
        else:
            perf_record_cmd.append("-a")
        perf_record_cmd.extend(["sleep", "10"])

        perf_report_cmd = ["perf", "report", "--stdio"]

        if host is None:
            with tempfile.TemporaryDirectory() as tmpdir:
                perf_data_path = os.path.join(tmpdir, "perf.data")

                print(f"[Local] Running: {' '.join(perf_record_cmd)}")
                subprocess.run(perf_record_cmd, check=True)

                print(f"[Local] Running: {' '.join(perf_report_cmd)}")
                result = subprocess.run(perf_report_cmd, capture_output=True, text=True, check=True)
                return parse_perf_report(result.stdout)

        else:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            config = FuncTimingTraceConfig().get_config()
            username = config.private_config.ssh_username
            key_file = config.private_config.ssh_key_path
            port = config.private_config.ssh_port or 22

            client.connect(host, port=port, username=username, key_filename=key_file, timeout=10)

            stdin, stdout, stderr = client.exec_command("mktemp -d")
            tmpdir = stdout.read().decode("utf-8").strip()
            perf_data_path = f"{tmpdir}/perf.data"

            print(f"[Remote] Running: {' '.join(perf_record_cmd)} on {host}")
            stdin, stdout, stderr = client.exec_command(" ".join(perf_record_cmd))
            stdin.close()
            stdout.channel.recv_exit_status()

            print(f"[Remote] Running: {' '.join(perf_report_cmd)} on {host}")
            stdin, stdout, stderr = client.exec_command(" ".join(perf_report_cmd))
            output = stdout.read().decode("utf-8")
            client.close()

            return parse_perf_report(output)

    except subprocess.CalledProcessError as e:
        if FuncTimingTraceConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise RuntimeError(f"本地 perf 命令执行失败: {e.stderr}")
        else:
            raise RuntimeError(f"Local perf command failed: {e.stderr}")
    except paramiko.AuthenticationException:
        if FuncTimingTraceConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise RuntimeError("SSH 认证失败，请检查用户名或密钥")
        else:
            raise RuntimeError("SSH authentication failed, please check the username or key")
    except paramiko.SSHException as e:
        if FuncTimingTraceConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise RuntimeError(f"SSH 连接错误: {e}")
        else:
            raise RuntimeError(f"SSH connection error: {e}")
    except Exception as e:
        if FuncTimingTraceConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise RuntimeError(f"性能分析失败: {str(e)}")
        else:
            raise RuntimeError(f"Performance analysis failed: {str(e)}")


if __name__ == "__main__":
    # 启动服务
    mcp.run(transport='sse')