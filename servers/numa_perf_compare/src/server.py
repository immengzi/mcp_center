from typing import Union, Dict, Any
import paramiko
import subprocess
import re
from datetime import datetime
from mcp.server import FastMCP
from config.public.base_config_loader import LanguageEnum
from config.private.numa_perf_compare.config_loader import NumaPerfCompareConfig

mcp = FastMCP("NUMA Performance Comparsion MCP Server",
             host="0.0.0.0",
             port=NumaPerfCompareConfig().get_config().private_config.port)


def get_numa_nodes(host: Union[str, None] = None) -> int:
    """获取系统中的NUMA节点数量"""
    if host is None:
        result = subprocess.run(['numactl', '--hardware'],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              text=True)
        if result.returncode != 0:
            raise RuntimeError(f"numactl --hardware failed: {result.stderr}")
        match = re.search(r'available:\s+(\d+)', result.stdout)
        if not match:
            raise RuntimeError("Could not parse NUMA nodes from local output")
        return int(match.group(1))
    else:
        for host_config in NumaPerfCompareConfig().get_config().public_config.remote_hosts:
            if host == host_config.name or host == host_config.host:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(
                    hostname=host_config.host,
                    port=host_config.port,
                    username=host_config.username,
                    password=host_config.password
                )
                stdin, stdout, stderr = ssh.exec_command('numactl --hardware')
                output = stdout.read().decode()
                ssh.close()

                match = re.search(r'available:\s+(\d+)', output)
                if not match:
                    raise RuntimeError("Could not parse NUMA nodes from remote output")
                return int(match.group(1))
        raise ValueError(f"Remote host {host} not found in configuration")


def run_benchmark(benchmark_path: str, 
                  cpu_node: Union[int, str, None] = None, 
                  mem_node: Union[int, str, None] = None, 
                  host: Union[str, None] = None) -> Dict:
    """运行基准测试并返回结果"""
    # 构造 numa 绑定参数
    numa_args = []
    if cpu_node is not None and cpu_node != "all":
        numa_args.append(f'--cpunodebind={cpu_node}')
    if mem_node is not None and mem_node != "all":
        numa_args.append(f'--membind={mem_node}')

    if host is None:
        command = ['numactl'] + numa_args + [benchmark_path] if numa_args else [benchmark_path]
        result = subprocess.run(command,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               text=True)

        metrics = {"raw_output": result.stdout}
        return {
            "command": " ".join(command),
            "output": result.stdout,
            "error": result.stderr,
            "return_code": result.returncode,
            "metrics": metrics
        }
    else:
        for host_config in NumaPerfCompareConfig().get_config().public_config.remote_hosts:
            if host == host_config.name or host == host_config.host:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(
                    hostname=host_config.host,
                    port=host_config.port,
                    username=host_config.username,
                    password=host_config.password
                )

                remote_cmd = (["numactl"] + numa_args + [benchmark_path]) if numa_args else [benchmark_path]
                remote_cmd_str = " ".join(remote_cmd)

                stdin, stdout, stderr = ssh.exec_command(remote_cmd_str)
                output = stdout.read().decode()
                error = stderr.read().decode()
                return_code = stdout.channel.recv_exit_status()

                ssh.close()

                metrics = {"raw_output": output}
                return {
                    "command": remote_cmd_str,
                    "output": output,
                    "error": error,
                    "return_code": return_code,
                    "metrics": metrics
                }
        raise ValueError(f"Remote host {host} not found in configuration")


@mcp.tool(
    name="numa_perf_compare"
    if NumaPerfCompareConfig().get_config().public_config.language == LanguageEnum.ZH
    else "numa_perf_compare",
    description='''
    执行NUMA基准测试，支持不同绑定策略：
    1. 本地绑定：CPU 和内存在同一节点
    2. 跨节点绑定：CPU 和内存在不同节点
    3. 不绑定：使用系统默认行为

    输入参数：
    - benchmark: 基准测试可执行文件路径（如 /root/mcp_center/stream）
    - host: 远程主机名称或IP地址（可选）
    '''
    if NumaPerfCompareConfig().get_config().public_config.language == LanguageEnum.ZH
    else '''
    Run NUMA benchmark tests with different binding strategies:
    1. Local binding: CPU and memory on the same node
    2. Cross-node binding: CPU and memory on different nodes
    3. No binding: Default system behavior

    Parameters:
    - benchmark: Path to the benchmark executable (e.g., /root/mcp_center/stream)
    - host: Remote host name or IP address (optional)
    '''
)
async def numa_perf_compare(benchmark: str, host: Union[str, None] = None) -> Dict[str, Any]:
    """执行NUMA基准测试"""
    try:
        numa_nodes = get_numa_nodes(host)
        first_node = 0
        last_node = numa_nodes - 1

        results = {}

        # 本地绑定测试
        local_result = run_benchmark(benchmark, cpu_node=first_node, mem_node=first_node, host=host)
        results["local_binding"] = {
            "description": f"CPU and memory bound to node {first_node}",
            "result": local_result
        }

        # 跨节点绑定测试
        if numa_nodes > 1:
            cross_result = run_benchmark(benchmark, cpu_node=first_node, mem_node=last_node, host=host)
            results["cross_node_binding"] = {
                "description": f"CPU on node {first_node}, memory on node {last_node}",
                "result": cross_result
            }

        # 不绑定测试
        no_bind_result = run_benchmark(benchmark, cpu_node="all", mem_node="all", host=host)
        results["no_binding"] = {
            "description": "No CPU/memory binding",
            "result": no_bind_result
        }

        return {
            "numa_nodes": numa_nodes,
            "test_results": results,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        return {
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


if __name__ == "__main__":
    mcp.run(transport='sse')
