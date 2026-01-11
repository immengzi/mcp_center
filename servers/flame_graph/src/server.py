import os
import subprocess
from typing import Any, Dict, Optional

import paramiko
from mcp.server import FastMCP

from config.private.flame_graph.config_loader import FlameGraphConfig
from config.public.base_config_loader import LanguageEnum

# 初始化配置
config = FlameGraphConfig()

mcp = FastMCP(
    "FlameGraph Profiling Server",
    host="0.0.0.0",
    port=config.get_config().private_config.port
)


@mcp.tool(
    name="flame_graph"
    if config.get_config().public_config.language == LanguageEnum.ZH
    else "flame_graph",
    description="""
    生成CPU火焰图用于性能分析。
    参数：
        perf_data_path: perf.data输入路径（必选）
        flamegraph_path: FlameGraph脚本路径（必选）
        output_path: SVG输出路径（默认：~/cpu_flamegraph.svg）
        host: 可选，远程主机名称（使用public_config.toml中配置的name字段）；留空则本机执行。
    返回：
        dict {
            "svg_path": str,       # 生成的火焰图文件路径
            "status": str,         # 生成状态（success/failure）
            "message": str,        # 状态信息
            "host": str            # 主机标识（本机为"localhost"）
        }
    """
    if config.get_config().public_config.language == LanguageEnum.ZH
    else """
    Generate CPU flamegraph for performance analysis.
    Args:
        perf_data_path: perf.data input path (required)
        flamegraph_path: FlameGraph scripts path (required)
        output_path: SVG output path (default: ~/cpu_flamegraph.svg)
        host: Optional remote host name (configured in public_config.toml); executes locally if omitted.
    Returns:
        dict {
            "svg_path": str,       # Generated flamegraph file path
            "status": str,         # Generation status (success/failure)
            "message": str,        # Status message
            "host": str            # Host identifier ("localhost" for local)
        }
    """
)
def flame_graph(
    perf_data_path: str,
    flamegraph_path: str,
    output_path: str = os.path.expanduser("~/cpu_flamegraph.svg"),
    host: Optional[str] = None
) -> Dict[str, Any]:
    """
    生成CPU火焰图
    
    Args:
        perf_data_path: perf.data 输入路径
        flamegraph_path: FlameGraph 脚本路径
        output_path: SVG 输出路径
        host: 远程主机名称（public_config.toml 中的 name），None 表示本机
        
    Returns:
        包含火焰图生成结果的字典
    """
    cfg = config.get_config()
    is_zh = cfg.public_config.language == LanguageEnum.ZH
    
    # 参数验证
    if not perf_data_path:
        msg = "perf_data_path 不能为空" if is_zh else "perf_data_path is required"
        return {
            "svg_path": "",
            "status": "failure",
            "message": msg,
            "host": "localhost" if not host else host
        }
    
    if not flamegraph_path:
        msg = "flamegraph_path 不能为空" if is_zh else "flamegraph_path is required"
        return {
            "svg_path": "",
            "status": "failure",
            "message": msg,
            "host": "localhost" if not host else host
        }
    
    try:
        # 本地执行
        if not host or host.strip().lower() in ("", "localhost"):
            return _execute_local_flamegraph(
                perf_data_path, flamegraph_path, output_path, is_zh
            )
        
        # 远程执行
        return _execute_remote_flamegraph_workflow(
            host.strip(), perf_data_path, flamegraph_path, output_path, cfg, is_zh
        )
    except Exception as e:
        msg = f"火焰图生成失败: {str(e)}" if is_zh else f"Flamegraph generation failed: {str(e)}"
        return {
            "svg_path": "",
            "status": "failure",
            "message": msg,
            "host": "localhost" if not host else host
        }


def _execute_local_flamegraph(
    perf_data_path: str, flamegraph_path: str, output_path: str, is_zh: bool
) -> Dict[str, Any]:
    """执行本地火焰图生成"""
    try:
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 生成火焰图
        command = (
            f"perf script -i {perf_data_path} | "
            f"{flamegraph_path}/stackcollapse-perf.pl | "
            f"{flamegraph_path}/flamegraph.pl > {output_path}"
        )
        
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        
        msg = "火焰图生成成功" if is_zh else "Flamegraph generated successfully"
        return {
            "svg_path": output_path,
            "status": "success",
            "message": msg,
            "host": "localhost"
        }
    except subprocess.CalledProcessError as e:
        msg = f"本地火焰图生成失败: {e.stderr}" if is_zh else f"Local flamegraph failed: {e.stderr}"
        raise RuntimeError(msg) from e


def _execute_remote_flamegraph_workflow(
    host_name: str, perf_data_path: str, flamegraph_path: str,
    output_path: str, cfg, is_zh: bool
) -> Dict[str, Any]:
    """远程执行工作流"""
    target_host = _find_remote_host(host_name, cfg.public_config.remote_hosts, is_zh)
    
    try:
        _execute_remote_flamegraph(
            target_host, perf_data_path, flamegraph_path, output_path, is_zh
        )
        
        msg = "火焰图生成成功" if is_zh else "Flamegraph generated successfully"
        return {
            "svg_path": output_path,
            "status": "success",
            "message": msg,
            "host": target_host.name
        }
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


def _execute_remote_flamegraph(
    host_config, perf_data_path: str, flamegraph_path: str,
    output_path: str, is_zh: bool
) -> None:
    """在远程主机执行火焰图生成"""
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
        
        # 确保输出目录存在
        client.exec_command(f"mkdir -p {os.path.dirname(output_path)}")
        
        # 生成火焰图
        command = (
            f"perf script -i {perf_data_path} | "
            f"{flamegraph_path}/stackcollapse-perf.pl | "
            f"{flamegraph_path}/flamegraph.pl > {output_path}"
        )
        
        stdin, stdout, stderr = client.exec_command(command)
        stdin.close()
        
        exit_code = stdout.channel.recv_exit_status()
        
        if exit_code != 0:
            error_msg = stderr.read().decode()
            msg = f"远程火焰图生成失败: {error_msg}" if is_zh else f"Remote flamegraph failed: {error_msg}"
            raise RuntimeError(msg)
    except paramiko.AuthenticationException as e:
        msg = "SSH认证失败" if is_zh else "SSH auth failed"
        raise ConnectionError(msg) from e
    finally:
        client.close()


if __name__ == "__main__":
    mcp.run(transport='sse')
