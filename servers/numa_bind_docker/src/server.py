from typing import Union, Dict, Any
import subprocess
import json
import paramiko
from mcp.server import FastMCP
from config.public.base_config_loader import LanguageEnum
from config.private.numa_bind_docker.config_loader import NumaBindDockerConfig

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
        - host: 远程主机 IP 或名称（可选）
    2. 返回值：
        - status: 操作状态（success / error）
        - message: 操作结果信息
        - output: 命令的原始输出（如有）
    '''
    if NumaBindDockerConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    '''
    Use numactl to insert the specified NUMA binding parameters before the original ENTRYPOINT / CMD of the image for execution.
    1. Input parameters:
        - image: Image name
        - cpuset_cpus: Range of CPU cores allowed for use
        - cpuset_mems: Memory nodes allowed for use
        - detach: Whether to run the container in the background (default False)
        - host: Remote host IP or name (optional)
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
    detach: bool = False,
    host: Union[str, None] = None
) -> Dict[str, Any]:

    def execute_local():
        # 获取镜像默认 CMD 和 ENTRYPOINT
        inspect_cmd = ['docker', 'inspect', '--format', '{{json .Config}}', image]
        inspect_result = subprocess.run(inspect_cmd, capture_output=True, text=True, check=True)
        config_data = json.loads(inspect_result.stdout)
        entrypoint = config_data.get('Entrypoint', []) or []
        cmd = config_data.get('Cmd', []) or []
        final_cmd = entrypoint + cmd

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
        run_result = subprocess.run(docker_run_cmd, capture_output=True, text=True, check=True)
        return {
            'status': 'success',
            'message': f"Started container with NUMA binding: {cpuset_cpus}/{cpuset_mems} for image '{image}'",
            'output': run_result.stdout
        }

    def execute_remote(target_host):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        ssh_username = target_host.username
        ssh_password = getattr(target_host, "password", None)
        ssh_key_file = getattr(target_host, "ssh_key_path", None)
        ssh_port = getattr(target_host, "port", 22)

        try:
            if ssh_key_file:
                client.connect(target_host.host, port=ssh_port, username=ssh_username, key_filename=ssh_key_file, timeout=10)
            else:
                client.connect(target_host.host, port=ssh_port, username=ssh_username, password=ssh_password, timeout=10)

            # 获取镜像默认 CMD 和 ENTRYPOINT
            inspect_cmd = f'docker inspect --format \'{{{{json .Config}}}}\' {image}'
            stdin, stdout, stderr = client.exec_command(inspect_cmd)
            config_data = json.loads(stdout.read().decode('utf-8'))
            entrypoint = config_data.get('Entrypoint', []) or []
            cmd = config_data.get('Cmd', []) or []
            final_cmd = entrypoint + cmd

            docker_run_cmd = f'docker run {"--detach" if detach else ""} --cap-add SYS_NICE --cpuset-cpus {cpuset_cpus} --cpuset-mems {cpuset_mems} --ulimit memlock=-1 {image}'
            stdin, stdout, stderr = client.exec_command(docker_run_cmd)
            stdout_text = stdout.read().decode('utf-8')
            stderr_text = stderr.read().decode('utf-8')
            exit_code = stdout.channel.recv_exit_status()

            status = "success" if exit_code == 0 else "error"
            message = "Started container successfully" if exit_code == 0 else f"Failed with exit code {exit_code}"
            return {
                'status': status,
                'message': message,
                'output': stdout_text + stderr_text
            }
        finally:
            client.close()

    try:
        if host is None:
            return execute_local()
        else:
            config = NumaBindDockerConfig().get_config()
            target_host = next(
                (h for h in config.public_config.remote_hosts if h.name == host or h.host == host),
                None
            )
            if not target_host:
                raise RuntimeError(f"未找到主机 {host} 的配置")
            return execute_remote(target_host)

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Docker 命令执行失败: {e.stderr}")
    except paramiko.AuthenticationException:
        raise RuntimeError("SSH 认证失败，请检查用户名或密钥")
    except paramiko.SSHException as e:
        raise RuntimeError(f"SSH 连接错误: {e}")
    except Exception as e:
        raise RuntimeError(f"运行 NUMA Docker 容器失败: {str(e)}")


if __name__ == "__main__":
    mcp.run(transport='sse')
