import re
import subprocess
from datetime import datetime
from typing import Any, Dict, Optional, Union

import paramiko
from mcp.server import FastMCP

from config.private.numa_perf_compare.config_loader import NumaPerfCompareConfig
from config.public.base_config_loader import LanguageEnum

# 初始化配置
config = NumaPerfCompareConfig()

mcp = FastMCP(
    "NUMA Performance Comparison MCP Server",
    host="0.0.0.0",
    port=config.get_config().private_config.port
)


@mcp.tool(
    name="numa_perf_compare"
    if config.get_config().public_config.language == LanguageEnum.ZH
    else "numa_perf_compare",
    description="""
    执行NUMA基准测试，支持不同绑定策略：
    1. 本地绑定：CPU 和内存在同一节点
    2. 跨节点绑定：CPU 和内存在不同节点
    3. 不绑定：使用系统默认行为
    参数：
        benchmark: 基准测试可执行文件路径（如 /root/mcp_center/stream）
        host: 可选，远程主机名称（使用public_config.toml中配置的name字段）；留空则本机执行。
    返回：
        dict {
            "numa_nodes": int,        # NUMA节点数量
            "test_results": dict,     # 测试结果字典
            "timestamp": str,         # 时间戳
            "host": str               # 主机标识（本机为"localhost"）
        }
    """
    if config.get_config().public_config.language == LanguageEnum.ZH
    else """
    Run NUMA benchmark tests with different binding strategies:
    1. Local binding: CPU and memory on the same node
    2. Cross-node binding: CPU and memory on different nodes
    3. No binding: Default system behavior
    Args:
        benchmark: Path to the benchmark executable (e.g., /root/mcp_center/stream)
        host: Optional remote host name (configured in public_config.toml); executes locally if omitted.
    Returns:
        dict {
            "numa_nodes": int,        # Number of NUMA nodes
            "test_results": dict,     # Test results dictionary
            "timestamp": str,         # Timestamp
            "host": str               # Host identifier ("localhost" for local)
        }
    """
)
async def numa_perf_compare(benchmark: str, host: Optional[str] = None) -> Dict[str, Any]:
    """
    执行NUMA基准测试
    
    Args:
        benchmark: 基准测试可执行文件路径
        host: 远程主机名称（public_config.toml 中的 name），None 表示本机
        
    Returns:
        包含测试结果的字典
    """
    cfg = config.get_config()
    is_zh = cfg.public_config.language == LanguageEnum.ZH
    
    try:
        # 本地执行
        if not host or host.strip().lower() in ("", "localhost"):
            return _execute_local_benchmark(benchmark, is_zh)
        
        # 远程执行
        return _execute_remote_benchmark_workflow(host.strip(), benchmark, cfg, is_zh)
    except Exception as e:
        msg = f"测试失败: {str(e)}" if is_zh else f"Test failed: {str(e)}"
        return {
            "error": msg,
            "timestamp": datetime.now().isoformat(),
            "host": "localhost" if not host else host
        }


def _execute_local_benchmark(benchmark: str, is_zh: bool) -> Dict[str, Any]:
    """执行本地基准测试"""
    try:
        numa_nodes = _get_local_numa_nodes(is_zh)
        results = _run_all_benchmarks(benchmark, numa_nodes, None, is_zh)
        results["host"] = "localhost"
        return results
    except Exception as e:
        msg = f"本地测试失败: {str(e)}" if is_zh else f"Local test failed: {str(e)}"
        raise RuntimeError(msg) from e


def _execute_remote_benchmark_workflow(
    host_name: str, benchmark: str, cfg, is_zh: bool
) -> Dict[str, Any]:
    """远程执行工作流"""
    target_host = _find_remote_host(host_name, cfg.public_config.remote_hosts, is_zh)
    
    try:
        numa_nodes = _get_remote_numa_nodes(target_host, is_zh)
        results = _run_all_benchmarks(benchmark, numa_nodes, target_host, is_zh)
        results["host"] = target_host.name
        return results
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


def _get_local_numa_nodes(is_zh: bool) -> int:
    """获取本地NUMA节点数量"""
    try:
        result = subprocess.run(
            ['numactl', '--hardware'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        match = re.search(r'available:\s+(\d+)', result.stdout)
        if not match:
            raise RuntimeError("Could not parse NUMA nodes from output")
        return int(match.group(1))
    except subprocess.CalledProcessError as e:
        msg = f"获取NUMA节点失败: {e.stderr}" if is_zh else f"Failed to get NUMA nodes: {e.stderr}"
        raise RuntimeError(msg) from e


def _get_remote_numa_nodes(host_config, is_zh: bool) -> int:
    """获取远程NUMA节点数量"""
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
        
        stdin, stdout, stderr = client.exec_command('numactl --hardware')
        stdin.close()
        
        output = stdout.read().decode('utf-8')
        match = re.search(r'available:\s+(\d+)', output)
        if not match:
            raise RuntimeError("Could not parse NUMA nodes from remote output")
        return int(match.group(1))
    except paramiko.AuthenticationException as e:
        msg = "SSH认证失败" if is_zh else "SSH auth failed"
        raise ConnectionError(msg) from e
    finally:
        client.close()


def _run_all_benchmarks(
    benchmark: str, numa_nodes: int, host_config: Optional[Any], is_zh: bool
) -> Dict[str, Any]:
    """运行所有基准测试"""
    first_node = 0
    last_node = numa_nodes - 1
    results = {}
    
    # 本地绑定测试
    local_result = _run_single_benchmark(
        benchmark, first_node, first_node, host_config, is_zh
    )
    results["local_binding"] = {
        "description": f"CPU and memory bound to node {first_node}",
        "result": local_result
    }
    
    # 跨节点绑定测试
    if numa_nodes > 1:
        cross_result = _run_single_benchmark(
            benchmark, first_node, last_node, host_config, is_zh
        )
        results["cross_node_binding"] = {
            "description": f"CPU on node {first_node}, memory on node {last_node}",
            "result": cross_result
        }
    
    # 不绑定测试
    no_bind_result = _run_single_benchmark(
        benchmark, "all", "all", host_config, is_zh
    )
    results["no_binding"] = {
        "description": "No CPU/memory binding",
        "result": no_bind_result
    }
    
    return {
        "numa_nodes": numa_nodes,
        "test_results": results,
        "timestamp": datetime.now().isoformat()
    }


def _run_single_benchmark(
    benchmark_path: str,
    cpu_node: Union[int, str],
    mem_node: Union[int, str],
    host_config: Optional[Any],
    is_zh: bool
) -> Dict[str, Any]:
    """运行单个基准测试"""
    # 构造 numa 绑定参数
    numa_args = []
    if cpu_node != "all":
        numa_args.append(f'--cpunodebind={cpu_node}')
    if mem_node != "all":
        numa_args.append(f'--membind={mem_node}')
    
    if host_config is None:
        return _run_local_benchmark(benchmark_path, numa_args, is_zh)
    else:
        return _run_remote_benchmark(benchmark_path, numa_args, host_config, is_zh)


def _run_local_benchmark(
    benchmark_path: str, numa_args: list, is_zh: bool
) -> Dict[str, Any]:
    """运行本地基准测试"""
    command = (['numactl'] + numa_args + [benchmark_path]) if numa_args else [benchmark_path]
    
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        
        return {
            "command": " ".join(command),
            "output": result.stdout,
            "error": result.stderr,
            "return_code": result.returncode,
            "metrics": {"raw_output": result.stdout}
        }
    except Exception as e:
        msg = f"基准测试执行失败: {str(e)}" if is_zh else f"Benchmark execution failed: {str(e)}"
        raise RuntimeError(msg) from e


def _run_remote_benchmark(
    benchmark_path: str, numa_args: list, host_config, is_zh: bool
) -> Dict[str, Any]:
    """运行远程基准测试"""
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
        
        remote_cmd = (['numactl'] + numa_args + [benchmark_path]) if numa_args else [benchmark_path]
        remote_cmd_str = " ".join(remote_cmd)
        
        stdin, stdout, stderr = client.exec_command(remote_cmd_str)
        stdin.close()
        
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')
        return_code = stdout.channel.recv_exit_status()
        
        return {
            "command": remote_cmd_str,
            "output": output,
            "error": error,
            "return_code": return_code,
            "metrics": {"raw_output": output}
        }
    except paramiko.AuthenticationException as e:
        msg = "SSH认证失败" if is_zh else "SSH auth failed"
        raise ConnectionError(msg) from e
    finally:
        client.close()


if __name__ == "__main__":
    mcp.run(transport='sse')
