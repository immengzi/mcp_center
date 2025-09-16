from typing import Dict, Any, Union
import subprocess
import shutil
import paramiko
from mcp.server import FastMCP
from config.public.base_config_loader import LanguageEnum
from config.private.monitor_docker.config_loader import MonitorDockerConfig

mcp = FastMCP(
    "Monitor Docker NUMA Memory Tool",
    host="0.0.0.0",
    port=MonitorDockerConfig().get_config().private_config.port
)


def find_executable(name: str) -> str:
    """在 PATH 中查找可执行文件，找不到抛出异常"""
    path = shutil.which(name)
    if not path:
        raise FileNotFoundError(f"缺少依赖: 找不到 {name}，请确保已安装并在 PATH 中")
    return path


@mcp.tool(
    name="monitor_docker"
    if MonitorDockerConfig().get_config().public_config.language == LanguageEnum.ZH
    else "monitor_docker",
    description=
    '''
    监控指定 Docker 容器的 NUMA 内存访问情况

    1. 输入参数：
        - container_id: 要监控的容器 ID 或名称
        - host: 远程主机地址（可选）
    2. 返回值：
        - status: 操作状态（success / error）
        - message: 操作结果信息
        - output: NUMA 内存访问统计信息（包含每个 NUMA 节点的内存使用情况）
    '''
    if MonitorDockerConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    '''
    Monitor NUMA memory access of a specific Docker container

    1. Input parameters:
        - container_id: Container ID or name to be monitored
        - host: Remote host address (optional)
    2. Return values:
        - status: Operation status (success / error)
        - message: Operation result information
        - output: NUMA memory access statistics (contains memory usage per NUMA node)
    '''
)
def monitor_docker(container_id: str, host: Union[str, None] = None) -> Dict[str, Any]:
    try:
        if host is None:
            # -------- 本地执行 --------
            docker_bin = find_executable("docker")
            numastat_bin = find_executable("numastat")

            # 获取容器主进程 PID
            inspect_cmd = [docker_bin, 'inspect', '--format', '{{.State.Pid}}', container_id]
            inspect_result = subprocess.run(inspect_cmd, capture_output=True, text=True, check=True)
            pid = inspect_result.stdout.strip()

            if not pid.isdigit():
                return {
                    'status': 'error',
                    'message': f"无法获取容器 {container_id} 的 PID: {pid}",
                    'output': ''
                }

            # 获取 NUMA 内存访问统计
            numastat_cmd = [numastat_bin, '-p', pid]
            numastat_result = subprocess.run(numastat_cmd, capture_output=True, text=True, check=True)

            return {
                'status': 'success',
                'message': f"成功获取容器 {container_id} 的 NUMA 内存访问统计（本地）",
                'output': numastat_result.stdout
            }

        else:
            # -------- 远程执行 --------
            config = MonitorDockerConfig().get_config()
            target_host = next(
                (h for h in config.public_config.remote_hosts if h.name == host or h.host == host),
                None
            )
            if not target_host:
                raise RuntimeError(f"未找到主机 {host} 的配置")

            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                if getattr(target_host, "ssh_key_path", None):
                    client.connect(target_host.host, port=target_host.port, username=target_host.username,
                                   key_filename=target_host.ssh_key_path, timeout=10)
                else:
                    client.connect(target_host.host, port=target_host.port, username=target_host.username,
                                   password=target_host.password, timeout=10)

                # 获取容器 PID
                inspect_cmd = f"docker inspect --format '{{{{.State.Pid}}}}' {container_id}"
                stdin, stdout, stderr = client.exec_command(inspect_cmd)
                pid = stdout.read().decode().strip()
                if not pid.isdigit():
                    return {
                        'status': 'error',
                        'message': f"无法获取容器 {container_id} 的 PID: {pid}",
                        'output': stderr.read().decode()
                    }

                # 获取 NUMA 内存访问统计
                numastat_cmd = f"numastat -p {pid}"
                stdin, stdout, stderr = client.exec_command(numastat_cmd)
                exit_code = stdout.channel.recv_exit_status()
                output = stdout.read().decode()
                error = stderr.read().decode()

                status = "success" if exit_code == 0 else "error"
                message = f"成功获取容器 {container_id} 的 NUMA 内存访问统计（远程）" if exit_code == 0 else f"远程命令执行失败: {error}"

                return {
                    'status': status,
                    'message': message,
                    'output': output
                }

            finally:
                client.close()

    except FileNotFoundError as e:
        return {'status': 'error', 'message': str(e), 'output': ''}
    except subprocess.CalledProcessError as e:
        return {'status': 'error', 'message': f"执行命令失败: {e.stderr}", 'output': e.stdout}
    except Exception as e:
        return {'status': 'error', 'message': str(e), 'output': ''}


if __name__ == "__main__":
    mcp.run(transport='sse')
