"""进程维度实现：专注于进程指标的采集与解析"""
import psutil
from typing import Any, Dict, List, Union
import paramiko
from base import execute_command
from datetime import datetime

from config.private.top.config_loader import TopCommandConfig
from config.public.base_config_loader import LanguageEnum

def collect_local_processes(top_n: int = 5) -> List[Dict[str, Any]]:
    """采集本地服务器Top进程信息"""
    processes = []
    
    # 获取所有进程信息
    for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 
                                     'memory_percent', 'create_time']):
        try:
            info = proc.as_dict()
            
            # 过滤无效进程
            if info['cpu_percent'] is None or info['memory_percent'] is None:
                continue
                
            processes.append({
                "pid": info['pid'],
                "name": info['name'],
                "user": info['username'] or "unknown",
                "cpu_percent": round(info['cpu_percent'], 1),
                "mem_percent": round(info['memory_percent'], 1),
                "start_time": datetime.fromtimestamp(info['create_time']).strftime("%Y-%m-%d %H:%M:%S")
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    # 按CPU使用率降序排序，取Top N
    return sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)[:top_n]


def collect_remote_processes(ssh_conn: paramiko.SSHClient, top_n: int = 5) -> List[Dict[str, Any]]:
    """采集远程服务器Top进程信息"""
    # 执行命令获取Top进程（按CPU使用率排序）
    success, output, error = execute_command(
        ssh_conn, f"ps -eo pid,user,%cpu,%mem,comm,lstart --sort=-%cpu | head -n {top_n + 1} | tail -n {top_n}"
    )
    
    if not success:
        raise RuntimeError(f"进程信息采集失败：{error}"if TopCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    else "Failed to collect process information: {error}")
    
    processes = []
    for line in output.split('\n'):
        line = line.strip()
        if not line:
            continue
            
        # 解析ps命令输出
        parts = line.split(maxsplit=5)  # 最多分割5次，保留命令完整名称
        if len(parts) < 6:
            continue
            
        pid, user, cpu, mem, comm, start_time = parts
        
        # 格式化启动时间
        start_time_str = ' '.join(start_time.split()[:5])  # 取前5个字段（忽略年份）
        
        processes.append({
            "pid": int(pid),
            "name": comm,
            "user": user,
            "cpu_percent": round(float(cpu), 1),
            "mem_percent": round(float(mem), 1),
            "start_time": start_time_str
        })
    
    return processes


def get_process_metrics(is_local: bool, ssh_conn: Union[paramiko.SSHClient, None], 
                       top_n: int = 5) -> Dict[str, List[Dict[str, Any]]]:
    """统一入口：根据服务器类型获取进程指标"""
    if is_local:
        return {"processes": collect_local_processes(top_n)}
    else:
        if not ssh_conn:
            raise RuntimeError("远程磁盘采集需要SSH连接"if TopCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    else "Remote disk collection requires an SSH connection")
        return {"processes": collect_remote_processes(ssh_conn, top_n)}
    