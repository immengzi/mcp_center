from typing import Dict, Any
import subprocess
import json
from mcp.server import FastMCP
from config.public.base_config_loader import LanguageEnum
from config.private.numa_container.config_loader import NumaContainerConfig

# 初始化 FastMCP 服务
mcp = FastMCP(
    "Monitor Docker NUMA Memory Tool",
    host="0.0.0.0",
    port=NumaContainerConfig().get_config().private_config.port
)


@mcp.tool(
    name="numa_container"
    if NumaContainerConfig().get_config().public_config.language == LanguageEnum.ZH
    else "numa_container",
    description=
    '''
    监控指定 Docker 容器的 NUMA 内存访问情况
    
    1. 输入参数：
        - container_id: 要监控的容器 ID 或名称
    2. 返回值：
        - status: 操作状态（success / error）
        - message: 操作结果信息
        - output: NUMA 内存访问统计信息（包含每个 NUMA 节点的内存使用情况）
    '''
    if NumaContainerConfig().get_config().public_config.language == LanguageEnum.ZH
    else 
    '''
    Monitor NUMA memory access of a specific Docker container
    
    1. Input parameters:
        - container_id: Container ID or name to be monitored
    2. Return values:
        - status: Operation status (success / error)
        - message: Operation result information
        - output: NUMA memory access statistics (contains memory usage per NUMA node)
    '''
)
def numa_container(container_id: str) -> Dict[str, Any]:
    try:
        # 获取容器主进程的 PID
        inspect_cmd = ['docker', 'inspect', '--format', '{{.State.Pid}}', container_id]
        inspect_result = subprocess.run(
            inspect_cmd,
            capture_output=True,
            text=True,
            check=True
        )
        pid = inspect_result.stdout.strip()
        
        if not pid.isdigit():
            return {
                'status': 'error',
                'message': f"无法获取容器 {container_id} 的 PID: {pid}",
                'output': ''
            }
            
        # 使用 numastat 获取 NUMA 内存访问统计
        numastat_cmd = ['numastat', '-p', pid]
        numastat_result = subprocess.run(
            numastat_cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        return {
            'status': 'success',
            'message': f"成功获取容器 {container_id} 的 NUMA 内存访问统计",
            'output': numastat_result.stdout
        }

    except subprocess.CalledProcessError as e:
        return {
            'status': 'error',
            'message': f"执行监控命令失败: {e.stderr}",
            'output': e.stdout
        }


if __name__ == "__main__":
    mcp.run(transport='sse')