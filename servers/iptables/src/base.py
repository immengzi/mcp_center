import paramiko
import subprocess
import re
from typing import Dict, Optional, List
from config.private.iptables.config_loader import IptablesConfig
from config.public.base_config_loader import LanguageEnum

def get_language() -> bool:
    """获取语言配置：True=中文，False=英文"""
    return IptablesConfig().get_config().public_config.language == LanguageEnum.ZH


def get_remote_auth(host: str) -> Optional[Dict]:
    """从配置获取远程主机认证信息"""
    remote_hosts = IptablesConfig().get_config().public_config.remote_hosts
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
    """执行远程iptables命令（需要root权限）"""
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
        # iptables需要sudo权限
        stdin, stdout, stderr = ssh_conn.exec_command(f"sudo {command}", timeout=30)
        # 处理sudo密码交互
        stdin.write(f"{auth['password']}\n")
        stdin.flush()
        
        result["output"] = stdout.read().decode("utf-8", errors="replace").strip()
        result["error"] = stderr.read().decode("utf-8", errors="replace").strip()
        result["success"] = len(result["error"]) == 0 or "Chain" in result["output"]

    except Exception as e:
        result["error"] = str(e)
    finally:
        if ssh_conn and ssh_conn.get_transport() and ssh_conn.get_transport().is_active(): # type: ignore
            ssh_conn.close()

    return result


def execute_local_command(command: str) -> Dict:
    """执行本地iptables命令（需要root权限）"""
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
        result["error"] = "命令执行超时（iptables操作未完成）" if get_language() else "Command timeout (iptables operation incomplete)"
    except Exception as e:
        result["error"] = str(e)

    return result


def parse_iptables_rules(output: str) -> List[Dict]:
    """解析iptables规则列表"""
    rules = []
    # 分割不同的链
    chain_sections = re.split(r'Chain\s+(\w+)\s', output)
    
    for i in range(1, len(chain_sections), 2):
        chain_name = chain_sections[i]
        chain_content = chain_sections[i+1]
        
        # 解析每条规则
        for line in chain_content.splitlines():
            line = line.strip()
            if not line or line.startswith(('target', 'Chain', 'pkts')):
                continue
                
            # 分割规则字段（处理多个空格）
            parts = re.split(r'\s+', line, 8)  # 最多分割为9个部分
            if len(parts) < 9:
                continue
                
            target, prot, opt, source, destination, _, _, _, details = parts
            
            rules.append({
                "chain": chain_name,
                "target": target,
                "protocol": prot,
                "source": source,
                "destination": destination,
                "details": details
            })
    
    return rules


def parse_nat_rules(output: str) -> List[Dict]:
    """解析NAT表规则（用于端口转发）"""
    nat_rules = []
    # 查找NAT表部分
    nat_match = re.search(r'Chain\s+PREROUTING\s.*?(?=Chain|$)', output, re.DOTALL)
    if not nat_match:
        return nat_rules
        
    nat_content = nat_match.group(0)
    for line in nat_content.splitlines():
        line = line.strip()
        if not line or line.startswith(('target', 'pkts')):
            continue
            
        parts = re.split(r'\s+', line, 8)
        if len(parts) < 9:
            continue
            
        target, prot, opt, source, destination, _, _, _, details = parts
        
        # 提取转发信息
        dnat_match = re.search(r'DNAT\s+to:([\d.]+):(\d+)', details)
        if dnat_match:
            nat_rules.append({
                "chain": "PREROUTING",
                "target": target,
                "protocol": prot,
                "source": source,
                "destination": destination,
                "to_ip": dnat_match.group(1),
                "to_port": dnat_match.group(2),
                "details": details
            })
    
    return nat_rules
