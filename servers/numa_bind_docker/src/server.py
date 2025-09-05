from typing import Union, Dict, Any
import subprocess
import json
from mcp.server import FastMCP
from config.public.base_config_loader import LanguageEnum
from config.private.numa_bind_docker.config_loader import NumaBindDockerConfig

# 初始化 FastMCP 服务
mcp = FastMCP("Numa Bind Docker Tool", host="0.0.0.0", port=NumaBindDockerConfig().get_config().private_config.port)


@mcp.tool(
    name="numa_bind_docker_tool"
    if NumaBindDockerConfig().get_config().public_config.language == LanguageEnum.ZH
    else "numa_bind_docker_tool",
    description=
    '''
    使用 numactl 将指定的 NUMA 绑定参数插入到镜像原有的 ENTRYPOINT / CMD 前面运行
    
    1. 输入参数：
        - image: 镜像名称
        - cpuset_cpus: 允许使用的 CPU 核心范围
        - cpuset_mems: 允许使用的内存节点
        - detach: 是否后台运行容器（默认 False）
    2. 返回值：
        - status: 操作状态（success / error）
        - message: 操作结果信息
        - output: 命令的原始输出（如有）
    '''
    if NumaRebindConfig().get_config().public_config.language == LanguageEnum.ZH
    else 
    '''
    Use numactl to insert the specified NUMA binding parameters before the original ENTRYPOINT / CMD of the image for execution.
    1. Input parameters:
        - image: Image name
        - cpuset_cpus: Range of CPU cores allowed for use
        - cpuset_mems: Memory nodes allowed for use
        - detach: Whether to run the container in the background (default False)
    2. Return values:
        - status: Operation status (success / error)
        - message: Operation result information
        - output: Original output of the command (if any)
    '''
)

def numa_bind_docker_tool(
    image: str,
    cpuset_cpus: str,
    cpuset_mems: str,
    detach: bool = False
) -> Dict[str, Any]:
    try:
        # 获取镜像的默认 CMD 和 ENTRYPOINT
        inspect_cmd = ['docker', 'inspect', '--format', '{{json .Config}}', image]
        inspect_result = subprocess.run(
            inspect_cmd,
            capture_output=True,
            text=True,
            check=True
        )
        config_data = json.loads(inspect_result.stdout)
        entrypoint = config_data.get('Entrypoint', [])
        cmd = config_data.get('Cmd', [])

        final_cmd = entrypoint + cmd
        orig = ' '.join(final_cmd)

        docker_run_cmd = [
            'docker',
            'run'
        ]

        if detach:
            docker_run_cmd.append('--detach')

        docker_run_cmd.extend([
            '--cap-add', 'SYS_NICE',
            '--cpuset-cpus', cpuset_cpus,
            '--cpuset-mems', cpuset_mems,
            '--ulimit', 'memlock=-1',
            image
        ])

        run_result = subprocess.run(
            docker_run_cmd,
            capture_output=True,
            text=True,
            check=True
        )

        return {
            'status': 'success',
            'message': f"Started container with NUMA binding: {cpuset_cpus}/{cpuset_mems} for image '{image}'",
            'output': run_result.stdout
        }

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"执行 Docker 命令失败: {e.stderr}")


if __name__ == "__main__":
    mcp.run(transport='sse')