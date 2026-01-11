import re
import subprocess
from typing import Any, Dict, List, Optional

import paramiko
from mcp.server import FastMCP

from config.private.perf_interrupt.config_loader import PerfInterruptConfig
from config.public.base_config_loader import LanguageEnum

# 初始化配置
config = PerfInterruptConfig()

mcp = FastMCP(
    "Performance Interrupt Health Check MCP Server",
    host="0.0.0.0",
    port=config.get_config().private_config.port
)


@mcp.tool(
    name="perf_interrupt_health_check"
    if config.get_config().public_config.language == LanguageEnum.ZH
    else "perf_interrupt_health_check",
    description="""
    检查系统中断统计信息以定位高频中断导致的 CPU 占用。
    参数：
        host: 可选，远程主机名称（使用public_config.toml中配置的name字段）；留空则获取本机信息。
    返回：
        list [{
            "irq_number": str,        # 中断编号
            "total_count": int,       # 总触发次数
            "device": str,            # 设备名称
            "cpu_distribution": list, # 各CPU核心的中断分布
            "interrupt_type": str     # 中断类型
        }]
    """
    if config.get_config().public_config.language == LanguageEnum.ZH
    else """
    Check system interrupt statistics to identify high-frequency interrupts causing CPU usage.
    Args:
        host: Optional remote host name (configured in public_config.toml); retrieves local info if omitted.
    Returns:
        list [{
            "irq_number": str,        # Interrupt number
            "total_count": int,       # Total trigger count
            "device": str,            # Device name
            "cpu_distribution": list, # Interrupt distribution across CPU cores
            "interrupt_type": str     # Interrupt type
        }]
    """
)
def perf_interrupt_health_check(host: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    检查系统中断统计信息
    
    Args:
        host: 远程主机名称（public_config.toml 中的 name），None 表示本机
        
    Returns:
        中断信息列表
    """
    cfg = config.get_config()
    is_zh = cfg.public_config.language == LanguageEnum.ZH
    
    # 本地执行
    if not host or host.strip().lower() in ("", "localhost"):
        return _execute_local_interrupts(is_zh)
    
    # 远程执行
    return _execute_remote_interrupts_workflow(host.strip(), cfg, is_zh)


def _execute_local_interrupts(is_zh: bool) -> List[Dict[str, Any]]:
    """执行本地中断统计"""
    try:
        result = subprocess.run(
            ['cat', '/proc/interrupts'],
            capture_output=True,
            text=True,
            check=True
        )
        return _parse_interrupts_output(result.stdout)
    except subprocess.CalledProcessError as e:
        msg = f"读取 /proc/interrupts 失败: {e.stderr}" if is_zh else f"Failed to read /proc/interrupts: {e.stderr}"
        raise RuntimeError(msg) from e


def _execute_remote_interrupts_workflow(
    host_name: str, cfg, is_zh: bool
) -> List[Dict[str, Any]]:
    """远程执行工作流"""
    target_host = _find_remote_host(host_name, cfg.public_config.remote_hosts, is_zh)
    
    try:
        return _execute_remote_interrupts(target_host, is_zh)
    except Exception as e:
        msg = (
            f"远程执行失败 [{target_host.name}]: {str(e)}" if is_zh
            else f"Remote execution failed [{target_host.name}]: {str(e)}"
        )
        raise RuntimeError(msg) from e


def _find_remote_host(host_name: str, remote_hosts: list, is_zh: bool):
    """查找远程主机配置"""
    for host in remote_hosts:
        if host.name == host_name or host.host == host_name:
            return host
    
    available = ", ".join([h.name for h in remote_hosts])
    msg = (
        f"未找到远程主机: {host_name}，可用: {available}" if is_zh
        else f"Host not found: {host_name}, available: {available}"
    )
    raise ValueError(msg)


def _execute_remote_interrupts(host_config, is_zh: bool) -> List[Dict[str, Any]]:
    """在远程主机读取中断统计"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        client.connect(
            hostname=host_config.host,
            port=host_config.port,
            username=host_config.username,
            password=host_config.password,
            timeout=10
        )
        
        stdin, stdout, stderr = client.exec_command('cat /proc/interrupts')
        stdin.close()
        
        output = stdout.read().decode('utf-8')
        err = stderr.read().decode('utf-8').strip()
        
        if err:
            raise RuntimeError(f"Failed to read /proc/interrupts: {err}")
        
        return _parse_interrupts_output(output)
    except paramiko.AuthenticationException as e:
        msg = "SSH认证失败" if is_zh else "SSH auth failed"
        raise ConnectionError(msg) from e
    finally:
        client.close()


def _parse_interrupts_output(output: str) -> List[Dict[str, Any]]:
    """解析 /proc/interrupts 输出"""
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
    # 过滤阈值并排序
    return sorted([irq for irq in interrupts if irq['total_count'] > 300],
                  key=lambda x: x['total_count'], reverse=True)


if __name__ == "__main__":
    mcp.run(transport='sse')
