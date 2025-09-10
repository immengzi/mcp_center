from typing import Union, List, Dict, Any
import platform
import os
import paramiko
import subprocess
import re
from datetime import datetime
from mcp.server import FastMCP
from config.private.numa_benchmark.config_loader import NumaBenchmarkConfig

mcp = FastMCP("NUMA Benchmark MCP Server", 
             host="0.0.0.0", 
             port=NumaBenchmarkConfig().get_config().private_config.port)

def get_numa_nodes(host: Union[str, None] = None) -> int:
    """获取系统中的NUMA节点数量"""
    if host is None:
        # 本地执行
        result = subprocess.run(['numactl', '--hardware'], 
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              text=True)
        if result.returncode != 0:
            raise RuntimeError("numactl --hardware execution failed")
        match = re.search(r'available:\s+(\d+)', result.stdout)
        if not match:
            raise RuntimeError("Could not parse NUMA nodes from output")
        return int(match.group(1))
    else:
        # 远程执行
        for host_config in NumaBenchmarkConfig().get_config().public_config.remote_hosts:
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

def run_benchmark(benchmark_path: str, numa_node: Union[int, str, tuple] = "all", host: Union[str, None] = None) -> Dict:
    """运行基准测试并返回结果"""
    # 处理numa_node参数，支持单个节点、多个节点或"all"
    if isinstance(numa_node, tuple):
        numa_node_str = ",".join(str(node) for node in numa_node)
    else:
        numa_node_str = str(numa_node)
    
    if host is None:
        # 本地执行
        command = ['numactl', f'--cpunodebind={numa_node_str}', f'--membind={numa_node_str}', benchmark_path]
        result = subprocess.run(command,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               text=True)
        
        # 解析结果
        metrics = {"raw_output": result.stdout}
        return {
            "command": " ".join(command),
            "output": result.stdout,
            "error": result.stderr,
            "return_code": result.returncode,
            "metrics": metrics
        }
    else:
        # 远程执行
        for host_config in NumaBenchmarkConfig().get_config().public_config.remote_hosts:
            if host == host_config.name or host == host_config.host:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(
                    hostname=host_config.host,
                    port=host_config.port,
                    username=host_config.username,
                    password=host_config.password
                )
                
                # 构造远程执行命令
                remote_cmd = f'numactl --cpunodebind={numa_node_str} --membind={numa_node_str} {benchmark_path}'
                stdin, stdout, stderr = ssh.exec_command(remote_cmd)
                
                output = stdout.read().decode()
                error = stderr.read().decode()
                return_code = stdout.channel.recv_exit_status()
                
                ssh.close()
                
                # 解析结果
                metrics = {"raw_output": output}
                return {
                    "command": remote_cmd,
                    "output": output,
                    "error": error,
                    "return_code": return_code,
                    "metrics": metrics
                }
        raise ValueError(f"Remote host {host} not found in configuration")

@mcp.tool(
    name="numa_benchmark",
    description='''Run NUMA benchmark tests with different binding strategies.
    1. Local binding: CPU and memory on the same node
    2. Cross-node binding: CPU and memory on different nodes
    3. No binding: Default system behavior
    
    Parameters:
    - benchmark: Path to the benchmark executable (e.g., /root/mcp_center/stream)
    - host: Remote host name or IP address (optional)
    '''
)
async def numa_benchmark(benchmark: str, host: Union[str, None] = None) -> Dict[str, Any]:
    """执行NUMA基准测试"""
    try:
        numa_nodes = get_numa_nodes(host)
        first_node = 0
        last_node = numa_nodes - 1
        
        # 执行不同测试场景
        results = {}
        
        # 本地绑定测试
        local_result = run_benchmark(benchmark, first_node, host)
        results["local_binding"] = {
            "description": f"CPU and memory bound to node {first_node}",
            "result": local_result
        }
        
        # 跨节点绑定测试
        cross_result = run_benchmark(benchmark, (first_node, last_node), host)
        results["cross_node_binding"] = {
            "description": f"CPU on node {first_node}, memory on node {last_node}",
            "result": cross_result
        }
        
        # 不绑定测试
        no_bind_result = run_benchmark(benchmark, "all", host)
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
    # 启动MCP服务
    mcp.run(transport='sse')