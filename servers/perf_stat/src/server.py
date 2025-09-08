from typing import Dict, Any, Optional
import subprocess
import tempfile
import re
import os
import paramiko

from mcp.server import FastMCP
from config.public.base_config_loader import LanguageEnum
from config.private.perf_stat.config_loader import PerfStatConfig

cfg = PerfStatConfig().get_config()
mcp = FastMCP(
    "Perf-Stat Tool MCP Server",
    host="0.0.0.0",
    port=cfg.private_config.port
)

@mcp.tool(
    name="perf_stat_tool"
    if cfg.public_config.language == LanguageEnum.ZH
    else "perf_stat_tool",
    description="""
    通过 `perf stat -a -e cache-misses,cycles,instructions sleep 10` 采集整机的微架构指标。
    参数：
        host : 可选，远程主机 IP/域名；留空则采集本机。
    返回：
        dict  {
            "cache_misses": int,
            "cycles"      : int,
            "instructions": int,
            "ipc"         : float,        # instructions / cycles
            "seconds"     : float         # sleep 时长
        }
    """
    if cfg.public_config.language == LanguageEnum.ZH
    else """
    Collect whole-system micro-arch metrics via
    `perf stat -a -e cache-misses,cycles,instructions sleep 10`.
    Args:
        host : Optional remote IP/hostname; analyse local if omitted.
    Returns:
        dict  {
            "cache_misses": int,
            "cycles"      : int,
            "instructions": int,
            "ipc"         : float,
            "seconds"     : float
        }
    """
)
def perf_stat_tool(host: Optional[str] = None) -> Dict[str, Any]:
    """采集并解析 perf stat 结果"""
    cmd = ["perf", "stat", "-a", "-e", "cache-misses,cycles,instructions", "sleep", "10"]

    if host is None:
        with tempfile.TemporaryDirectory() as tmp:
            perf_data = os.path.join(tmp, "perf.data")
            completed = subprocess.run(
                cmd,
                stderr=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                text=True,
                check=True
            )
            return _parse_stat(completed.stderr)

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
        stdin, stdout, stderr = client.exec_command(" ".join(cmd))
        stdin.close()
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            raise RuntimeError(f"Remote perf stat failed, exit={exit_code}")
        stat_output = stderr.read().decode()
        return _parse_stat(stat_output)
    finally:
        client.close()

def _parse_stat(raw: str) -> Dict[str, Any]:
    """
    解析示例片段：
         3,361,887      cache-misses
       792,941,840      cycles
       292,432,459      instructions    # 0.37 insn per cycle
    """
    pat = re.compile(r"^\s*([\d,]+)\s+(cache-misses|cycles|instructions)", re.M)
    hit = {k: 0 for k in ("cache-misses", "cycles", "instructions")}
    for num, key in pat.findall(raw):
        hit[key] = int(num.replace(",", ""))

    ipc_match = re.search(r"#\s*([\d.]+)\s*insn per cycle", raw)
    ipc = float(ipc_match.group(1)) if ipc_match else 0.0

    sec_match = re.search(r"(\d+\.\d+)\s+seconds time elapsed", raw)
    seconds = float(sec_match.group(1)) if sec_match else 10.0

    return {
        "cache_misses": hit["cache-misses"],
        "cycles": hit["cycles"],
        "instructions": hit["instructions"],
        "ipc": ipc,
        "seconds": seconds
    }

if __name__ == "__main__":
    mcp.run(transport="sse")