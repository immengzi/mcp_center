from typing import Union, Dict, Any
import paramiko
import subprocess
import re
import json
from mcp.server import FastMCP
from config.public.base_config_loader import LanguageEnum
from config.private.lscpu.config_loader import LscpuConfig

mcp = FastMCP("Lscpu Info MCP Server", host="0.0.0.0", port=LscpuConfig().get_config().private_config.port)

@mcp.tool(
    name="lscpu_info_tool"
    if LscpuConfig().get_config().public_config.language == LanguageEnum.ZH
    else "lscpu_info_tool",
    description='''
    使用lscpu命令获取远端机器或者本机CPU架构等核心静态信息
    1. 输入值如下：
        - host: 远程主机名称或IP地址，若不提供则表示获取本机信息
    2. 返回值为包含CPU架构与系统信息的字典，包含以下键：
        - architecture: 架构（如 x86_64）
        - cpus_total: 总CPU数量
        - model_name: CPU型号名称
        - cpu_max_mhz: CPU最大频率（MHz，浮点数）
        - vulnerabilities: 常见安全漏洞的缓解状态字典
    '''
    if LscpuConfig().get_config().public_config.language == LanguageEnum.ZH
    else 
    '''
    Use the lscpu command to obtain static information such as CPU architecture from a remote machine
    or the local machine.
    1. Input values are as follows:
        - host: Remote host name or IP address. If not provided, retrieves local machine info.
    2. The return value is a dictionary containing CPU architecture and system information, with
        each dictionary including the following keys:
        - architecture: CPU architecture (e.g., x86_64)
        - cpus_total: Total number of CPUs
        - model_name: CPU model name
        - cpu_max_mhz: Maximum CPU frequency in MHz (float)
        - vulnerabilities: Dictionary of vulnerability mitigation statuses
    '''
)

def lscpu_info_tool(host: Union[str, None] = None) -> Dict[str, Any]:
    """
    使用lscpu命令获取本地或远程主机的CPU核心静态信息
    """
    def parse_lscpu_json(data: Dict[str, Any]) -> Dict[str, Any]:
        info = {
            'architecture': '',
            'cpus_total': 0,
            'model_name': '',
            'cpu_max_mhz': 0.0,
            'vulnerabilities': {}
        }

        def traverse(entries):
            for item in entries:
                field_raw = item["field"].strip()
                value = item.get("data", "").strip()

                if field_raw == "Architecture:":
                    info['architecture'] = value
                elif field_raw == "CPU(s):":
                    try:
                        info['cpus_total'] = int(value.split()[0])
                    except (ValueError, IndexError):
                        info['cpus_total'] = 0
                elif field_raw == "Model name:":
                    info['model_name'] = value
                elif field_raw == "CPU max MHz:":
                    try:
                        info['cpu_max_mhz'] = float(value.split()[0])
                    except (ValueError, IndexError):
                        info['cpu_max_mhz'] = 0.0

                elif field_raw.startswith("Vulnerability "):
                    vuln_name = field_raw[len("Vulnerability "):].strip(": ")
                    normalized_key = vuln_name.lower().replace(' ', '_').replace('-', '_')
                    info['vulnerabilities'][normalized_key] = value

                if "children" in item:
                    traverse(item["children"])

        traverse(data.get("lscpu", []))
        return info

    try:
        if host is None:
            result = subprocess.run(['lscpu', '-J'], capture_output=True, text=True, check=True)
            output = result.stdout
        else:
            config = LscpuConfig().get_config()
            target_host = None
            for host_config in config.public_config.remote_hosts:
                if host.strip() == host_config.name or host.strip() == host_config.host:
                    target_host = host_config
                    break

            if not target_host:
                if config.public_config.language == LanguageEnum.ZH:
                    raise ValueError(f"未找到远程主机: {host}")
                else:
                    raise ValueError(f"Remote host not found: {host}")

            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                hostname=target_host.host,
                port=target_host.port,
                username=target_host.username,
                password=getattr(target_host, "password", None),
                key_filename=getattr(target_host, "ssh_key_path", None),
                timeout=10
            )
            stdin, stdout, stderr = client.exec_command('lscpu -J')
            output = stdout.read().decode('utf-8')
            err = stderr.read().decode('utf-8').strip()
            client.close()

            if err:
                raise RuntimeError(err)

        data = json.loads(output.strip())
        return parse_lscpu_json(data)

    except subprocess.CalledProcessError as e:
        if LscpuConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise RuntimeError(f"本地 lscpu 执行失败: {e.stderr}")
        else:
            raise RuntimeError(f"Local lscpu execution failed: {e.stderr}")
    except paramiko.AuthenticationException:
        if LscpuConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise RuntimeError("SSH 认证失败，请检查用户名或密钥")
        else:
            raise RuntimeError("SSH authentication failed, please check the username or key")
    except paramiko.SSHException as e:
        if LscpuConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise RuntimeError(f"SSH 连接错误: {e}")
        else:
            raise RuntimeError(f"SSH connection error: {e}")
    except Exception as e:
        if LscpuConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise RuntimeError(f"获取 CPU 信息失败: {str(e)}")
        else:
            raise RuntimeError(f"Failed to retrieve CPU information: {str(e)}")

        


if __name__ == "__main__":
    mcp.run(transport='sse')