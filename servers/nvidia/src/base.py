import subprocess
import re
import logging
from typing import Optional, Dict, List, Any
import paramiko  # 用于远程SSH连接
from paramiko.ssh_exception import SSHException

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


import subprocess
import re
import logging
from typing import Optional, Dict, List, Any
import paramiko
from paramiko.ssh_exception import SSHException

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _parse_nvidia_smi_output(raw_output: str, include_processes: bool, language: str) -> List[Dict[str, Any]]:
    """
    解析nvidia-smi的CSV格式输出，提取GPU核心信息
    Parse CSV-formatted nvidia-smi output to extract core GPU information
    """
    gpu_info = []
    lines = [line.strip() for line in raw_output.splitlines() if line.strip()]
    if not lines:
        return gpu_info  # 无数据直接返回空列表

    # 分离GPU信息和进程信息（如果包含）
    # 进程信息行通常包含"pid"相关字段，通过关键词区分
    gpu_lines = []
    process_lines = []
    for line in lines:
        if include_processes and "pid" in line.lower():
            process_lines.append(line)
        else:
            gpu_lines.append(line)

    # 解析GPU信息（CSV格式：index,name,utilization.gpu,utilization.memory,temperature.gpu,memory.used,memory.total）
    for line in gpu_lines:
        # 按逗号分割CSV字段（处理可能的空格）
        parts = [p.strip() for p in line.split(',')]
        # 校验字段数量是否正确（7个字段）
        if len(parts) != 7:
            continue  # 格式异常跳过

        try:
            idx = int(parts[0])
            name = parts[1]
            gpu_util = int(parts[2])
            mem_util = int(parts[3])
            temp = int(parts[4])
            mem_used = int(parts[5])
            mem_total = int(parts[6])
            mem_free = mem_total - mem_used

            gpu_data = {
                "index": idx,
                "name": name,
                "utilization_gpu": gpu_util,
                "utilization_memory": mem_util,
                "temperature": temp,
                "memory_total": mem_total,
                "memory_used": mem_used,
                "memory_free": mem_free,
                "processes": []  # 先初始化空进程列表
            }
            gpu_info.append(gpu_data)
        except (ValueError, IndexError):
            # 处理数字转换失败或字段索引异常
            error_msg = f"解析GPU信息失败，行内容: {line}" if language == "zh" else f"Failed to parse GPU info, line: {line}"
            logger.warning(error_msg)
            continue

    # 解析进程信息（如果需要，CSV格式：pid,gpu_index,name,used_memory）
    if include_processes and process_lines:
        processes: Dict[int, List[Dict]] = {}  # 按GPU索引分组
        for line in process_lines:
            parts = [p.strip() for p in line.split(',')]
            # 校验进程字段数量（4个字段）
            if len(parts) != 4:
                continue

            try:
                pid = int(parts[0])
                gpu_idx = int(parts[1])
                proc_name = parts[2]
                mem_used = int(parts[3])
                if gpu_idx not in processes:
                    processes[gpu_idx] = []
                processes[gpu_idx].append({
                    "pid": pid,
                    "name": proc_name,
                    "memory_used": mem_used
                })
            except (ValueError, IndexError):
                error_msg = f"解析进程信息失败，行内容: {line}" if language == "zh" else f"Failed to parse process info, line: {line}"
                logger.warning(error_msg)
                continue

        # 将进程信息关联到对应的GPU
        for gpu in gpu_info:
            gpu_idx = gpu["index"]
            if gpu_idx in processes:
                gpu["processes"] = processes[gpu_idx]

    return gpu_info


def _get_local_gpu_status(gpu_index: Optional[int], include_processes: bool, language: str) -> str:
    """
    获取本地GPU状态，执行nvidia-smi命令
    Get local GPU status by executing nvidia-smi command
    
    Args:
        gpu_index: 特定GPU索引（可选） / Specific GPU index (optional)
        include_processes: 是否包含进程信息 / Whether to include process information
        language: 语言标识（zh/en） / Language identifier (zh/en)
    
    Returns:
        命令输出结果 / Command output result
    
    Raises:
        RuntimeError: 命令执行失败时抛出 / Raised when command execution fails
    """
    # 构建nvidia-smi命令
    # Build nvidia-smi command
    base_cmd = "nvidia-smi --query-gpu=index,name,utilization.gpu,utilization.memory,temperature.gpu,memory.used,memory.total --format=csv,noheader,nounits"
    
    if gpu_index is not None:
        base_cmd += f" --id={gpu_index}"
    
    if include_processes:
        base_cmd += " && nvidia-smi --query-compute-apps=pid,gpu_name,name,used_memory --format=csv,noheader,nounits"
    
    try:
        result = subprocess.run(
            base_cmd,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8"
        )
        logger.info(result.stdout)
        return result.stdout
    except subprocess.CalledProcessError as e:
        error_msg = "本地nvidia-smi执行失败: {e.stderr}" if language == "zh" else f"Local nvidia-smi execution failed: {e.stderr}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)


def _get_remote_gpu_status(
    host: str,
    username: str,
    password: str,
    port: int,
    gpu_index: Optional[int],
    include_processes: bool,
    language: str
) -> str:
    """
    通过SSH获取远程GPU状态
    Get remote GPU status via SSH
    
    Args:
        host: 远程主机地址 / Remote host address
        username: SSH用户名 / SSH username
        password: SSH密码 / SSH password
        port: SSH端口 / SSH port
        gpu_index: 特定GPU索引（可选） / Specific GPU index (optional)
        include_processes: 是否包含进程信息 / Whether to include process information
        language: 语言标识（zh/en） / Language identifier (zh/en)
    
    Returns:
        命令输出结果 / Command output result
    
    Raises:
        RuntimeError: 连接失败或命令执行失败时抛出 / Raised when connection or command execution fails
    """
    base_cmd = "nvidia-smi --query-gpu=index,name,utilization.gpu,utilization.memory,temperature.gpu,memory.used,memory.total --format=csv,noheader,nounits"
    
    if gpu_index is not None:
        base_cmd += f" --id={gpu_index}"
    
    if include_processes:
        base_cmd += " && nvidia-smi --query-compute-apps=pid,gpu_name,name,used_memory --format=csv,noheader,nounits"
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(
            hostname=host,
            port=port,
            username=username,
            password=password,
            timeout=10
        )
        
        stdin, stdout, stderr = ssh.exec_command(base_cmd)
        exit_status = stdout.channel.recv_exit_status()
        stderr_output = stderr.read().decode("utf-8")
        
        if exit_status != 0:
            error_msg = f"远程nvidia-smi执行失败: {stderr_output}" if language == "zh" else f"Remote nvidia-smi execution failed: {stderr_output}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        return stdout.read().decode("utf-8")
    
    except SSHException as e:
        error_msg = f"SSH连接失败: {str(e)}" if language == "zh" else f"SSH connection failed: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    finally:
        ssh.close()


def _format_gpu_info(raw_info: str, host: str, include_processes: bool, language: str) -> Dict[str, Any]:
    """
    格式化GPU信息为标准字典结构
    Format GPU information into standard dictionary structure
    
    Args:
        raw_info: 原始命令输出 / Raw command output
        host: 主机地址 / Host address
        include_processes: 是否包含进程信息 / Whether to include process information
        language: 语言标识（zh/en） / Language identifier (zh/en)
    
    Returns:
        格式化的GPU状态信息 / Formatted GPU status information
    """
    gpus = _parse_nvidia_smi_output(raw_info, include_processes, language)
    if not gpus:
        if language == "zh":
            message = "未检测到可用的NVIDIA GPU设备"
        else:
            message = "No available NVIDIA GPU devices detected"
        logger.warning(message)
    else:
        logger.info(f"检测到 {len(gpus)} 个GPU设备" if language == "zh" else f"Detected {len(gpus)} GPU devices")
    return {
        "host": host,
        "gpus": gpus
    }


#原生nvidia-smi表格输出

def _run_local_nvidia_smi(language: str) -> str:
    """
    在本地执行nvidia-smi命令，返回原始表格输出
    Execute local nvidia-smi command and return raw table output
    """
    try:
        # 执行原生nvidia-smi（默认输出表格格式）
        result = subprocess.run(
            "nvidia-smi",
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8"
        )
        logger.info(result.stdout)
        return result.stdout
    except subprocess.CalledProcessError as e:
        error_msg = f"本地nvidia-smi执行失败: {e.stderr}" if language == "zh" else f"Local nvidia-smi execution failed: {e.stderr}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)


def _run_remote_nvidia_smi(host: str, username: str, password: str, port: int, language: str) -> str:
    """
    通过SSH在远程执行nvidia-smi命令，返回原始表格输出
    Execute remote nvidia-smi via SSH and return raw table output
    """
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(
            hostname=host,
            port=port,
            username=username,
            password=password,
            timeout=10
        )
        
        # 执行原生nvidia-smi（默认输出表格格式）
        stdin, stdout, stderr = ssh.exec_command("nvidia-smi")
        exit_status = stdout.channel.recv_exit_status()
        stderr_output = stderr.read().decode("utf-8")
        
        if exit_status != 0:
            error_msg = f"远程nvidia-smi执行失败: {stderr_output}" if language == "zh" else f"Remote nvidia-smi execution failed: {stderr_output}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        return stdout.read().decode("utf-8")
    
    except SSHException as e:
        error_msg = f"SSH连接失败: {str(e)}" if language == "zh" else f"SSH connection failed: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    finally:
        ssh.close()