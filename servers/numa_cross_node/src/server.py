from typing import Union, List, Dict, Any, Optional
import os
import paramiko
from mcp.server import FastMCP
from config.public.base_config_loader import LanguageEnum
from config.private.numa_cross_node.config_loader import NumaCrossNodeConfig

config = NumaCrossNodeConfig().get_config()
mcp = FastMCP(
    "NUMA Cross-Node Checker",
    host="0.0.0.0",
    port=config.private_config.port
)


@mcp.tool(
    name="numa_cross_node"
    if NumaCrossNodeConfig().get_config().public_config.language == LanguageEnum.ZH
    else "numa_cross_node",
    description='''
    自动检测 NUMA 跨节点访问异常的进程（支持本地与远程主机）
    输入参数：
        - host: 远程主机 IP/域名（可选），留空则检测本机
        - threshold: 跨节点内存比例阈值（默认 30%）
    输出：
        - overall_conclusion: {
            has_issue: bool,
            severity: str,
            summary: str
        }
        - anomaly_processes: List[{ 
            pid: int,
            local_memory: int,
            remote_memory: int,
            cross_ratio: float,
            name: str,
            command: str
        }]
    '''
    if NumaCrossNodeConfig().get_config().public_config.language == LanguageEnum.ZH
    else '''
    Automatically detect processes with NUMA cross-node access anomalies (supports local and remote hosts)
    Input parameters:
        - host: Remote host IP/domain (optional), if empty, detect the local host
        - threshold: Cross-node memory ratio threshold (default 30%)
    Output:
        - overall_conclusion: {
            has_issue: bool,
            severity: str,
            summary: str
        }
        - anomaly_processes: List[{ 
            pid: int,
            local_memory: int,
            remote_memory: int,
            cross_ratio: float,
            name: str,
            command: str
        }]
    '''
)

def numa_cross_node(host: Optional[str] = None, threshold: float = 30.0) -> Dict[str, Any]:
    """检测 NUMA 跨节点异常进程"""

    def parse_numa_maps_content(content: str) -> Dict[str, Any]:
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
        return {"local_memory": local, "remote_memory": remote, "cross_ratio": round(remote / total * 100, 2)}

    def get_process_info(pid: int, host_cfg=None) -> Dict[str, Any]:
        try:
            if host_cfg is None:
                with open(f"/proc/{pid}/comm") as f:
                    name = f.read().strip()
                with open(f"/proc/{pid}/cmdline") as f:
                    command = f.read().replace("\x00", " ").strip() or name
            else:
                name = run_remote_command(f"cat /proc/{pid}/comm", host_cfg).strip()
                command = run_remote_command(f"cat /proc/{pid}/cmdline", host_cfg).replace("\x00", " ").strip() or name
            return {"name": name, "command": command}
        except Exception:
            return {"name": f"Unknown (PID {pid})", "command": ""}

    def run_remote_command(command: str, host_cfg) -> str:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh.connect(
                hostname=host_cfg.host,
                port=getattr(host_cfg, "port", 22),
                username=getattr(host_cfg, "username", None),
                password=getattr(host_cfg, "password", None),
                key_filename=getattr(host_cfg, "ssh_key_path", None),
                timeout=10
            )
            stdin, stdout, stderr = ssh.exec_command(command)
            exit_code = stdout.channel.recv_exit_status()
            output = stdout.read().decode("utf-8")
            error = stderr.read().decode("utf-8").strip()
            if exit_code != 0:
                raise RuntimeError(error or f"Remote command failed with exit code {exit_code}")
            return output
        finally:
            ssh.close()

    try:
        anomaly_processes = []

        if host is None:
            # 本地处理
            pids = [pid for pid in os.listdir("/proc") if pid.isdigit()]
            for pid in map(int, pids):
                try:
                    with open(f"/proc/{pid}/numa_maps") as f:
                        stats = parse_numa_maps_content(f.read())
                    if stats["cross_ratio"] > threshold:
                        stats.update(get_process_info(pid))
                        stats["pid"] = pid
                        anomaly_processes.append(stats)
                except Exception:
                    continue
        else:
            # 远程处理
            target_host = next(
                (h for h in config.public_config.remote_hosts if host.strip() in (h.host, h.name)),
                None
            )
            if not target_host:
                msg = f"未找到远程主机: {host}" if config.public_config.language == LanguageEnum.ZH else f"Remote host not found: {host}"
                raise ValueError(msg)

            # 一次 SSH 获取所有 pid 和 numa_maps
            command = r"""
for pid in $(ls /proc | grep '^[0-9]\+'); do
    echo "===PID:$pid==="
    cat /proc/$pid/numa_maps 2>/dev/null
done
"""
            output = run_remote_command(command, target_host)

            # 解析远程输出
            current_pid = None
            buffer = []
            for line in output.splitlines():
                if line.startswith("===PID:") and line.endswith("==="):
                    # 处理上一个 pid
                    if current_pid is not None:
                        stats = parse_numa_maps_content("\n".join(buffer))
                        if stats["cross_ratio"] > threshold:
                            info = get_process_info(current_pid, target_host)
                            stats.update(info)
                            stats["pid"] = current_pid
                            anomaly_processes.append(stats)
                    current_pid = int(line[len("===PID:"):-3])
                    buffer = []
                else:
                    buffer.append(line)
            # 最后一个 pid
            if current_pid is not None:
                stats = parse_numa_maps_content("\n".join(buffer))
                if stats["cross_ratio"] > threshold:
                    info = get_process_info(current_pid, target_host)
                    stats.update(info)
                    stats["pid"] = current_pid
                    anomaly_processes.append(stats)

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

    except Exception as e:
        msg = f"NUMA 异常检测失败: {str(e)}" if config.public_config.language == LanguageEnum.ZH else f"NUMA anomaly detection failed: {str(e)}"
        return {
            "overall_conclusion": {
                "has_issue": True,
                "severity": "high",
                "summary": msg
            },
            "anomaly_processes": []
        }


if __name__ == "__main__":
    mcp.run(transport="sse")
