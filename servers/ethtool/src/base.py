import paramiko
import subprocess
import re
from typing import Dict, Optional
from config.private.ethtool.config_loader import EthtoolConfig
from config.public.base_config_loader import LanguageEnum

def get_language() -> bool:
    """获取语言配置：True=中文，False=英文"""
    return EthtoolConfig().get_config().public_config.language == LanguageEnum.ZH


def get_remote_auth(host: str) -> Optional[Dict]:
    """从配置获取远程主机认证信息（遵循原有配置类逻辑）"""
    remote_hosts = EthtoolConfig().get_config().public_config.remote_hosts
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
    """执行远程命令（适配ethtool输出解析）"""
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
        result["error"] = "命令执行超时（ethtool查询未完成）" if get_language() else "Command timeout (ethtool query incomplete)"
    except Exception as e:
        result["error"] = str(e)

    return result


def parse_ethtool_basic(output: str, iface: str) -> Dict:
    """解析ethtool基础信息输出"""
    info = {
        "interface": iface,
        "driver": "",
        "version": "",
        "firmware_version": "",
        "bus_info": "",
        "supports_wake_on": "",
        "current_wake_on": "",
        "speed": "",
        "duplex": "",
        "port": "",
        "link_detected": False
    }

    # 提取驱动信息
    driver_match = re.search(r'Driver:\s+(\S+)', output)
    if driver_match:
        info["driver"] = driver_match.group(1)

    # 提取版本信息
    version_match = re.search(r'Version:\s+(\S+)', output)
    if version_match:
        info["version"] = version_match.group(1)

    # 提取固件版本
    firmware_match = re.search(r'Firmware Version:\s+(\S+)', output)
    if firmware_match:
        info["firmware_version"] = firmware_match.group(1)

    # 提取总线信息
    bus_match = re.search(r'Bus info:\s+(\S+)', output)
    if bus_match:
        info["bus_info"] = bus_match.group(1)

    # 提取WOL支持
    wol_support_match = re.search(r'Supports Wake-on:\s+(\S+)', output)
    if wol_support_match:
        info["supports_wake_on"] = wol_support_match.group(1)

    # 提取当前WOL设置
    wol_current_match = re.search(r'Wake-on:\s+(\S+)', output)
    if wol_current_match:
        info["current_wake_on"] = wol_current_match.group(1)

    # 提取速度
    speed_match = re.search(r'Speed:\s+(\S+)', output)
    if speed_match:
        info["speed"] = speed_match.group(1)

    # 提取双工模式
    duplex_match = re.search(r'Duplex:\s+(\S+)', output)
    if duplex_match:
        info["duplex"] = duplex_match.group(1)

    # 提取端口类型
    port_match = re.search(r'Port:\s+(\S+)', output)
    if port_match:
        info["port"] = port_match.group(1)

    # 提取链路状态
    link_match = re.search(r'Link detected:\s+(\S+)', output)
    if link_match:
        info["link_detected"] = link_match.group(1).lower() == "yes"

    return info


def parse_ethtool_features(output: str) -> Dict:
    """解析ethtool特性信息输出"""
    features = {
        "supported": [],
        "advertised": [],
        "speed_duplex": []
    }

    # 提取支持的特性
    supported_match = re.search(r'Supported features:\s+(.+?)(?:\n\n|$)', output, re.DOTALL)
    if supported_match:
        features["supported"] = [f.strip() for f in supported_match.group(1).split() if f.strip()]

    # 提取通告的特性
    advertised_match = re.search(r'Advertised features:\s+(.+?)(?:\n\n|$)', output, re.DOTALL)
    if advertised_match:
        features["advertised"] = [f.strip() for f in advertised_match.group(1).split() if f.strip()]

    # 提取速度和双工模式
    speed_duplex_match = re.search(r'Advertised link modes:\s+(.+?)(?:\n\n|$)', output, re.DOTALL)
    if speed_duplex_match:
        features["speed_duplex"] = [f.strip() for f in speed_duplex_match.group(1).split() if f.strip()]

    return features
