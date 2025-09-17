from typing import Union, Dict, Any
import paramiko
import subprocess
import re
import os
import tempfile
import shlex
from mcp.server import FastMCP
from config.public.base_config_loader import LanguageEnum
from config.private.hotspot_trace.config_loader import HotspotTraceConfig

mcp = FastMCP(
    "Hotspot Trace Tool MCP Server",
    host="0.0.0.0",
    port=HotspotTraceConfig().get_config().private_config.port
)

@mcp.tool(
    name="hotspot_trace_tool"
    if HotspotTraceConfig().get_config().public_config.language == LanguageEnum.ZH
    else "hotspot_trace_tool",
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
    if HotspotTraceConfig().get_config().public_config.language == LanguageEnum.ZH
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
def hotspot_trace_tool(host: Union[str, None] = None, pid: Union[int, None] = None) -> Dict[str, Any]:
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
        if host is None:
            # 本地执行
            with tempfile.TemporaryDirectory() as tmpdir:
                perf_data_path = os.path.join(tmpdir, "perf.data")
                perf_record_cmd = ["perf", "record", "-o", perf_data_path]
                if pid:
                    perf_record_cmd.extend(["-p", str(pid)])
                else:
                    perf_record_cmd.append("-a")
                perf_record_cmd.extend(["sleep", "10"])

                subprocess.run(perf_record_cmd, check=True)
                perf_report_cmd = ["perf", "report", "--stdio", "-i", perf_data_path]
                result = subprocess.run(perf_report_cmd, capture_output=True, text=True, check=True)
                return parse_perf_report(result.stdout)

        else:
            # 远程执行
            config = HotspotTraceConfig().get_config()
            target_host = None
            for h in config.public_config.remote_hosts:
                if host.strip() == h.name or host.strip() == h.host:
                    target_host = h
                    break
            if not target_host:
                msg = f"未找到远程主机: {host}" if config.public_config.language == LanguageEnum.ZH else f"Remote host not found: {host}"
                raise ValueError(msg)

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

            # 固定远程文件路径
            perf_data_remote = "/tmp/perf.data"
            client.exec_command(f"rm -f {shlex.quote(perf_data_remote)}")

            # perf record
            perf_record_cmd = ["perf", "record", "-o", perf_data_remote]
            if pid:
                perf_record_cmd.extend(["-p", str(pid)])
            else:
                perf_record_cmd.append("-a")
            perf_record_cmd.extend(["sleep", "10"])
            perf_record_remote_cmd = " ".join(shlex.quote(arg) for arg in perf_record_cmd)

            stdin, stdout, stderr = client.exec_command(perf_record_remote_cmd)
            exit_status = stdout.channel.recv_exit_status()
            err = stderr.read().decode("utf-8").strip()
            if exit_status != 0:
                raise RuntimeError(err or f"perf record exited with code {exit_status}")

            # perf report
            perf_report_cmd = ["perf", "report", "--stdio", "-i", perf_data_remote]
            perf_report_remote_cmd = " ".join(shlex.quote(arg) for arg in perf_report_cmd)
            stdin, stdout, stderr = client.exec_command(perf_report_remote_cmd)
            output = stdout.read().decode("utf-8")
            err = stderr.read().decode("utf-8").strip()
            client.close()
            if err:
                raise RuntimeError(err)

            return parse_perf_report(output)

    except subprocess.CalledProcessError as e:
        msg = e.stderr or e.stdout or str(e)
        lang = HotspotTraceConfig().get_config().public_config.language
        raise RuntimeError(f"本地 perf 命令执行失败: {msg}" if lang == LanguageEnum.ZH else f"Local perf command failed: {msg}")
    except paramiko.AuthenticationException:
        lang = HotspotTraceConfig().get_config().public_config.language
        raise RuntimeError("SSH 认证失败，请检查用户名或密钥" if lang == LanguageEnum.ZH else "SSH authentication failed, please check the username or key")
    except paramiko.SSHException as e:
        lang = HotspotTraceConfig().get_config().public_config.language
        raise RuntimeError(f"SSH 连接错误: {e}" if lang == LanguageEnum.ZH else f"SSH connection error: {e}")
    except Exception as e:
        lang = HotspotTraceConfig().get_config().public_config.language
        raise RuntimeError(f"性能分析失败: {str(e)}" if lang == LanguageEnum.ZH else f"Performance analysis failed: {str(e)}")


if __name__ == "__main__":
    mcp.run(transport='sse')
