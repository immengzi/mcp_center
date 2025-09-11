"""CPU维度实现：专注于CPU指标的采集与解析"""
from asyncio.log import logger
import psutil
from typing import Any, Dict, Union
import paramiko
from config.private.top.config_loader import TopCommandConfig
from config.public.base_config_loader import LanguageEnum
from servers.top.src.base import execute_command

def collect_local_cpu() -> Dict[str, Any]:
    """采集本地服务器CPU指标"""
    # 获取CPU使用率（间隔0.5秒确保准确性）
    cpu_percent = psutil.cpu_percent(interval=0.5)
    
    # 获取CPU核心数
    cores = psutil.cpu_count(logical=False) or 0
    
    # 获取负载均值
    load_1m, load_5m, load_15m = psutil.getloadavg()
    
    # 获取详细使用率分布
    cpu_times = psutil.cpu_times_percent(interval=0.5)
    
    return {
        "usage": {
            "total": round(cpu_percent, 1),
            "user": round(cpu_times.user, 1),
            "system": round(cpu_times.system, 1),
            "idle": round(cpu_times.idle, 1)
        },
        "load": {
            "1m": round(load_1m, 2),
            "5m": round(load_5m, 2),
            "15m": round(load_15m, 2)
        },
        "cores": cores
    }


def collect_remote_cpu(ssh_conn: paramiko.SSHClient) -> Dict[str, Any]:
    """采集远程服务器CPU指标"""
    # 执行命令获取CPU信息（兼容主流Linux发行版）
    success, output, error = execute_command(ssh_conn, """
        top -bn1 | grep 'Cpu(s)' | awk '{print $2, $4, $8}';
        uptime | awk -F'load average: ' '{print $2}';
        nproc --all
    """)
    
    if not success:
        raise RuntimeError(f"CPU信息采集失败：{error}")
        
    # 解析命令输出
    lines = [line.strip() for line in output.split('\n') if line.strip()]
    
    if len(lines) < 3:
        raise RuntimeError(f"CPU信息解析失败，输出格式异常：{output}" if TopCommandConfig().get_config(
                        ).public_config.language == LanguageEnum.ZH else f"Failed to parse CPU information, unexpected output format: {output}")
    
    # 解析CPU使用率
    
    user, system, idle = map(float, lines[0].split(' '))
    
    total_usage = 100 - idle  # 总使用率 = 100% - 空闲率
    
    # 解析负载均值
    
    load_avg = lines[1].split(',')
    load_1m, load_5m, load_15m = map(float, load_avg)
    
    # 解析核心数
    
    cores = int(lines[2])
    
    return {
        "usage": {
            "total": round(total_usage, 1),
            "user": round(user, 1),
            "system": round(system, 1),
            "idle": round(idle, 1)
        },
        "load": {
            "1m": round(load_1m, 2),
            "5m": round(load_5m, 2),
            "15m": round(load_15m, 2)
        },
        "cores": cores
    }


def get_cpu_metrics(is_local: bool, ssh_conn: Union[paramiko.SSHClient, None]) -> Dict[str, Any]:
    """统一入口：根据服务器类型获取CPU指标"""
    if is_local:
        logger.info("info-------localhost")
        return {"cpu": collect_local_cpu()}
    else:
        if not ssh_conn:
            raise RuntimeError("远程CPU采集需要SSH连接" if TopCommandConfig().get_config(
                        ).public_config.language == LanguageEnum.ZH else "Remote CPU collection requires SSH connection")
        return {"cpu": collect_remote_cpu(ssh_conn)}
    