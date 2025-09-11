"""网络维度实现：专注于网络指标的采集与解析"""
import psutil
from typing import Any, Dict, Union, List
import paramiko
from base import execute_command
from config.private.top.config_loader import TopCommandConfig
from config.public.base_config_loader import LanguageEnum


def collect_local_network() -> Dict[str, Any]:
    """采集本地服务器网络指标"""
    # 获取所有网络接口信息
    interfaces = []
    net_io = psutil.net_io_counters(pernic=True)
    net_stats = psutil.net_if_stats()
    
    for iface, stats in net_stats.items():
        if not stats.isup:  # 只统计活跃接口
            continue
            
        io = net_io.get(iface, None)
        if not io:
            continue
            
        interfaces.append({
            "interface": iface,
            "speed_mbps": stats.speed,
            "bytes_sent_mb": round(io.bytes_sent / (1024 **2), 1),
            "bytes_recv_mb": round(io.bytes_recv / (1024** 2), 1),
            "packets_sent": io.packets_sent,
            "packets_recv": io.packets_recv
        })
    
    # 获取TCP连接数
    connections = psutil.net_connections()
    tcp_established = sum(1 for c in connections if c.status == psutil.CONN_ESTABLISHED)
    
    return {
        "interfaces": interfaces,
        "connections": {
            "tcp_established": tcp_established,
            "total": len(connections)
        }
    }


def collect_remote_network(ssh_conn: paramiko.SSHClient) -> Dict[str, Any]:
    """采集远程服务器网络指标"""
    # 1. 获取网络接口信息
    success, iface_output, error = execute_command(
        ssh_conn, "ifconfig | grep -E '^[a-zA-Z]' | awk '{print $1}' | tr -d ':'"
    )
    if not success:
        raise RuntimeError(f"网络接口信息采集失败：{error}"if TopCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    else"Failed to collect network interface information: {error}")
    
    interfaces = []
    for iface in iface_output.split('\n'):
        iface = iface.strip()
        if not iface:
            continue
            
        # 获取接口详细信息
        success, stats_output, error = execute_command(
            ssh_conn, f"ifconfig {iface} | grep -E 'RX bytes|TX bytes|Speed'"
        )
        if not success:
            continue
            
        # 解析接口数据
        rx_bytes = 0
        tx_bytes = 0
        speed = 0
        
        for line in stats_output.split('\n'):
            if 'RX bytes' in line:
                rx_bytes = int(line.split('RX bytes:')[1].split()[0])
            if 'TX bytes' in line:
                tx_bytes = int(line.split('TX bytes:')[1].split()[0])
            if 'Speed' in line:
                speed = int(line.split('Speed=')[1].split('M')[0])
                
        interfaces.append({
            "interface": iface,
            "speed_mbps": speed,
            "bytes_sent_mb": round(tx_bytes / (1024 **2), 1),
            "bytes_recv_mb": round(rx_bytes / (1024** 2), 1)
        })
    
    # 2. 获取TCP连接数
    success, conn_output, error = execute_command(
        ssh_conn, "netstat -an | grep -c ESTABLISHED"
    )
    if not success:
        raise RuntimeError(f"连接数采集失败：{error}")
    
    return {
        "interfaces": interfaces,
        "connections": {
            "tcp_established": int(conn_output.strip()),
            "total": int(conn_output.strip())  # 简化处理，实际可扩展
        }
    }


def get_network_metrics(is_local: bool, ssh_conn: Union[paramiko.SSHClient, None]) -> Dict[str, Any]:
    """统一入口：根据服务器类型获取网络指标"""
    if is_local:
        return {"network": collect_local_network()}
    else:
        if not ssh_conn:
            raise RuntimeError("远程磁盘采集需要SSH连接"if TopCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    else "Remote disk collection requires an SSH connection")
        return {"network": collect_remote_network(ssh_conn)}
    