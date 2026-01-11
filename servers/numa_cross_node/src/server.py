import os
from typing import Any, Dict, Optional

import paramiko
from mcp.server import FastMCP

from config.private.numa_cross_node.config_loader import NumaCrossNodeConfig
from config.public.base_config_loader import LanguageEnum

# 初始化配置
config = NumaCrossNodeConfig()

mcp = FastMCP(
    "NUMA Cross-Node Checker",
    host="0.0.0.0",
    port=config.get_config().private_config.port
)


@mcp.tool(
    name="numa_cross_node"
    if config.get_config().public_config.language == LanguageEnum.ZH
    else "numa_cross_node",
    description="""
    自动检测 NUMA 跨节点访问异常的进程（支持本地与远程主机）。
    参数：
        host: 可选，远程主机名称（使用public_config.toml中配置的name字段）；留空则检测本机。
        threshold: 跨节点内存比例阈值（默认 30%）。
    返回：
        dict {
            "overall_conclusion": {
                "has_issue": bool,
                "severity": str,         # none/low/medium/high
                "summary": str
            },
            "anomaly_processes": [{
                "pid": int,
                "local_memory": int,
                "remote_memory": int,
                "cross_ratio": float,
                "name": str,
                "command": str
            }]
        }
    """
    if config.get_config().public_config.language == LanguageEnum.ZH
    else """
    Automatically detect processes with NUMA cross-node access anomalies (supports local and remote hosts).
    Args:
        host: Optional remote host name (configured in public_config.toml); detects local host if omitted.
        threshold: Cross-node memory ratio threshold (default 30%).
    Returns:
        dict {
            "overall_conclusion": {
                "has_issue": bool,
                "severity": str,         # none/low/medium/high
                "summary": str
            },
            "anomaly_processes": [{
                "pid": int,
                "local_memory": int,
                "remote_memory": int,
                "cross_ratio": float,
                "name": str,
                "command": str
            }]
        }
    """
)
def numa_cross_node(host: Optional[str] = None, threshold: float = 30.0) -> Dict[str, Any]:
    """
    检测 NUMA 跨节点异常进程
    
    Args:
        host: 远程主机名称（public_config.toml 中的 name），None 表示本机
        threshold: 跨节点内存比例阈值
        
    Returns:
        包含检测结果的字典
    """
    cfg = config.get_config()
    is_zh = cfg.public_config.language == LanguageEnum.ZH
    
    try:
        # 本地执行
        if not host or host.strip().lower() in ("", "localhost"):
            anomaly_processes = _detect_local_anomalies(threshold)
        else:
            # 远程执行
            anomaly_processes = _detect_remote_anomalies(host.strip(), threshold, cfg, is_zh)
        
        return _build_conclusion(anomaly_processes, threshold)
    except Exception as e:
        msg = f"NUMA 异常检测失败: {str(e)}" if is_zh else f"NUMA anomaly detection failed: {str(e)}"
        return {
            "overall_conclusion": {
                "has_issue": True,
                "severity": "high",
                "summary": msg
            },
            "anomaly_processes": []
        }


def _detect_local_anomalies(threshold: float) -> list:
    """检测本地 NUMA 跨节点异常进程"""
    anomaly_processes = []
    pids = [pid for pid in os.listdir("/proc") if pid.isdigit()]
    
    for pid in map(int, pids):
        try:
            with open(f"/proc/{pid}/numa_maps") as f:
                stats = _parse_numa_maps_content(f.read())
            if stats["cross_ratio"] > threshold:
                stats.update(_get_local_process_info(pid))
                stats["pid"] = pid
                anomaly_processes.append(stats)
        except Exception:
            continue
    
    return anomaly_processes


def _detect_remote_anomalies(host_name: str, threshold: float, cfg, is_zh: bool) -> list:
    """检测远程 NUMA 跨节点异常进程"""
    target_host = _find_remote_host(host_name, cfg.public_config.remote_hosts, is_zh)
    
    # 一次 SSH 获取所有 pid 和 numa_maps
    command = r"""
for pid in $(ls /proc | grep '^[0-9]\+'); do
    echo "===PID:$pid==="
    cat /proc/$pid/numa_maps 2>/dev/null
done
"""
    try:
        output = _run_remote_command(command, target_host, is_zh)
        return _parse_remote_output(output, threshold, target_host)
    except Exception as e:
        msg = f"远程检测失败: {str(e)}" if is_zh else f"Remote detection failed: {str(e)}"
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


def _run_remote_command(command: str, host_config, is_zh: bool) -> str:
    """在远程主机执行命令"""
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
        
        stdin, stdout, stderr = client.exec_command(command)
        stdin.close()
        
        exit_code = stdout.channel.recv_exit_status()
        output = stdout.read().decode("utf-8")
        error = stderr.read().decode("utf-8").strip()
        
        if exit_code != 0:
            raise RuntimeError(error or f"Command failed with exit code {exit_code}")
        
        return output
    except paramiko.AuthenticationException as e:
        msg = "SSH认证失败" if is_zh else "SSH auth failed"
        raise ConnectionError(msg) from e
    finally:
        client.close()


def _parse_numa_maps_content(content: str) -> Dict[str, Any]:
    """解析 numa_maps 文件内容"""
    counts = {}
    for line in content.splitlines():
        for part in line.split():
            if part.startswith("N") and "=" in part:
                node, val = part.split("=")
                counts[node] = counts.get(node, 0) + int(val)
    
    total = sum(counts.values())
    if total == 0:
        return {"local_memory": 0, "remote_memory": 0, "cross_ratio": 0.0}
    
    local = counts.get("N0", 0)
    remote = total - local
    return {
        "local_memory": local,
        "remote_memory": remote,
        "cross_ratio": round(remote / total * 100, 2)
    }


def _get_local_process_info(pid: int) -> Dict[str, str]:
    """获取本地进程信息"""
    try:
        with open(f"/proc/{pid}/comm") as f:
            name = f.read().strip()
        with open(f"/proc/{pid}/cmdline") as f:
            command = f.read().replace("\x00", " ").strip() or name
        return {"name": name, "command": command}
    except Exception:
        return {"name": f"Unknown (PID {pid})", "command": ""}


def _get_remote_process_info(pid: int, host_config, is_zh: bool) -> Dict[str, str]:
    """获取远程进程信息"""
    try:
        name = _run_remote_command(f"cat /proc/{pid}/comm", host_config, is_zh).strip()
        command = _run_remote_command(f"cat /proc/{pid}/cmdline", host_config, is_zh)
        command = command.replace("\x00", " ").strip() or name
        return {"name": name, "command": command}
    except Exception:
        return {"name": f"Unknown (PID {pid})", "command": ""}


def _parse_remote_output(output: str, threshold: float, host_config) -> list:
    """解析远程输出"""
    anomaly_processes = []
    current_pid = None
    buffer = []
    
    for line in output.splitlines():
        if line.startswith("===PID:") and line.endswith("==="):
            # 处理上一个 pid
            if current_pid is not None:
                stats = _parse_numa_maps_content("\n".join(buffer))
                if stats["cross_ratio"] > threshold:
                    info = _get_remote_process_info(current_pid, host_config, False)
                    stats.update(info)
                    stats["pid"] = current_pid
                    anomaly_processes.append(stats)
            current_pid = int(line[len("===PID:"):-3])
            buffer = []
        else:
            buffer.append(line)
    
    # 最后一个 pid
    if current_pid is not None:
        stats = _parse_numa_maps_content("\n".join(buffer))
        if stats["cross_ratio"] > threshold:
            info = _get_remote_process_info(current_pid, host_config, False)
            stats.update(info)
            stats["pid"] = current_pid
            anomaly_processes.append(stats)
    
    return anomaly_processes


def _build_conclusion(anomaly_processes: list, threshold: float) -> Dict[str, Any]:
    """构建检测结论"""
    has_issue = len(anomaly_processes) > 0
    severity = "none"
    
    if has_issue:
        max_ratio = max(p["cross_ratio"] for p in anomaly_processes)
        if max_ratio > 80:
            severity = "high"
        elif max_ratio > 50:
            severity = "medium"
        else:
            severity = "low"
    
    summary = (
        f"{len(anomaly_processes)} processes exceed {threshold}% cross-node memory ratio."
        if has_issue else
        "No processes with abnormal NUMA cross-node memory detected."
    )
    
    return {
        "overall_conclusion": {
            "has_issue": has_issue,
            "severity": severity,
            "summary": summary
        },
        "anomaly_processes": anomaly_processes
    }


if __name__ == "__main__":
    mcp.run(transport="sse")
