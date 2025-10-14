from typing import Dict, List, Optional
import paramiko
import subprocess
import re

from config.private.npu.config_loader import NpuSmiConfig
from config.public.base_config_loader import LanguageEnum

def get_language() -> bool:
    """获取语言配置：True=中文，False=英文"""
    return NpuSmiConfig().get_config().public_config.language == LanguageEnum.ZH


def get_remote_auth(host: str) -> Optional[Dict]:
    """从配置获取远程主机认证信息"""
    remote_hosts = NpuSmiConfig().get_config().public_config.remote_hosts
    for host_config in remote_hosts:
        # 假设remote_hosts中每个元素是字典，包含"host"/"hostname"/"port"/"username"/"password"键
        if host in [host_config.host, host_config.name]:
            # 返回标准连接字典，确保键与后续使用一致
            return {
                "host": host_config.host,  # 默认为目标IP
                "port": host_config.port,  # 默认为SSH默认端口22
                "username": host_config.username,
                "password": host_config.password
            }
    return None


def execute_remote_command(auth: Dict, command: str) -> Dict:
    """执行远程命令并返回结果"""
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
            timeout=10,
            banner_timeout=10
        )
        
        stdin, stdout, stderr = ssh_conn.exec_command(command)
        result["output"] = stdout.read().decode("utf-8", errors="replace").strip()
        result["error"] = stderr.read().decode("utf-8", errors="replace").strip()
        
        if not result["error"]:
            result["success"] = True
            
    except Exception as e:
        result["error"] = str(e)
    finally:
        if ssh_conn:
            transport = ssh_conn.get_transport()
            if transport and transport.is_active():
                ssh_conn.close()
    
    return result


def execute_local_command(command: str) -> Dict:
    """执行本地命令并返回结果"""
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
            stderr=subprocess.STDOUT
        )
        result["output"] = output.strip()
        result["success"] = True
    except subprocess.CalledProcessError as e:
        result["error"] = e.output.strip()
    except Exception as e:
        result["error"] = str(e)
    
    return result


def parse_npu_info(output: str) -> List[Dict]:
    """解析npu-smi输出的设备信息"""
    npus = []
    lines = [line.strip() for line in output.split('\n') if line.strip()]
    
    # 查找设备信息起始行
    start_index = -1
    for i, line in enumerate(lines):
        if re.match(r'^\+-+\+', line):  # 表格分隔线
            start_index = i + 1
            break
    
    if start_index == -1:
        return npus
    
    # 解析表头
    header_line = lines[start_index]
    headers = [h.strip() for h in re.split(r'\s*\|\s*', header_line) if h.strip()]
    start_index += 2  # 跳过表头和分隔线
    
    # 解析每个NPU设备信息
    for line in lines[start_index:]:
        if re.match(r'^\+-+\+', line):  # 结束分隔线
            break
            
        values = [v.strip() for v in re.split(r'\s*\|\s*', line) if v.strip()]
        if len(values) != len(headers):
            continue
            
        npu_info = dict(zip(headers, values))
        
        # 转换数值类型
        for key in npu_info:
            if key in ['Id', 'Memory-Usage (MiB)', 'Utilization (%)', 'Temperature (°C)']:
                try:
                    # 处理内存使用等格式如"1024/8192"
                    if '/' in npu_info[key]:
                        parts = npu_info[key].split('/')
                        npu_info[key] = {
                            'used': int(parts[0]),
                            'total': int(parts[1])
                        }
                    else:
                        npu_info[key] = int(npu_info[key])
                except ValueError:
                    pass
                    
        npus.append(npu_info)
    
    return npus

