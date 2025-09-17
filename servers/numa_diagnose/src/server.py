from typing import Any, Union, Dict
import re
import paramiko
import subprocess
from mcp.server import FastMCP
from config.public.base_config_loader import LanguageEnum
from config.private.numa_diagnose.config_loader import NumaDiagnoseConfig

mcp = FastMCP(
    "NUMA Hardware Monitoring Server",
    host="0.0.0.0",
    port=NumaDiagnoseConfig().get_config().private_config.port
)

def _parse_cpu_frequencies(output: str) -> Dict[str, float]:
    """解析CPU实时频率信息"""
    frequencies = {}
    for line in output.split('\n'):
        if ': ' in line and "MHz" in line:
            try:
                path, freq = line.split(': ')
                cpu_id = path.split('/')[-3].replace('cpu', '')
                frequencies[f"cpu{cpu_id}"] = float(freq.replace(' MHz', '').strip())
            except Exception:
                continue
    return frequencies

def _parse_cpu_specifications(output: str) -> Dict[str, Any]:
    result = {}
    numa_nodes = {}
    
    for line in output.split('\n'):
        if line.startswith("Model name:"):
            result["model_name"] = line.split(":")[1].strip()
        elif line.startswith("CPU max MHz:"):
            result["max_mhz"] = float(line.split(":")[1].strip())
        elif line.startswith("CPU min MHz:"):
            result["min_mhz"] = float(line.split(":")[1].strip())
        elif line.startswith("NUMA node"):
            parts = line.split(':')
            if len(parts) < 2:
                continue
            match = re.search(r'node(\d+)', parts[0])
            if match:
                node_id = match.group(1)
                cpus_str = parts[1].strip()
                cpu_list = []
                for part in cpus_str.split(','):
                    part = part.strip()
                    if '-' in part:
                        start, end = map(int, part.split('-'))
                        cpu_list.extend(range(start, end + 1))
                    elif part.isdigit():
                        cpu_list.append(int(part))
                numa_nodes[node_id] = {"cpus": cpu_list}
    
    result["numa_nodes"] = numa_nodes
    return result

def execute_command(cmd: str, host: Union[str, None] = None) -> str:
    """执行命令并返回输出"""
    try:
        if host:  # 仅当指定了 host 时才尝试远程
            print(f"[DEBUG] Looking for remote host: {host}")
            for config in NumaDiagnoseConfig().get_config().public_config.remote_hosts:
                if host == config.name or host == config.host:
                    print(f"[DEBUG] Found remote host: {config.name} ({config.host})")
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh.connect(
                        hostname=config.host,
                        port=config.port,
                        username=config.username,
                        password=config.password
                    )
                    stdin, stdout, stderr = ssh.exec_command(cmd)
                    output = stdout.read().decode() + stderr.read().decode()
                    ssh.close()
                    print(f"[DEBUG] Remote command output:\n{output}")
                    return output
            raise ValueError(f"Remote host {host} not found in configuration")
        else:
            print(f"[DEBUG] Running local command: {cmd}")
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                check=False
            )
            output = result.stdout + result.stderr
            print(f"[DEBUG] Local command output:\n{output}")
            return output
    except Exception as e:
        print(f"[ERROR] Command execution failed: {str(e)}")
        raise

@mcp.tool(
    name="numa_diagnose"
    if NumaDiagnoseConfig().get_config().public_config.language == LanguageEnum.ZH
    else "numa_diagnose",
    description='''
    获取NUMA架构硬件监控信息
    1. 输入参数：
        - host: 远程主机地址（可选）
    2. 返回字段：
        - real_time_frequencies: 各CPU核心实时频率(MHz)
        - specifications: CPU规格信息（型号/频率范围/NUMA节点）
        - numa_topology: NUMA拓扑结构
    '''
    if NumaDiagnoseConfig().get_config().public_config.language == LanguageEnum.ZH
    else '''
    Get NUMA hardware monitoring information
    1. Parameters:
        - host: Remote host address (optional)
    2. Return fields:
        - real_time_frequencies: Real-time frequency of each CPU core (MHz)
        - specifications: CPU specifications (model/frequency range/NUMA nodes)
        - numa_topology: NUMA topology
    '''
)
def numa_diagnose(host: Union[str, None] = None) -> Dict[str, Any]:
    """获取NUMA硬件监控信息"""

    # 获取实时频率
    real_time_cmd = 'for i in /sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_cur_freq; do [ -f $i ] && echo "$i: $(($(cat $i)/1000)) MHz"; done'
    try:
        real_time_output = execute_command(real_time_cmd, host)
        real_time_frequencies = _parse_cpu_frequencies(real_time_output)
    except Exception as e:
        print(f"[ERROR] Failed to parse real-time frequencies: {str(e)}")
        real_time_frequencies = {}

    # 获取规格和NUMA信息
    try:
        lscpu_output = execute_command('lscpu', host)
        specifications = _parse_cpu_specifications(lscpu_output)
    except Exception as e:
        print(f"[ERROR] Failed to parse CPU specifications: {str(e)}")
        specifications = {
            "model_name": "Unknown",
            "max_mhz": 0,
            "min_mhz": 0,
            "numa_nodes": {}
        }

    return {
        "real_time_frequencies": real_time_frequencies,
        "specifications": specifications,
        "numa_topology": specifications.get("numa_nodes", {})
    }

if __name__ == "__main__":
    mcp.run(transport='sse')
