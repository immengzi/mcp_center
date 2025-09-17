import os
import subprocess
from typing import Dict, Optional
import paramiko


# -------------------------- 私有辅助函数（简化核心逻辑，避免代码冗余） --------------------------


def _is_local_process_exist(pid: int) -> bool:
    """检查本地进程是否存在（通过/proc文件系统判断）"""
    return os.path.exists(f"/proc/{pid}")


def _is_remote_process_exist(ssh_conn: paramiko.SSHClient, pid: int) -> bool:
    """检查远程进程是否存在（通过ps命令判断）"""
    stdin, stdout, stderr = ssh_conn.exec_command(f"ps -p {pid} > /dev/null 2>&1 && echo 1 || echo 0")
    return stdout.read().decode("utf-8").strip() == "1"
