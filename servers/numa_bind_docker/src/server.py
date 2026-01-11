import json
import subprocess
from typing import Any, Dict, Optional

import paramiko
from mcp.server import FastMCP

from config.private.numa_bind_docker.config_loader import NumaBindDockerConfig
from config.public.base_config_loader import LanguageEnum

# 初始化配置
config = NumaBindDockerConfig()

mcp = FastMCP(
    "Numa Bind Docker Tool",
    host="0.0.0.0",
    port=config.get_config().private_config.port
)


@mcp.tool(
    name="numa_bind_docker_tool"
    if config.get_config().public_config.language == LanguageEnum.ZH
    else "numa_bind_docker_tool",
    description="""
    使用 numactl 将指定的 NUMA 绑定参数插入到镜像原有的 ENTRYPOINT / CMD 前面运行。
    参数：
        image: 镜像名称
        cpuset_cpus: 允许使用的 CPU 核心范围
        cpuset_mems: 允许使用的内存节点
        detach: 是否后台运行容器（默认 False）
        host: 可选，远程主机名称（使用public_config.toml中配置的name字段）；留空则本机执行。
    返回：
        dict {
            "status": str,       # 操作状态（success / error）
            "message": str,      # 操作结果信息
            "output": str,       # 命令的原始输出（如有）
            "host": str          # 主机标识（本机为"localhost"）
        }
    """
    if config.get_config().public_config.language == LanguageEnum.ZH
    else """
    Use numactl to insert the specified NUMA binding parameters before the original ENTRYPOINT / CMD of the image for execution.
    Args:
        image: Image name
        cpuset_cpus: Range of CPU cores allowed for use
        cpuset_mems: Memory nodes allowed for use
        detach: Whether to run the container in the background (default False)
        host: Optional remote host name (configured in public_config.toml); executes locally if omitted.
    Returns:
        dict {
            "status": str,       # Operation status (success / error)
            "message": str,      # Operation result information
            "output": str,       # Original output of the command (if any)
            "host": str          # Host identifier ("localhost" for local)
        }
    """
)
def numa_bind_docker_tool(
    image: str,
    cpuset_cpus: str,
    cpuset_mems: str,
    detach: bool = False,
    host: Optional[str] = None
) -> Dict[str, Any]:
    """
    使用 Docker 配合 NUMA 绑定启动容器
    
    Args:
        image: Docker 镜像名称
        cpuset_cpus: CPU 核心范围
        cpuset_mems: 内存节点范围
        detach: 是否后台运行
        host: 远程主机名称（public_config.toml 中的 name），None 表示本机
        
    Returns:
        包含执行结果的字典
    """
    cfg = config.get_config()
    is_zh = cfg.public_config.language == LanguageEnum.ZH
    
    # 本地执行
    if not host or host.strip().lower() in ("", "localhost"):
        return _execute_local_docker(image, cpuset_cpus, cpuset_mems, detach, is_zh)
    
    # 远程执行
    return _execute_remote_docker_workflow(
        host.strip(), image, cpuset_cpus, cpuset_mems, detach, cfg, is_zh
    )


def _execute_local_docker(
    image: str, cpuset_cpus: str, cpuset_mems: str, detach: bool, is_zh: bool
) -> Dict[str, Any]:
    """执行本地 Docker 命令"""
    try:
        # 构建 docker run 命令
        docker_run_cmd = ['docker', 'run']
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
            'output': run_result.stdout,
            'host': 'localhost'
        }
    except subprocess.CalledProcessError as e:
        msg = f"Docker 命令执行失败: {e.stderr}" if is_zh else f"Docker command failed: {e.stderr}"
        raise RuntimeError(msg) from e


def _execute_remote_docker_workflow(
    host_name: str, image: str, cpuset_cpus: str, cpuset_mems: str,
    detach: bool, cfg, is_zh: bool
) -> Dict[str, Any]:
    """远程执行工作流"""
    target_host = _find_remote_host(host_name, cfg.public_config.remote_hosts, is_zh)
    
    try:
        result = _execute_remote_docker(
            target_host, image, cpuset_cpus, cpuset_mems, detach, is_zh
        )
        result["host"] = target_host.name
        return result
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


def _execute_remote_docker(
    host_config, image: str, cpuset_cpus: str, cpuset_mems: str,
    detach: bool, is_zh: bool
) -> Dict[str, Any]:
    """在远程主机执行 Docker 命令"""
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
        
        # 构建远程命令
        docker_run_cmd = (
            f"docker run {'--detach' if detach else ''} "
            f"--cap-add SYS_NICE "
            f"--cpuset-cpus {cpuset_cpus} "
            f"--cpuset-mems {cpuset_mems} "
            f"--ulimit memlock=-1 {image}"
        )
        
        stdin, stdout, stderr = client.exec_command(docker_run_cmd)
        stdin.close()
        
        stdout_text = stdout.read().decode('utf-8')
        stderr_text = stderr.read().decode('utf-8')
        exit_code = stdout.channel.recv_exit_status()
        
        status = "success" if exit_code == 0 else "error"
        message = (
            "Started container successfully" if exit_code == 0
            else f"Failed with exit code {exit_code}"
        )
        
        return {
            'status': status,
            'message': message,
            'output': stdout_text + stderr_text
        }
    except paramiko.AuthenticationException as e:
        msg = "SSH认证失败" if is_zh else "SSH auth failed"
        raise ConnectionError(msg) from e
    finally:
        client.close()


if __name__ == "__main__":
    mcp.run(transport='sse')
