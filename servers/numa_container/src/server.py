import shutil
import subprocess
from typing import Any, Dict, Optional

import paramiko
from mcp.server import FastMCP

from config.private.numa_container.config_loader import NumaContainerConfig
from config.public.base_config_loader import LanguageEnum

# 初始化配置
config = NumaContainerConfig()

mcp = FastMCP(
    "Monitor Docker NUMA Memory Tool",
    host="0.0.0.0",
    port=config.get_config().private_config.port
)


@mcp.tool(
    name="numa_container"
    if config.get_config().public_config.language == LanguageEnum.ZH
    else "numa_container",
    description="""
    监控指定 Docker 容器的 NUMA 内存访问情况。
    参数：
        container_id: 要监控的容器 ID 或名称。
        host: 可选，远程主机名称（使用public_config.toml中配置的name字段）；留空则监控本机。
    返回：
        dict {
            "status": str,          # success / error
            "message": str,         # 操作结果信息
            "output": str           # NUMA 内存访问统计信息
        }
    """
    if config.get_config().public_config.language == LanguageEnum.ZH
    else """
    Monitor NUMA memory access of a specific Docker container.
    Args:
        container_id: Container ID or name to be monitored.
        host: Optional remote host name (configured in public_config.toml); monitors local host if omitted.
    Returns:
        dict {
            "status": str,          # success / error
            "message": str,         # Operation result information
            "output": str           # NUMA memory access statistics
        }
    """
)
def numa_container(container_id: str, host: Optional[str] = None) -> Dict[str, Any]:
    """
    监控 Docker 容器的 NUMA 内存访问
    
    Args:
        container_id: 容器 ID 或名称
        host: 远程主机名称（public_config.toml 中的 name），None 表示本机
        
    Returns:
        包含监控结果的字典
    """
    cfg = config.get_config()
    is_zh = cfg.public_config.language == LanguageEnum.ZH
    
    try:
        # 本地执行
        if not host or host.strip().lower() in ("", "localhost"):
            return _monitor_local_container(container_id, is_zh)
        
        # 远程执行
        return _monitor_remote_container(container_id, host.strip(), cfg, is_zh)
    except Exception as e:
        msg = f"监控失败: {str(e)}" if is_zh else f"Monitoring failed: {str(e)}"
        return {
            'status': 'error',
            'message': msg,
            'output': ''
        }


def _monitor_local_container(container_id: str, is_zh: bool) -> Dict[str, Any]:
    """监控本地 Docker 容器（选择 RSS 最大的业务进程）"""
    try:
        docker_bin = _find_executable("docker", is_zh)
        numastat_bin = _find_executable("numastat", is_zh)

        # 1. 获取容器 init PID（宿主机视角）
        inspect_cmd = [docker_bin, "inspect", "--format", "{{.State.Pid}}", container_id]
        inspect_result = subprocess.run(inspect_cmd, capture_output=True, text=True, check=True)
        init_pid = inspect_result.stdout.strip()

        if not init_pid.isdigit():
            msg = f"无法获取容器 {container_id} 的 PID: {init_pid}" if is_zh \
                else f"Failed to get PID for container {container_id}: {init_pid}"
            return {"status": "error", "message": msg, "output": ""}

        # 2. 查找该容器下 RSS 最大的子进程（排除 PID 1）
        # ps: pid,ppid,rss,comm
        ps_cmd = [
            "ps", "-e", "-o", "pid=,ppid=,rss=,comm="
        ]
        ps_result = subprocess.run(ps_cmd, capture_output=True, text=True, check=True)

        candidates = []
        for line in ps_result.stdout.splitlines():
            pid, ppid, rss, comm = line.split(maxsplit=3)
            if ppid == init_pid and pid != init_pid:
                candidates.append((int(rss), pid, comm))

        if not candidates:
            msg = f"容器 {container_id} 中未找到可监控的业务进程" if is_zh \
                else f"No workload process found in container {container_id}"
            return {"status": "error", "message": msg, "output": ""}

        # 3. 选择 RSS 最大的进程
        candidates.sort(reverse=True)
        rss_kb, target_pid, target_comm = candidates[0]

        # 4. 执行 numastat
        numastat_cmd = [numastat_bin, "-p", target_pid]
        numastat_result = subprocess.run(
            numastat_cmd, capture_output=True, text=True, check=True
        )

        msg = (
            f"成功获取容器 {container_id} 的 NUMA 内存访问统计（进程 {target_comm}, PID {target_pid}）"
            if is_zh
            else f"Successfully retrieved NUMA stats for container {container_id} "
                 f"(process {target_comm}, PID {target_pid})"
        )

        return {
            "status": "success",
            "message": msg,
            "output": numastat_result.stdout,
        }

    except subprocess.CalledProcessError as e:
        msg = f"命令执行失败: {e.stderr}" if is_zh else f"Command failed: {e.stderr}"
        raise RuntimeError(msg) from e


def _monitor_remote_container(container_id: str, host_name: str, cfg, is_zh: bool) -> Dict[str, Any]:
    """监控远程 Docker 容器"""
    target_host = _find_remote_host(host_name, cfg.public_config.remote_hosts, is_zh)
    
    try:
        output = _execute_remote_monitoring(container_id, target_host, is_zh)
        msg = f"成功获取容器 {container_id} 的 NUMA 内存访问统计（远程）" if is_zh else f"Successfully retrieved NUMA stats for container {container_id} (remote)"
        return {
            'status': 'success',
            'message': msg,
            'output': output
        }
    except Exception as e:
        msg = f"远程监控失败: {str(e)}" if is_zh else f"Remote monitoring failed: {str(e)}"
        raise RuntimeError(msg) from e


def _find_executable(name: str, is_zh: bool) -> str:
    """在 PATH 中查找可执行文件"""
    path = shutil.which(name)
    if not path:
        msg = f"缺少依赖: 找不到 {name}，请确保已安装并在 PATH 中" if is_zh else f"Missing dependency: {name} not found in PATH"
        raise FileNotFoundError(msg)
    return path


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


def _execute_remote_monitoring(container_id: str, host_config, is_zh: bool) -> str:
    """在远程主机执行监控"""
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
        
        # 获取容器 PID
        inspect_cmd = f"docker inspect --format '{{{{.State.Pid}}}}' {container_id}"
        stdin, stdout, stderr = client.exec_command(inspect_cmd)
        stdin.close()
        
        pid = stdout.read().decode('utf-8').strip()
        err = stderr.read().decode('utf-8').strip()
        
        if err or not pid.isdigit():
            raise RuntimeError(f"Failed to get container PID: {err or pid}")
        
        # 获取 NUMA 统计
        numastat_cmd = f"numastat -p {pid}"
        stdin, stdout, stderr = client.exec_command(numastat_cmd)
        stdin.close()
        
        output = stdout.read().decode('utf-8')
        err = stderr.read().decode('utf-8').strip()
        
        if err:
            raise RuntimeError(f"numastat failed: {err}")
        
        return output
    except paramiko.AuthenticationException as e:
        msg = "SSH认证失败" if is_zh else "SSH auth failed"
        raise ConnectionError(msg) from e
    finally:
        client.close()


if __name__ == "__main__":
    mcp.run(transport='sse')
