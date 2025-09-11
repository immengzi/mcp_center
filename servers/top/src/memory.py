"""内存维度实现：专注于内存指标的采集与解析"""
import psutil
from typing import Any, Dict, Union
import paramiko
from base import execute_command
from config.private.top.config_loader import TopCommandConfig
from config.public.base_config_loader import LanguageEnum


def collect_local_memory() -> Dict[str, Any]:
    """采集本地服务器内存指标"""
    # 获取物理内存信息
    mem = psutil.virtual_memory()
    
    # 获取交换分区信息
    swap = psutil.swap_memory()
    
    return {
        "physical": {
            "total_gb": round(mem.total / (1024 **3), 1),
            "used": {
                "gb": round(mem.used / (1024** 3), 1),
                "percent": round(mem.percent, 1)
            },
            "free_gb": round(mem.free / (1024 **3), 1),
            "available_gb": round(mem.available / (1024** 3), 1)
        },
        "swap": {
            "total_gb": round(swap.total / (1024 **3), 1),
            "used": {
                "gb": round(swap.used / (1024** 3), 1),
                "percent": round(swap.percent, 1)
            }
        }
    }


def collect_remote_memory(ssh_conn: paramiko.SSHClient) -> Dict[str, Any]:
    """采集远程服务器内存指标"""
    # 执行命令获取内存信息
    success, output, error = execute_command(ssh_conn, """
        free -b | awk '/Mem/ {print $2, $3, $4, $7}';
        free -b | awk '/Swap/ {print $2, $3}';
    """)
    
    if not success:
        raise RuntimeError(f"内存信息采集失败：{error}")
        
    # 解析命令输出
    lines = [line.strip() for line in output.split('\n') if line.strip()]
    if len(lines) < 2:
        raise RuntimeError(f"内存信息解析失败，输出格式异常：{output}")
    
    # 解析物理内存（转为GB）
    mem_total, mem_used, mem_free, mem_available = map(int, lines[0].split())
    mem_total_gb = round(mem_total / (1024 **3), 1)
    mem_used_gb = round(mem_used / (1024** 3), 1)
    mem_used_percent = round((mem_used / mem_total) * 100, 1) if mem_total > 0 else 0
    
    # 解析交换分区
    swap_total, swap_used = map(int, lines[1].split())
    swap_total_gb = round(swap_total / (1024 **3), 1)
    swap_used_gb = round(swap_used / (1024** 3), 1)
    swap_used_percent = round((swap_used / swap_total) * 100, 1) if swap_total > 0 else 0
    
    return {
        "physical": {
            "total_gb": mem_total_gb,
            "used": {
                "gb": mem_used_gb,
                "percent": mem_used_percent
            },
            "free_gb": round(mem_free / (1024 **3), 1),
            "available_gb": round(mem_available / (1024** 3), 1)
        },
        "swap": {
            "total_gb": swap_total_gb,
            "used": {
                "gb": swap_used_gb,
                "percent": swap_used_percent
            }
        }
    }


def get_memory_metrics(is_local: bool, ssh_conn: Union[paramiko.SSHClient, None]) -> Dict[str, Any]:
    """统一入口：根据服务器类型获取内存指标"""
    if is_local:
        return {"memory": collect_local_memory()}
    else:
        if not ssh_conn:
            raise RuntimeError("远程磁盘采集需要SSH连接"if TopCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    else "Remote disk collection requires an SSH connection")
        return {"memory": collect_remote_memory(ssh_conn)}
    