from typing import Union, Dict, Any, List
import paramiko
import subprocess
import re
from mcp.server import FastMCP
from config.public.base_config_loader import LanguageEnum
from config.private.perf_interrupt.config_loader import PerfInterruptConfig

config = PerfInterruptConfig().get_config()
mcp = FastMCP(
    "Performance Interrupt Health Check MCP Server",
    host="0.0.0.0",
    port=config.private_config.port
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
    """检查系统中断统计信息"""
    
    def parse_interrupts_output(output: str) -> List[Dict[str, Any]]:
        interrupts = []
        pattern = re.compile(
            r'^\s*(\d+):\s+'       # 中断号
            r'([0-9,\s]+)\s+'      # CPU分布
            r'(\S+)\s+'             # 中断类型
            r'(\S+)\s+'             # 后缀或IRQ号
            r'(.*)$',               # 设备名称
            re.MULTILINE
        )
        for match in pattern.finditer(output):
            irq_number = match.group(1)
            cpu_distribution = [int(x.replace(',', '')) for x in match.group(2).split()]
            interrupt_type = match.group(3)
            suffix = match.group(4)
            device = match.group(5).strip()
            total_count = sum(cpu_distribution)
            interrupts.append({
                'irq_number': f"{irq_number}:{suffix}",
                'total_count': total_count,
                'device': device,
                'cpu_distribution': cpu_distribution,
                'interrupt_type': interrupt_type
            })
        # 过滤阈值
        return sorted([irq for irq in interrupts if irq['total_count'] > 300],
                      key=lambda x: x['total_count'], reverse=True)

    try:
        if host is None:
            result = subprocess.run(['cat', '/proc/interrupts'],
                                    capture_output=True, text=True, check=True)
            output = result.stdout
        else:
            target_host = None
            for h in config.public_config.remote_hosts:
                if host.strip() in (h.host, h.name):
                    target_host = h
                    break
            if not target_host:
                msg = f"未找到远程主机: {host}" if config.public_config.language == LanguageEnum.ZH else f"Remote host not found: {host}"
                raise ValueError(msg)

            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                client.connect(
                    hostname=target_host.host,
                    port=getattr(target_host, 'port', 22),
                    username=getattr(target_host, 'username', None),
                    password=getattr(target_host, 'password', None),
                    key_filename=getattr(target_host, 'ssh_key_path', None),
                    timeout=10
                )
                stdin, stdout, stderr = client.exec_command('cat /proc/interrupts')
                stdout.channel.recv_exit_status()
                output = stdout.read().decode('utf-8')
                err = stderr.read().decode('utf-8').strip()
                if err:
                    raise RuntimeError(err)
            finally:
                client.close()

        return parse_interrupts_output(output)

    except subprocess.CalledProcessError as e:
        msg = e.stderr or e.stdout or str(e)
        raise RuntimeError(f"本地中断信息获取失败: {msg}" if config.public_config.language == LanguageEnum.ZH
                           else f"Local interrupt info retrieval failed: {msg}")
    except paramiko.AuthenticationException:
        raise RuntimeError("SSH 认证失败，请检查用户名或密钥" if config.public_config.language == LanguageEnum.ZH
                           else "SSH authentication failed, please check the username or key")
    except paramiko.SSHException as e:
        raise RuntimeError(f"SSH 连接错误: {e}" if config.public_config.language == LanguageEnum.ZH
                           else f"SSH connection error: {e}")
    except Exception as e:
        raise RuntimeError(f"获取中断信息失败: {str(e)}" if config.public_config.language == LanguageEnum.ZH
                           else f"Failed to retrieve interrupt information: {str(e)}")

if __name__ == "__main__":
    mcp.run(transport='sse')
