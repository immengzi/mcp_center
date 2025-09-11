from typing import Union, List, Dict, Any
import paramiko
import subprocess
import re
from mcp.server import FastMCP
from config.public.base_config_loader import LanguageEnum
from config.private.numa_cross_node.config_loader import NumaCrossNodeConfig

mcp = FastMCP("NUMA Cross-Node Checker", host="0.0.0.0", port=NumaCrossNodeConfig().get_config().private_config.port)

@mcp.tool(
    name="numa_cross_node" 
    if NumaCrossNodeConfig().get_config().public_config.language == LanguageEnum.ZH
    else "numa_cross_node",
    description='''自动检测 NUMA 跨节点访问异常的进程（支持本地与远程主机）'''
    if NumaCrossNodeConfig().get_config().public_config.language == LanguageEnum.ZH
    else 
    '''Automatically detects processes with abnormal NUMA cross-node memory access (supports local and remote hosts)'''
)

def numa_cross_node(host: Union[str, None] = None) -> Dict[str, Any]:
    """
    自动检测 NUMA 跨节点访问异常的进程（支持本地和远程主机）
    """
    def run_local_command(command: str) -> str:
        """本地执行命令并返回输出"""
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Local command failed: {command}\nError: {result.stderr}")
        return result.stdout

    def run_remote_command(command: str, host: str) -> str:
        """远程执行命令并返回输出"""
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        config = NumaCrossNodeConfig().get_config()
        username = config.private_config.ssh_username
        key_file = config.private_config.ssh_key_path
        port = config.private_config.ssh_port or 22

        try:
            client.connect(
                hostname=host,
                port=port,
                username=username,
                key_filename=key_file,
                timeout=10
            )
            stdin, stdout, stderr = client.exec_command(command)
            output = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')

            if stdout.channel.recv_exit_status() != 0:
                raise RuntimeError(f"Remote command failed: {command}\nError: {error}")
            return output
        except Exception as e:
            raise RuntimeError(f"Remote execution error: {str(e)}")
        finally:
            client.close()

    def parse_numastat_processes(output: str) -> List[Dict[str, Any]]:
        """解析 numastat -c 的输出，提取每个进程的内存使用情况"""
        lines = output.strip().split('\n')
        header = lines[0].split()
        data_lines = lines[1:]

        # 提取字段索引
        pid_idx = header.index('pid')
        tgid_idx = header.index('tgid')
        local_node_idx = header.index('local_node')
        other_node_idx = header.index('other_node')

        processes = []
        for line in data_lines:
            fields = line.split()
            if len(fields) < max(pid_idx, tgid_idx, local_node_idx, other_node_idx):
                continue

            pid = int(fields[pid_idx])
            local = int(fields[local_node_idx])
            other = int(fields[other_node_idx])
            total = local + other

            if total == 0:
                ratio = 0.0
            else:
                ratio = (other / total) * 100  # 百分比

            processes.append({
                'pid': pid,
                'local_memory': local,
                'remote_memory': other,
                'cross_ratio': round(ratio, 2),
            })

        return processes

    def get_process_info(pid: int) -> Dict[str, str]:
        """获取进程名称和命令行参数"""
        try:
            # 获取进程名称和命令行
            ps_output = run_local_command(f"ps -p {pid} -o comm=,cmd= --no-headers")
            parts = ps_output.strip().split('\t', 1)
            if len(parts) < 2:
                name, command = parts[0], parts[0]
            else:
                name, command = parts

            return {'name': name, 'command': command}
        except Exception as e:
            return {'name': f'Unknown (PID {pid})', 'command': f'Failed to retrieve: {str(e)}'}

    try:
        # Step 1: 获取所有进程的 NUMA 内存使用情况
        if host is None:
            numastat_output = run_local_command('numastat -c')
        else:
            numastat_output = run_remote_command('numastat -c', host)

        processes = parse_numastat_processes(numastat_output)

        # Step 2: 筛选异常进程 (other_node 占比 > 50%)
        threshold = 50
        anomaly_processes = []
        for proc in processes:
            if proc['cross_ratio'] > threshold:
                proc_info = get_process_info(proc['pid'])
                proc.update(proc_info)
                anomaly_processes.append(proc)

        # Step 3: 构建结构化输出
        has_issue = len(anomaly_processes) > 0
        severity = "none"
        if has_issue:
            if len(anomaly_processes) > 3:
                severity = "high"
            elif len(anomaly_processes) > 1:
                severity = "medium"
            else:
                severity = "low"

        summary = (
            f"{len(anomaly_processes)} processes have more than {threshold}% memory accessed from remote nodes."
            if has_issue
            else "No processes with abnormal NUMA access detected."
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
        if NumaCrossNodeConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise RuntimeError(f"NUMA 异常检测失败: {str(e)}")
        else:
            raise RuntimeError(f"NUMA anomaly detection failed: {str(e)}")

if __name__ == "__main__":
    mcp.run(transport='sse')