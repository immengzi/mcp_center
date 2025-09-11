from typing import Union, Dict, Any, List
import paramiko
import subprocess
import re
import json
from mcp.server import FastMCP
from config.public.base_config_loader import LanguageEnum
from config.private.perf_interrupt.config_loader import PerfInterruptConfig

# 获取配置并初始化MCP服务
mcp = FastMCP(
    "Performance Interrupt Health Check MCP Server",
    host="0.0.0.0",
    port=PerfInterruptConfig().get_config().private_config.port
)

@mcp.tool(
    name="perf_interrupt_health_check"
    if PerfInterruptConfig().get_config().public_config.language == LanguageEnum.ZH
    else "perf_interrupt_health_check",
    description='''
    检查系统中断统计信息以定位高频中断导致的CPU占用
    1. 输入值如下：
        - host: 远程主机名称或IP地址，若不提供则表示获取本机信息
    2. 返回值为包含中断信息的列表，每个元素包含：
        - irq_number: 中断编号
        - total_count: 总触发次数
        - device: 设备名称
        - cpu_distribution: 各CPU核心的中断分布
    '''
    if PerfInterruptConfig().get_config().public_config.language == LanguageEnum.ZH
    else 
    '''
    Check system interrupt statistics to identify high-frequency interrupts causing CPU usage
    1. Input values are as follows:
        - host: Remote host name or IP address. If not provided, retrieves local machine info.
    2. The return value is a list containing interrupt information, each element includes:
        - irq_number: Interrupt number
        - total_count: Total trigger count
        - device: Device name
        - cpu_distribution: Interrupt distribution across CPU cores
    '''
)
def perf_interrupt_health_check(host: Union[str, None] = None) -> List[Dict[str, Any]]:
    """
    检查系统中断统计信息以定位高频中断
    """
    def parse_interrupts_output(output: str) -> List[Dict[str, Any]]:
        interrupts = []
        
        # 匹配中断行的正则表达式
        pattern = re.compile(
            r'^\s*(\d+):\s+'  # 中断号
            r'([0-9\,\s]+)\s+'  # CPU分布
            r'(\w+-\w+)\s+'  # 中断类型
            r'(\d+)\s+'  # 中断号后缀
            r'(.*)'  # 设备名称
            r'$',
            re.MULTILINE
        )
        
        for match in pattern.finditer(output):
            irq_number = match.group(1)
            cpu_distribution = [int(count.replace(',', '')) for count in match.group(2).split()]
            interrupt_type = match.group(3)
            suffix = match.group(4)
            device = match.group(5).strip()
            
            # 计算总中断次数
            total_count = sum(cpu_distribution)
            
            interrupts.append({
                'irq_number': f"{irq_number}:{suffix}",
                'total_count': total_count,
                'device': device,
                'cpu_distribution': cpu_distribution,
                'interrupt_type': interrupt_type
            })
        
        filtered_interrupts = [
            irq for irq in interrupts 
            if irq['total_count'] > 300  # 可配置的过滤阈值
        ]

        # 按总次数降序排序
        return sorted(filtered_interrupts, key=lambda x: x['total_count'], reverse=True)

    try:
        if host is None:
            result = subprocess.run(['cat', '/proc/interrupts'], 
                                  capture_output=True, text=True, check=True)
            output = result.stdout
        else:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            config = PerfInterruptConfig().get_config()
            username = config.private_config.ssh_username
            key_file = config.private_config.ssh_key_path
            port = config.private_config.ssh_port or 22

            client.connect(host, port=port, username=username, key_filename=key_file, timeout=10)
            stdin, stdout, stderr = client.exec_command('cat /proc/interrupts')
            output = stdout.read().decode('utf-8')
            client.close()

        return parse_interrupts_output(output)

    except subprocess.CalledProcessError as e:
        if PerfInterruptConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise RuntimeError(f"本地中断信息获取失败: {e.stderr}")
        else:
            raise RuntimeError(f"Local interrupt info retrieval failed: {e.stderr}")
    except paramiko.AuthenticationException:
        if PerfInterruptConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise RuntimeError("SSH 认证失败，请检查用户名或密钥")
        else:
            raise RuntimeError("SSH authentication failed, please check the username or key")
    except paramiko.SSHException as e:
        if PerfInterruptConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise RuntimeError(f"SSH 连接错误: {e}")
        else:
            raise RuntimeError(f"SSH connection error: {e}")
    except Exception as e:
        if PerfInterruptConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise RuntimeError(f"获取中断信息失败: {str(e)}")
        else:
            raise RuntimeError(f"Failed to retrieve interrupt information: {str(e)}")

if __name__ == "__main__":
    # 初始化并运行服务器
    mcp.run(transport='sse')