import paramiko
import subprocess
import re
from typing import Dict, Optional, List
from config.public.base_config_loader import LanguageEnum
from config.private.firewalld.config_loader import FirewalldConfig
def get_language() -> bool:
    """获取语言配置：True=中文，False=英文"""
    return FirewalldConfig().get_config().public_config.language == LanguageEnum.ZH


def get_remote_auth(host: str) -> Optional[Dict]:
    """从配置获取远程主机认证信息"""
    remote_hosts = FirewalldConfig().get_config().public_config.remote_hosts
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
    """执行远程命令（需要root权限）"""
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
        # firewalld命令需要sudo权限
        stdin, stdout, stderr = ssh_conn.exec_command(f"sudo {command}", timeout=30)
        # 处理sudo密码交互
        stdin.write(f"{auth['password']}\n")
        stdin.flush()
        
        result["output"] = stdout.read().decode("utf-8", errors="replace").strip()
        result["error"] = stderr.read().decode("utf-8", errors="replace").strip()
        # 判断成功：无错误输出或包含"success"关键词
        result["success"] = len(result["error"]) == 0 or "success" in result["output"].lower()

    except Exception as e:
        result["error"] = str(e)
    finally:
        if ssh_conn and ssh_conn.get_transport() and ssh_conn.get_transport().is_active(): # type: ignore
            ssh_conn.close()

    return result


def execute_local_command(command: str) -> Dict:
    """执行本地命令（需要root权限）"""
    result = {
        "success": False,
        "output": "",
        "error": ""
    }

    try:
        # 本地执行需要sudo权限
        output = subprocess.check_output(
            f"sudo {command}",
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
        result["error"] = "命令执行超时（firewalld操作未完成）" if get_language() else "Command timeout (firewalld operation incomplete)"
    except Exception as e:
        result["error"] = str(e)

    return result


def parse_firewalld_rules(output: str) -> List[Dict]:
    """解析firewalld规则列表"""
    rules = []
    # 匹配区域和规则的正则表达式
    zone_pattern = re.compile(r'zone\s+"([^"]+)"')
    service_pattern = re.compile(r'service\s+"([^"]+)"\s+.*?enabled')
    port_pattern = re.compile(r'port\s+port="([^"]+)",protocol="([^"]+)"\s+.*?enabled')
    rich_rule_pattern = re.compile(r'rich rule\s+rule\s+(.*?)\s+enabled')
    masquerade_pattern = re.compile(r'masquerade\s+.*?enabled')
    forward_port_pattern = re.compile(r'forward-port\s+port="([^"]+)",protocol="([^"]+)",to-port="([^"]+)",to-addr="([^"]+)"')

    current_zone = ""
    for line in output.splitlines():
        # 提取当前区域
        zone_match = zone_pattern.search(line)
        if zone_match:
            current_zone = zone_match.group(1)
            continue
            
        if current_zone:
            # 解析服务规则
            service_match = service_pattern.search(line)
            if service_match:
                rules.append({
                    "zone": current_zone,
                    "type": "service",
                    "name": service_match.group(1),
                    "status": "enabled"
                })
            
            # 解析端口规则
            port_match = port_pattern.search(line)
            if port_match:
                rules.append({
                    "zone": current_zone,
                    "type": "port",
                    "port": port_match.group(1),
                    "protocol": port_match.group(2),
                    "status": "enabled"
                })
                
            # 解析富规则（IP限制等）
            rich_match = rich_rule_pattern.search(line)
            if rich_match:
                rules.append({
                    "zone": current_zone,
                    "type": "rich_rule",
                    "rule": rich_match.group(1),
                    "status": "enabled"
                })
                
            # 解析地址伪装规则
            masquerade_match = masquerade_pattern.search(line)
            if masquerade_match:
                rules.append({
                    "zone": current_zone,
                    "type": "masquerade",
                    "status": "enabled"
                })
                
            # 解析端口转发规则
            forward_match = forward_port_pattern.search(line)
            if forward_match:
                rules.append({
                    "zone": current_zone,
                    "type": "forward_port",
                    "source_port": forward_match.group(1),
                    "protocol": forward_match.group(2),
                    "dest_port": forward_match.group(3),
                    "dest_ip": forward_match.group(4),
                    "status": "enabled"
                })
    
    return rules


def parse_firewalld_zones(output: str) -> List[Dict]:
    """解析防火墙区域信息"""
    zones = []
    # 分割不同区域的配置
    zone_sections = re.split(r'Zone:\s+', output)[1:]
    
    for section in zone_sections:
        if not section.strip():
            continue
            
        # 提取区域名称
        name_match = re.match(r'(\w+)\s', section)
        if not name_match:
            continue
        zone_name = name_match.group(1)
        
        # 提取默认区域标识
        is_default = "default zone" in section.lower()
        
        # 提取关联的网络接口
        interfaces = re.findall(r'interfaces:\s*(\w+)', section)
        
        # 提取目标策略
        target_match = re.search(r'target:\s*(\w+)', section)
        target = target_match.group(1) if target_match else "default"
        
        zones.append({
            "name": zone_name,
            "is_default": is_default,
            "interfaces": interfaces,
            "target": target
        })
    
    return zones
