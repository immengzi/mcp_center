from asyncio.log import logger
import re
import json
import paramiko
import subprocess
from typing import Dict, Optional, List
from config.private.docker.config_loader import DockerConfig
from config.public.base_config_loader import LanguageEnum
def get_language() -> bool:
    """获取语言配置：True=中文，False=英文"""
    return DockerConfig().get_config().public_config.language == LanguageEnum.ZH


def get_remote_auth(host: str) -> Optional[Dict]:
    """从配置获取远程主机认证信息"""
    remote_hosts = DockerConfig().get_config().public_config.remote_hosts
    for host_config in remote_hosts:
        if host in [host_config.host, host_config.name]:
            return {
                "host": host_config.host,
                "port": host_config.port,
                "username": host_config.username,
                "password": host_config.password,
                "docker_port": 2375  # Docker远程API端口
            }
    return None


def execute_remote_command(auth: Dict, command: str) -> Dict:
    """执行远程Docker命令（通过SSH）"""
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
        # 执行Docker命令（远程环境需确保用户有Docker权限）
        stdin, stdout, stderr = ssh_conn.exec_command(command, timeout=60)
        result["output"] = stdout.read().decode("utf-8", errors="replace").strip()
        result["error"] = stderr.read().decode("utf-8", errors="replace").strip()
        # 判断成功：无错误输出或包含Docker操作特征信息
        result["success"] = len(result["error"]) == 0 or (
            "Created" in result["output"] or 
            "Started" in result["output"] or 
            "Deleted" in result["output"] or
            "Successfully" in result["output"]
        )

    except Exception as e:
        result["error"] = str(e)
    finally:
        if ssh_conn and ssh_conn.get_transport() and ssh_conn.get_transport().is_active(): # type: ignore
            ssh_conn.close()

    return result


def execute_local_command(command: str) -> Dict:
    """执行本地Docker命令"""
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
            timeout=60
        )
        result["output"] = output.strip()
        result["success"] = True
    except subprocess.CalledProcessError as e:
        result["error"] = e.output.strip()
    except subprocess.TimeoutExpired:
        result["error"] = "命令执行超时（Docker操作未完成）" if get_language() else "Command timeout (Docker operation incomplete)"
    except Exception as e:
        result["error"] = str(e)

    return result


def parse_container_list(output: str) -> List[Dict]:
    """解析容器列表输出（docker ps 结果）"""
    containers = []
    if not output:
        return containers
    
    # 处理docker ps输出（表头行+数据行）
    lines = output.splitlines()
    if len(lines) < 2:
        return containers
    
    # 解析表头（兼容不同Docker版本的列顺序）
    header = re.split(r'\s{2,}', lines[0].strip())
    for line in lines[1:]:
        parts = re.split(r'\s{2,}', line.strip(), len(header)-1)
        if len(parts) != len(header):
            continue
        
        container = dict(zip(header, parts))
        # 标准化字段格式
        containers.append({
            "id": container.get("CONTAINER ID", ""),
            "name": container.get("NAMES", ""),
            "image": container.get("IMAGE", ""),
            "command": container.get("COMMAND", ""),
            "created": container.get("CREATED", ""),
            "status": container.get("STATUS", ""),
            "ports": container.get("PORTS", ""),
            "networks": container.get("NETWORKS", "")
        })
    return containers


def parse_image_list(output: str) -> List[Dict]:
    """解析镜像列表输出（docker images 结果）"""
    images = []
    if not output:
        return images
    
    lines = output.splitlines()
    if len(lines) < 2:
        return images
    
    header = re.split(r'\s{2,}', lines[0].strip())
    for line in lines[1:]:
        parts = re.split(r'\s{2,}', line.strip(), len(header)-1)
        if len(parts) != len(header):
            continue
        
        image = dict(zip(header, parts))
        images.append({
            "repository": image.get("REPOSITORY", ""),
            "tag": image.get("TAG", ""),
            "id": image.get("IMAGE ID", ""),
            "created": image.get("CREATED", ""),
            "size": image.get("SIZE", "")
        })
    return images


def parse_container_inspect(output: str) -> Optional[Dict]:
    """解析容器详情（docker inspect 结果）"""
    try:
        inspect_data = json.loads(output)
        if isinstance(inspect_data, list) and len(inspect_data) > 0:
            return {
                "id": inspect_data[0]["Id"],
                "name": inspect_data[0]["Name"].lstrip("/"),
                "image": inspect_data[0]["Config"]["Image"],
                "state": inspect_data[0]["State"],
                "network_settings": inspect_data[0]["NetworkSettings"],
                "mounts": inspect_data[0]["Mounts"],
                "env": inspect_data[0]["Config"]["Env"],
                "cmd": inspect_data[0]["Config"]["Cmd"],
                "created": inspect_data[0]["Created"]
            }
    except json.JSONDecodeError:
        logger.error("Failed to parse container inspect data")
    return None
