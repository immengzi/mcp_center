from typing import Any, Dict, Optional
import paramiko
import subprocess
import os
from mcp.server import FastMCP
from config.public.base_config_loader import LanguageEnum
from config.private.flame_graph.config_loader import FlameGraphConfig

mcp = FastMCP(
    "FlameGraph Profiling Server",
    host="0.0.0.0",
    port=FlameGraphConfig().get_config().private_config.port
)


@mcp.tool(
    name="flame_graph"
    if FlameGraphConfig().get_config().public_config.language == LanguageEnum.ZH
    else "flame_graph",
    description='''
生成CPU火焰图用于性能分析
1. 输入参数：
    - host: 远程主机地址（可选）
    - perf_data_path: perf.data输入路径（必选）
    - output_path: SVG输出路径（默认：~/cpu_flamegraph.svg）
    - flamegraph_path: FlameGraph脚本路径（必选）
2. 返回字段：
    - svg_path: 生成的火焰图文件路径
    - status: 生成状态（success/failure）
    - message: 状态信息
    '''
    if FlameGraphConfig().get_config().public_config.language == LanguageEnum.ZH
    else '''
Generate CPU flamegraph for performance analysis
1. Input parameters:
    - host: Remote host address (optional)
    - perf_data_path: perf.data input path (required)
    - output_path: SVG output path (default: ~/cpu_flamegraph.svg)
    - flamegraph_path: FlameGraph scripts path (required)
2. Return fields:
    - svg_path: Generated flamegraph file path
    - status: Generation status (success/failure)
    - message: Status message
    '''
)
def flame_graph(
    host: Optional[str] = None,
    perf_data_path: str = "",
    output_path: str = os.path.expanduser("~/cpu_flamegraph.svg"),
    flamegraph_path: str = ""
) -> Dict[str, Any]:
    """生成CPU火焰图"""

    if not perf_data_path:
        return {
            "svg_path": "",
            "status": "failure",
            "message": "perf_data_path is required"
        }
    if not flamegraph_path:
        return {
            "svg_path": "",
            "status": "failure",
            "message": "flamegraph_path is required"
        }

    try:
        if host:
            remote_config = next(
                (h for h in FlameGraphConfig().get_config().public_config.remote_hosts
                 if h.name == host or h.host == host),
                None
            )

            if not remote_config:
                raise ValueError(f"Remote host configuration not found for {host}")

            # 连接远程主机
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=remote_config.host,
                port=remote_config.port,
                username=remote_config.username,
                password=remote_config.password
            )

            # 确保目录存在
            ssh.exec_command(f"mkdir -p {os.path.dirname(output_path)}")

            # 生成命令
            command = (
                f"perf script -i {perf_data_path} | "
                f"{flamegraph_path}/stackcollapse-perf.pl | "
                f"{flamegraph_path}/flamegraph.pl > {output_path}"
            )

            stdin, stdout, stderr = ssh.exec_command(command)
            exit_code = stdout.channel.recv_exit_status()

            if exit_code != 0:
                error_msg = stderr.read().decode()
                raise RuntimeError(f"Remote flamegraph generation failed: {error_msg}")

            ssh.close()
            return {
                "svg_path": output_path,
                "status": "success",
                "message": "Flamegraph generated successfully on remote host"
            }

        else:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            command = (
                f"perf script -i {perf_data_path} | "
                f"{flamegraph_path}/stackcollapse-perf.pl | "
                f"{flamegraph_path}/flamegraph.pl > {output_path}"
            )

            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                raise RuntimeError(f"Local flamegraph generation failed: {result.stderr}")

            return {
                "svg_path": output_path,
                "status": "success",
                "message": "Flamegraph generated successfully locally"
            }

    except Exception as e:
        return {
            "svg_path": "",
            "status": "failure",
            "message": f"Flamegraph generation failed: {str(e)}"
        }


if __name__ == "__main__":
    mcp.run(transport='sse')
