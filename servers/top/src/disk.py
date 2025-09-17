"""磁盘维度实现：专注于磁盘指标的采集与解析"""
import psutil
from typing import Any, Dict, Union, List
import paramiko
from base import execute_command
from config.private.top.config_loader import TopCommandConfig
from config.public.base_config_loader import LanguageEnum


def collect_local_disk() -> Dict[str, Any]:
    """采集本地服务器磁盘指标"""
    # 获取磁盘分区信息（排除虚拟文件系统）
    partitions = []
    for part in psutil.disk_partitions(all=False):
        if part.fstype:  # 只处理有文件系统的分区
            try:
                usage = psutil.disk_usage(part.mountpoint)
                partitions.append({
                    "device": part.device,
                    "mount_point": part.mountpoint,
                    "fstype": part.fstype,
                    "total_gb": round(usage.total / (1024 **3), 1),
                    "used": {
                        "gb": round(usage.used / (1024** 3), 1),
                        "percent": round(usage.percent, 1)
                    }
                })
            except PermissionError:
                continue  # 跳过无权限访问的分区
    
    # 获取磁盘IO信息
    disk_io = psutil.disk_io_counters()
    if disk_io is not None:
        return {
            "partitions": partitions,
            "io": {
                "read_mb_s": round(disk_io.read_bytes / (1024 **2), 1),
                "write_mb_s": round(disk_io.write_bytes / (1024** 2), 1),
                "read_count": disk_io.read_count,
                "write_count": disk_io.write_count
            }
        }
    else:
        raise ValueError("无法获取全局磁盘统计信息，psutil返回空值"if TopCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    else "Failed to obtain global disk statistics, psutil returns a null value")

def collect_remote_disk(ssh_conn: paramiko.SSHClient) -> Dict[str, Any]:
    """采集远程服务器磁盘指标"""
    # 1. 获取磁盘分区信息
    success, partitions_output, error = execute_command(
        ssh_conn, "df -P -B 1 | awk 'NR>1 {print $1, $2, $3, $5, $6}'"
    )
    if not success:
        raise RuntimeError(f"磁盘分区信息采集失败：{error}")
    
    partitions = []
    for line in partitions_output.split('\n'):
        if not line.strip():
            continue
        parts = line.strip().split()
        if len(parts) != 5:
            continue
            
        device, total, used, used_percent, mount_point = parts
        partitions.append({
            "device": device,
            "mount_point": mount_point,
            "total_gb": round(int(total) / (1024 **3), 1),
            "used": {
                "gb": round(int(used) / (1024** 3), 1),
                "percent": float(used_percent.strip('%'))
            }
        })
    
    # 2. 获取磁盘IO信息
    success, io_output, error = execute_command(
        ssh_conn, "iostat -k | awk 'NR==4 {print $1, $2, $3, $4}'"
    )
    if not success:
        raise RuntimeError(f"磁盘IO信息采集失败：{error}"if TopCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    else "Failed to collect disk IO information: {error}")
    
    io_data = io_output.strip().split()
    if len(io_data) < 4:
        raise RuntimeError(f"磁盘IO解析失败：{io_output}"if TopCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    else "Failed to parse disk IO: {io_output}")
    
    return {
        "partitions": partitions,
        "io": {
            "read_mb_s": round(float(io_data[2]) / 1024, 1),  # 转换为MB/s
            "write_mb_s": round(float(io_data[3]) / 1024, 1),
            "read_count": round(float(io_data[0])),  # 四舍五入
            "write_count": round(float(io_data[1]))   # 四舍五入
        }
    }


def get_disk_metrics(is_local: bool, ssh_conn: Union[paramiko.SSHClient, None]) -> Dict[str, Any]:
    """统一入口：根据服务器类型获取磁盘指标"""
    if is_local:
        return {"disk": collect_local_disk()}
    else:
        if not ssh_conn:
            raise RuntimeError("远程磁盘采集需要SSH连接"if TopCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    else "Remote disk collection requires an SSH connection")
        return {"disk": collect_remote_disk(ssh_conn)}
    