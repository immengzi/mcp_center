import os
import subprocess
from typing import Dict, Optional
import paramiko
from paramiko.ssh_exception import (
    SSHException, AuthenticationException, NoValidConnectionsError
)

from config.private.nohup.config_loader import NohupCommandConfig
from config.public.base_config_loader import LanguageEnum

def _run_local_nohup(
    command: str,
    output_file: Optional[str] = None,
    working_dir: Optional[str] = None
) -> Dict:
    """本地执行nohup命令（原有逻辑）"""
    # 根据配置获取语言
    is_zh = NohupCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    
    result = {
        "success": False,
        "message": "",
        "pid": None,
        "output_file": output_file or "nohup.out",
        "command": command,
        "host": "localhost"
    }

    output_file = output_file or "nohup.out"
    cwd = working_dir or os.getcwd()

    if not os.path.exists(cwd):
        result["message"] = (f"工作目录不存在: {cwd}" 
                           if is_zh else f"Working directory does not exist: {cwd}")
        return result

    try:
        # 构建本地nohup命令
        nohup_cmd = f"nohup {command} > {output_file} 2>&1 & echo $!"
        proc = subprocess.run(
            nohup_cmd,
            shell=True,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )

        if proc.stderr:
            result["message"] = (f"本地执行错误: {proc.stderr.strip()}" 
                               if is_zh else f"Local execution error: {proc.stderr.strip()}")
            return result

        # 解析PID
        pid_str = proc.stdout.strip()
        if pid_str and pid_str.isdigit():
            result["pid"] = int(pid_str)
            result["success"] = True
            result["message"] = (f"本地命令已后台运行，PID: {pid_str}，日志: {output_file}" 
                               if is_zh else f"Local command running in background, PID: {pid_str}, log: {output_file}")
        else:
            result["message"] = (f"本地无法获取PID: {pid_str}" 
                               if is_zh else f"Failed to get local PID: {pid_str}")

    except Exception as e:
        result["message"] = (f"本地执行异常: {str(e)}" 
                           if is_zh else f"Local execution exception: {str(e)}")

    return result


def _run_remote_nohup(
    command: str,
    host: str,
    username: str,
    password: str,
    port: int = 22,
    output_file: Optional[str] = None,
    working_dir: Optional[str] = None
) -> Dict:
    """远程执行nohup命令（新增逻辑）"""
    # 根据配置获取语言
    is_zh = NohupCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    
    result = {
        "success": False,
        "message": "",
        "pid": None,
        "output_file": output_file or "nohup.out",
        "command": command,
        "host": host
    }

    # 处理远程路径
    output_file = output_file or "nohup.out"
    remote_cwd = working_dir or "~"  # 远程默认工作目录为用户家目录

    # 创建SSH客户端
    ssh: Optional[paramiko.SSHClient] = None
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=host,
            port=port,
            username=username,
            password=password,
            timeout=10
        )

        # 检查远程工作目录是否存在
        check_dir_cmd = f"if [ -d {remote_cwd} ]; then echo exists; else echo not_exists; fi"
        stdin, stdout, stderr = ssh.exec_command(check_dir_cmd, timeout=5)
        dir_status = stdout.read().decode().strip()
        if dir_status == "not_exists":
            result["message"] = (f"远程工作目录不存在: {remote_cwd}" 
                               if is_zh else f"Remote working directory does not exist: {remote_cwd}")
            return result

        # 构建远程nohup命令（处理路径转义）
        remote_output = os.path.join(remote_cwd, output_file) if remote_cwd != "~" else output_file
        nohup_cmd = (
            f"cd {remote_cwd} && "
            f"nohup {command} > {remote_output} 2>&1 & "
            f"echo $!"  # 获取后台进程PID
        )

        # 执行远程命令
        stdin, stdout, stderr = ssh.exec_command(nohup_cmd, timeout=10)
        error = stderr.read().decode().strip()
        if error:
            result["message"] = (f"远程执行错误: {error}" 
                               if is_zh else f"Remote execution error: {error}")
            return result

        # 解析远程PID
        pid_str = stdout.read().decode().strip()
        if pid_str and pid_str.isdigit():
            result["pid"] = int(pid_str)
            result["success"] = True
            result["message"] = (f"远程命令已后台运行，PID: {pid_str}，日志: {remote_output}" 
                               if is_zh else f"Remote command running in background, PID: {pid_str}, log: {remote_output}")
        else:
            result["message"] = (f"远程无法获取PID: {pid_str}" 
                               if is_zh else f"Failed to get remote PID: {pid_str}")

    except AuthenticationException:
        result["message"] = ("SSH认证失败（用户名/密码错误）" 
                           if is_zh else "SSH authentication failed (username/password error)")
    except NoValidConnectionsError:
        result["message"] = (f"无法连接到远程主机 {host}:{port}" 
                           if is_zh else f"Could not connect to remote host {host}:{port}")
    except SSHException as e:
        result["message"] = (f"SSH协议错误或超时: {str(e)}" 
                           if is_zh else f"SSH protocol error or timeout: {str(e)}")
    except Exception as e:
        result["message"] = (f"远程执行异常: {str(e)}" 
                           if is_zh else f"Remote execution exception: {str(e)}")
    finally:
        if ssh:
            ssh.close()

    return result