from typing import Dict, List, Optional
import paramiko
import subprocess
import re

from config.private.lsof.config_loader import LsofConfig
from config.public.base_config_loader import LanguageEnum

def get_language() -> bool:
    """获取语言配置：True=中文，False=英文"""
    return LsofConfig().get_config().public_config.language == LanguageEnum.ZH


def get_remote_auth(host: str) -> Optional[Dict]:
    """从配置获取远程主机认证信息（遵循原有配置类逻辑）"""
    remote_hosts = LsofConfig().get_config().public_config.remote_hosts
    for host_config in remote_hosts:
        if host in [host_config.host, host_config.name]:
            return {
                "host": host_config.host,
                "port": host_config.port,
                "username": host_config.username,
                "password": host_config.password
            }
    return None


def execute_remote_command(auth: Dict, command: str) -> Dict:
    """执行远程命令（适配lsof输出解析）"""
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
        result["success"] = len(result["error"]) == 0

    except Exception as e:
        result["error"] = str(e)
    finally:
        if ssh_conn and ssh_conn.get_transport() and ssh_conn.get_transport().is_active():  # type: ignore
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
        result["error"] = "命令执行超时（lsof查询未完成）" if get_language() else "Command timeout (lsof query incomplete)"
    except Exception as e:
        result["error"] = str(e)

    return result


def parse_lsof_network_output(output: str) -> List[Dict]:
    """解析lsof网络相关输出"""
    connections = []
    # lsof -i 输出格式：COMMAND  PID   USER   FD   TYPE DEVICE SIZE/OFF NODE NAME
    lines = output.splitlines()
    if not lines:
        return connections

    # 跳过表头行
    for line in lines[1:]:
        parts = re.split(r'\s+', line.strip(), maxsplit=8)
        if len(parts) < 9:
            continue

        command, pid, user, fd, type_, device, size_off, node, name = parts
        
        # 解析网络地址信息
        local = ""
        foreign = ""
        state = ""
        if '->' in name:
            local_foreign = name.split('->')
            local = local_foreign[0].strip()
            if len(local_foreign) > 1:
                foreign_part = local_foreign[1].split()
                foreign = foreign_part[0].strip()
                if len(foreign_part) > 1:
                    state = foreign_part[1].strip('()')
        
        connections.append({
            "command": command,
            "pid": pid,
            "user": user,
            "fd": fd,
            "type": type_,
            "device": device,
            "size_off": size_off,
            "node": node,
            "local_address": local,
            "foreign_address": foreign,
            "state": state
        })
    
    return connections


def parse_lsof_file_output(output: str) -> List[Dict]:
    """解析lsof文件相关输出"""
    files = []
    # lsof 文件名 输出格式：COMMAND  PID   USER   FD   TYPE DEVICE SIZE/OFF NODE NAME
    lines = output.splitlines()
    if not lines:
        return files

    # 跳过表头行
    for line in lines[1:]:
        parts = re.split(r'\s+', line.strip(), maxsplit=8)
        if len(parts) < 9:
            continue

        command, pid, user, fd, type_, device, size_off, node, name = parts
        
        files.append({
            "command": command,
            "pid": pid,
            "user": user,
            "fd": fd,
            "type": type_,
            "device": device,
            "size_off": size_off,
            "node": node,
            "file_path": name
        })
    
    return files

