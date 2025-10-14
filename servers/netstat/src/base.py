import re
import subprocess
from typing import Dict, List, Optional

import paramiko

from config.private.netstat.config_loader import NetstatConfig
from config.public.base_config_loader import LanguageEnum


def get_language() -> bool:
    """获取语言配置：True=中文，False=英文"""
    return NetstatConfig().get_config().public_config.language == LanguageEnum.ZH


def get_remote_auth(host: str) -> Optional[Dict]:
    """从配置获取远程主机认证信息（遵循原有配置类逻辑）"""
    remote_hosts = NetstatConfig().get_config().public_config.remote_hosts
    for host_config in remote_hosts:
        # 匹配主机IP或配置中的主机名
        if host in [host_config.host, host_config.name]:
            return {
                "host": host_config.host,
                "port": host_config.port,
                "username": host_config.username,
                "password": host_config.password
            }
    return None


def execute_remote_command(auth: Dict, command: str) -> Dict:
    """执行远程命令（适配netstat输出解析）"""
    result = {
        "success": False,
        "output": "",
        "error": ""
    }
    ssh_conn: Optional[paramiko.SSHClient] = None

    try:
        ssh_conn = paramiko.SSHClient()
        ssh_conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_conn.connect(
            hostname=auth["host"],
            port=auth["port"],
            username=auth["username"],
            password=auth["password"],
            timeout=15,
            banner_timeout=10
        )
        stdin, stdout, stderr = ssh_conn.exec_command(command, timeout=30)
        result["output"] = stdout.read().decode("utf-8", errors="replace").strip()
        result["error"] = stderr.read().decode("utf-8", errors="replace").strip()
        # netstat正常执行无错误输出即判定成功
        result["success"] = len(result["error"]) == 0

    except Exception as e:
        result["error"] = str(e)
    finally:
        if ssh_conn and ssh_conn.get_transport() and ssh_conn.get_transport().is_active(): # type: ignore
            ssh_conn.close()

    return result


def execute_local_command(command: str) -> Dict:
    """执行本地命令"""
    result = {
        "success": False,
        "output": "",
        "error": ""
    }

    try:
        output = subprocess.check_output(
            command,
            shell=True,
            text=True,
            stderr=subprocess.STDOUT,
            timeout=30
        )
        result["output"] = output.strip()
        result["success"] = True
    except subprocess.CalledProcessError as e:
        result["error"] = e.output.strip()
    except subprocess.TimeoutExpired:
        result["error"] = "命令执行超时（netstat查询未完成）" if get_language() else "Command timeout (netstat query incomplete)"
    except Exception as e:
        result["error"] = str(e)

    return result


def parse_netstat_connections(output: str) -> List[Dict]:
    """解析netstat连接列表输出（支持tcp/udp）"""
    connections = []
    # 匹配netstat -tulnp输出格式：Proto Recv-Q Send-Q Local Address           Foreign Address         State       PID/Program name
    conn_pattern = re.compile(
        r'^(\S+)\s+(\d+)\s+(\d+)\s+([0-9.:]+)\s+([0-9.:*]+)\s+(\S+)?\s+(\d+/\S+)?$',
        re.MULTILINE
    )

    for match in conn_pattern.finditer(output):
        proto, recv_q, send_q, local_addr, foreign_addr, state, pid_program = match.groups()
        # 拆分本地地址与端口
        local_ip, local_port = local_addr.rsplit(':', 1) if ':' in local_addr else (local_addr, '')
        # 拆分远程地址与端口（foreign_addr可能为*:*）
        foreign_ip, foreign_port = foreign_addr.rsplit(':', 1) if ':' in foreign_addr and foreign_addr != '*:*' else (foreign_addr, '')
        
        connections.append({
            "protocol": proto.upper(),  # 协议（TCP/UDP）
            "recv_queue": int(recv_q),  # 接收队列
            "send_queue": int(send_q),  # 发送队列
            "local_ip": local_ip,       # 本地IP
            "local_port": local_port,   # 本地端口
            "foreign_ip": foreign_ip,   # 远程IP
            "foreign_port": foreign_port,  # 远程端口
            "state": state if state else "-",  # 连接状态（UDP无状态）
            "pid": pid_program.split('/')[0] if pid_program else "-",  # 进程ID
            "program": pid_program.split('/')[1] if pid_program and '/' in pid_program else "-"  # 进程名
        })
    return connections


def parse_port_occupation(output: str, port: str) -> List[Dict]:
    """解析指定端口的占用情况"""
    port_occupations = []
    connections = parse_netstat_connections(output)
    # 筛选本地端口匹配的记录
    for conn in connections:
        if conn["local_port"] == port:
            port_occupations.append({
                "protocol": conn["protocol"],
                "local_ip": conn["local_ip"],
                "pid": conn["pid"],
                "program": conn["program"],
                "state": conn["state"]
            })
    return port_occupations
