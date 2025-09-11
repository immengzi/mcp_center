from asyncio.log import logger
import re
import subprocess
import paramiko
import os
from typing import Dict, Optional
from paramiko.ssh_exception import (
    SSHException, AuthenticationException, NoValidConnectionsError
)

from config.private.strace.config_loader import StraceCommandConfig
from config.public.base_config_loader import LanguageEnum

# ------------------------------
# 共用基础组件
# ------------------------------
def _create_ssh_connection(host: str, port: int, username: str, password: str) -> Optional[paramiko.SSHClient]:
    """创建SSH连接（共用组件）"""
    # 根据配置获取语言
    is_zh = StraceCommandConfig().get_config().public_config.language == LanguageEnum.ZH
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
        return ssh
    except AuthenticationException:
        logger.error("SSH认证失败：用户名或密码错误" if is_zh else "SSH authentication failed: username or password is incorrect")
    except NoValidConnectionsError:
        logger.error(f"无法连接到远程主机 {host}:{port}" if is_zh else f"Failed to connect to remote host {host}:{port}")
    except SSHException as e:
        logger.error(f"SSH协议错误：{str(e)}" if is_zh else f"SSH protocol error: {str(e)}")
    except Exception as e:
        logger.error(f"SSH连接失败: {str(e)}" if is_zh else f"SSH connection failed: {str(e)}")
    return None


def _validate_local_process(pid: int) -> Optional[str]:
    """验证本地进程是否存在（共用组件）"""
    # 根据配置获取语言
    is_zh = StraceCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    if not os.path.isdir(f"/proc/{pid}"):
        return f"本地进程 {pid} 不存在" if is_zh else f"Local process {pid} does not exist"
    # 检查权限
    try:
        proc_uid = os.stat(f"/proc/{pid}").st_uid
        current_uid = os.getuid()
        if current_uid != 0 and proc_uid != current_uid:
            return (f"权限不足：非root用户只能跟踪自己的进程（进程属于UID {proc_uid}）" 
                    if is_zh else f"Insufficient permissions: non-root users can only track their own processes (process belongs to UID {proc_uid})")
    except Exception as e:
        return (f"验证进程权限失败：{str(e)}" 
                if is_zh else f"Failed to verify process permissions: {str(e)}")
    return None


def _validate_remote_process(ssh: paramiko.SSHClient, pid: int) -> Optional[str]:
    """验证远程进程是否存在（共用组件）"""
    # 根据配置获取语言
    is_zh = StraceCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    try:
        stdin, stdout, stderr = ssh.exec_command(f"test -d /proc/{pid} && echo exists || echo not_exists", timeout=5)
        if stdout.read().decode().strip() != "exists":
            return f"远程进程 {pid} 不存在" if is_zh else f"Remote process {pid} does not exist"
        return None
    except Exception as e:
        return (f"验证远程进程失败: {str(e)}" 
                if is_zh else f"Failed to verify remote process: {str(e)}")


def _check_strace_installed(ssh: paramiko.SSHClient) -> Optional[str]:
    """检查远程服务器是否安装strace（共用组件）"""
    # 根据配置获取语言
    is_zh = StraceCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    try:
        stdin, stdout, stderr = ssh.exec_command("which strace", timeout=5)
        if not stdout.read().decode().strip():
            return (f"远程服务器未安装strace，请先安装（如: apt install strace 或 yum install strace）" 
                    if is_zh else f"strace is not installed on the remote server, please install it first (e.g.: apt install strace or yum install strace)")
        return None
    except Exception as e:
        return (f"检查strace安装失败: {str(e)}" 
                if is_zh else f"Failed to check strace installation: {str(e)}")
    
    
    
    
    
    
    
    
# ------------------------------
# 功能1：跟踪文件和进程运行状态
# ------------------------------
def _run_local_strace_track(
    pid: int,
    output_file: Optional[str] = None,
    follow_children: bool = False,
    duration: Optional[int] = None
) -> Dict:
    """本地执行strace，跟踪进程的文件操作"""
    # 根据配置获取语言
    is_zh = StraceCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    
    result = {
        "success": False,
        "message": "",
        "strace_pid": None,
        "output_file": output_file or f"strace_local_{pid}.log",
        "target_pid": pid,
        "host": "localhost"
    }

    # 验证进程状态
    validate_msg = _validate_local_process(pid)
    if validate_msg:
        result["message"] = validate_msg
        return result

    # 构建strace命令（只跟踪文件相关系统调用）
    strace_cmd = [
        "strace",
        "-p", str(pid),                  # 跟踪目标进程
        "-e", "trace=file",              # 只记录文件相关调用
        "-o", result["output_file"]      # 输出到日志文件
    ]

    # 可选：跟踪子进程
    if follow_children:
        strace_cmd.append("-f")

    # 可选：限制跟踪时长
    cmd = strace_cmd
    if duration:
        cmd = ["timeout", str(duration)] + strace_cmd

    try:
        # 后台启动strace（非阻塞方式）
        proc = subprocess.Popen(cmd)
        result["strace_pid"] = proc.pid
        result["success"] = True
        
        base_msg = (f"已开始跟踪本地进程 {pid} 的文件操作，日志: {result['output_file']}" 
                   if is_zh else f"Started tracking file operations of local process {pid}, log: {result['output_file']}")
        duration_msg = (f"，将在 {duration} 秒后自动停止" 
                      if is_zh else f", will automatically stop after {duration} seconds")
        stop_msg = (f"，如需手动停止请终止进程 {proc.pid}" 
                  if is_zh else f", to stop manually, terminate process {proc.pid}")
        
        msg = base_msg
        if duration:
            msg += duration_msg
        msg += stop_msg
        result["message"] = msg

    except PermissionError:
        result["message"] = (f"权限不足：需要root权限跟踪进程 {pid}" 
                           if is_zh else f"Insufficient permissions: root privileges required to track process {pid}")
    except FileNotFoundError:
        result["message"] = (f"未找到strace工具，请先安装（如: apt install strace 或 yum install strace）" 
                           if is_zh else f"strace tool not found, please install first (e.g.: apt install strace or yum install strace)")
    except Exception as e:
        result["message"] = (f"本地跟踪启动失败：{str(e)}" 
                           if is_zh else f"Failed to start local tracking: {str(e)}")

    return result


def _run_remote_strace_track(
    pid: int,
    host: str,
    username: str,
    password: str,
    port: int = 22,
    output_file: Optional[str] = None,
    follow_children: bool = False,
    duration: Optional[int] = None
) -> Dict:
    """远程执行strace，跟踪进程的文件操作"""
    # 根据配置获取语言
    is_zh = StraceCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    
    result = {
        "success": False,
        "message": "",
        "strace_pid": None,
        "output_file": output_file or f"strace_remote_{pid}.log",
        "target_pid": pid,
        "host": host
    }

    ssh = _create_ssh_connection(host, port, username, password)
    if not ssh:
        result["message"] = (f"SSH连接失败，请检查远程参数" 
                           if is_zh else f"SSH connection failed, please check remote parameters")
        return result

    try:
        # 检查远程进程是否存在
        proc_msg = _validate_remote_process(ssh, pid)
        if proc_msg:
            result["message"] = proc_msg
            return result

        # 检查远程是否安装strace
        strace_msg = _check_strace_installed(ssh)
        if strace_msg:
            result["message"] = strace_msg
            return result

        # 构建远程strace命令
        remote_output = result["output_file"]
        strace_cmd = f"strace -p {pid} -e trace=file -o {remote_output}"
        
        # 跟踪子进程
        if follow_children:
            strace_cmd += " -f"
        
        # 限制跟踪时长
        if duration:
            strace_cmd = f"timeout {duration} {strace_cmd}"
        
        # 后台运行并获取strace自身PID
        strace_cmd += " & echo $!"

        # 执行远程命令
        stdin, stdout, stderr = ssh.exec_command(strace_cmd, timeout=10)
        error = stderr.read().decode().strip()
        if error:
            result["message"] = (f"远程跟踪启动失败：{error}" 
                               if is_zh else f"Failed to start remote tracking: {error}")
            return result

        # 解析strace进程PID
        strace_pid = stdout.read().decode().strip()
        if strace_pid and strace_pid.isdigit():
            result["strace_pid"] = int(strace_pid)
            result["success"] = True
            
            base_msg = (f"已开始跟踪远程进程 {pid} 的文件操作，日志: {remote_output}" 
                       if is_zh else f"Started tracking file operations of remote process {pid}, log: {remote_output}")
            duration_msg = (f"，将在 {duration} 秒后自动停止" 
                          if is_zh else f", will automatically stop after {duration} seconds")
            stop_msg = (f"，如需手动停止请在远程终止进程 {strace_pid}" 
                      if is_zh else f", to stop manually, terminate process {strace_pid} on remote")
            
            msg = base_msg
            if duration:
                msg += duration_msg
            msg += stop_msg
            result["message"] = msg
        else:
            result["message"] = (f"无法获取远程strace进程PID：{strace_pid}" 
                               if is_zh else f"Failed to get remote strace process PID: {strace_pid}")

    except Exception as e:
        result["message"] = (f"远程跟踪异常：{str(e)}" 
                           if is_zh else f"Remote tracking exception: {str(e)}")
    finally:
        if ssh:
            ssh.close()

    return result


# ------------------------------
# 功能2：排查权限不足和文件找不到问题
# ------------------------------
# 错误类型识别正则
PERMISSION_DENIED_PATTERN = re.compile(r"Permission denied|EACCES")
FILE_NOT_FOUND_PATTERN = re.compile(r"No such file or directory|ENOENT")
FILE_OPERATIONS = {"open", "openat", "creat", "read", "write", "unlink", "rename", "mkdir", "rmdir", "access", "stat", "lstat"}


def _parse_strace_errors(log_content: str) -> Dict:
    """解析strace日志，提取权限错误和文件找不到错误"""
    errors = {
        "permission_denied": [],  # 权限不足错误
        "file_not_found": [],     # 文件找不到错误
        "other_errors": []        # 其他错误
    }

    for line in log_content.splitlines():
        if any(op in line for op in FILE_OPERATIONS):
            if PERMISSION_DENIED_PATTERN.search(line):
                errors["permission_denied"].append(_format_error_line(line))
            elif FILE_NOT_FOUND_PATTERN.search(line):
                errors["file_not_found"].append(_format_error_line(line))
            elif "= -1" in line:
                errors["other_errors"].append(_format_error_line(line))

    return errors


def _format_error_line(line: str) -> Dict:
    """格式化错误行，提取关键信息"""
    parts = line.split(" = ")
    if len(parts) < 2:
        return {"raw_line": line, "operation": "unknown", "path": "unknown", "error": "unknown"}

    op_part, error_part = parts[0].strip(), " = ".join(parts[1:]).strip()
    op_match = re.match(r"^(\w+)", op_part)
    operation = op_match.group(1) if op_match else "unknown"
    path_match = re.search(r'"([^"]+)"', op_part)
    path = path_match.group(1) if path_match else "unknown"

    return {
        "raw_line": line,
        "operation": operation,
        "path": path,
        "error": error_part
    }


def _run_local_error_tracking(
    pid: int,
    output_file: Optional[str] = None,
    duration: int = 30
) -> Dict:
    """本地跟踪：监控权限不足和文件找不到错误"""
    # 根据配置获取语言
    is_zh = StraceCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    
    result = {
        "success": False, 
        "message": "", 
        "output_file": output_file or f"strace_error_local_{pid}.log",
        "target_pid": pid, 
        "host": "localhost", 
        "errors": None
    }

    validate_msg = _validate_local_process(pid)
    if validate_msg:
        result["message"] = validate_msg
        return result

    strace_cmd = [
        "strace", "-p", str(pid),
        "-e", f"trace={','.join(FILE_OPERATIONS)}",
        "-o", result["output_file"], "-s", "2048"
    ]

    try:
        subprocess.run(["timeout", str(duration)] + strace_cmd, capture_output=True, text=True)

        if not os.path.exists(result["output_file"]):
            result["message"] = (
                "跟踪完成但未生成日志文件，可能进程无文件操作" 
                if is_zh else "Tracking completed but no log file generated, process may have no file operations"
            )
            result["success"] = True
            return result

        with open(result["output_file"], "r") as f:
            result["errors"] = _parse_strace_errors(f.read())
        
        result["success"] = True
        perm_count = len(result["errors"]["permission_denied"])
        not_found_count = len(result["errors"]["file_not_found"])
        
        result["message"] = (
            f"跟踪完成（持续 {duration} 秒），共捕获 "
            f"权限不足错误 {perm_count} 个，文件找不到错误 {not_found_count} 个，"
            f"日志文件: {result['output_file']}"
            if is_zh else
            f"Tracking completed (duration {duration} seconds), captured "
            f"{perm_count} permission denied errors, {not_found_count} file not found errors, "
            f"log file: {result['output_file']}"
        )

    except Exception as e:
        result["message"] = (
            f"本地错误跟踪失败：{str(e)}" 
            if is_zh else f"Local error tracking failed: {str(e)}"
        )

    return result

def _run_remote_error_tracking(
    pid: int, host: str, username: str, password: str, port: int = 22,
    output_file: Optional[str] = None, duration: int = 30
) -> Dict:
    """远程跟踪：监控权限不足和文件找不到错误"""
    # 根据配置获取语言
    is_zh = StraceCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    
    result = {
        "success": False, "message": "", "output_file": output_file or f"strace_error_remote_{pid}.log",
        "target_pid": pid, "host": host, "errors": None
    }

    ssh = _create_ssh_connection(host, port, username, password)
    if not ssh:
        result["message"] = "SSH连接失败" if is_zh else "SSH connection failed"
        return result

    try:
        # 检查远程进程和strace安装状态
        proc_msg = _validate_remote_process(ssh, pid)
        strace_msg = _check_strace_installed(ssh)
        if proc_msg or strace_msg:
            result["message"] = proc_msg or strace_msg
            return result

        remote_output = result["output_file"]
        file_ops = ",".join(FILE_OPERATIONS)
        strace_cmd = f"timeout {duration} strace -p {pid} -e trace={file_ops} -o {remote_output} -s 2048"
        
        stdin, stdout, stderr = ssh.exec_command(strace_cmd, timeout=duration + 10)
        error_output = stderr.read().decode().strip()
        if error_output and "timed out" not in error_output.lower():
            result["message"] = (f"远程命令错误：{error_output}" 
                               if is_zh else f"Remote command error: {error_output}")
            return result

        # 检查远程日志文件是否存在
        stdin, stdout, stderr = ssh.exec_command(f"test -f {remote_output} && echo exists", timeout=5)
        if "exists" not in stdout.read().decode():
            result["message"] = (
                "未生成日志文件，可能进程无文件操作" 
                if is_zh else "No log file generated, process may have no file operations"
            )
            result["success"] = True
            return result

        # 下载远程日志到本地
        sftp = ssh.open_sftp()
        sftp.get(remote_output, result["output_file"])
        sftp.close()

        with open(result["output_file"], "r") as f:
            result["errors"] = _parse_strace_errors(f.read())
        
        result["success"] = True
        perm_count = len(result["errors"]["permission_denied"])
        not_found_count = len(result["errors"]["file_not_found"])
        
        result["message"] = (
            f"远程跟踪完成（持续 {duration} 秒），共捕获 "
            f"权限不足错误 {perm_count} 个，文件找不到错误 {not_found_count} 个，"
            f"本地日志: {result['output_file']}"
            if is_zh else
            f"Remote tracking completed (duration {duration} seconds), captured "
            f"{perm_count} permission denied errors, {not_found_count} file not found errors, "
            f"local log: {result['output_file']}"
        )

    except Exception as e:
        result["message"] = (
            f"远程错误跟踪异常：{str(e)}" 
            if is_zh else f"Remote error tracking exception: {str(e)}"
        )
    finally:
        if ssh:
            ssh.close()

    return result


# ------------------------------
# 功能3：排查网络连接和通信问题
# ------------------------------
NETWORK_OPERATIONS = {
    "socket", "connect", "bind", "listen", "accept", "accept4",
    "send", "sendto", "sendmsg", "recv", "recvfrom", "recvmsg",
    "close", "shutdown", "setsockopt", "getsockopt",
    "getaddrinfo", "gethostbyname", "gethostbyname2"
}

# 网络错误识别正则
CONNECTION_REFUSED_PATTERN = re.compile(r"Connection refused|ECONNREFUSED")
TIMEOUT_PATTERN = re.compile(r"Connection timed out|ETIMEDOUT")
HOST_UNREACHABLE_PATTERN = re.compile(r"No route to host|EHOSTUNREACH")
ADDRESS_IN_USE_PATTERN = re.compile(r"Address already in use|EADDRINUSE")
NETWORK_UNREACHABLE_PATTERN = re.compile(r"Network is unreachable|ENETUNREACH")


def _parse_network_errors(log_content: str) -> Dict:
    """解析strace日志，提取网络相关错误"""
    errors = {
        "connection_refused": [], "timeout": [], "host_unreachable": [],
        "address_in_use": [], "network_unreachable": [], "other_network_errors": []
    }

    for line in log_content.splitlines():
        if any(op in line for op in NETWORK_OPERATIONS):
            if CONNECTION_REFUSED_PATTERN.search(line):
                errors["connection_refused"].append(_format_network_error(line))
            elif TIMEOUT_PATTERN.search(line):
                errors["timeout"].append(_format_network_error(line))
            elif HOST_UNREACHABLE_PATTERN.search(line):
                errors["host_unreachable"].append(_format_network_error(line))
            elif ADDRESS_IN_USE_PATTERN.search(line):
                errors["address_in_use"].append(_format_network_error(line))
            elif NETWORK_UNREACHABLE_PATTERN.search(line):
                errors["network_unreachable"].append(_format_network_error(line))
            elif "= -1" in line:
                errors["other_network_errors"].append(_format_network_error(line))

    return errors


def _format_network_error(line: str) -> Dict:
    """格式化网络错误行，提取关键信息"""
    parts = line.split(" = ")
    if len(parts) < 2:
        return {"raw_line": line, "operation": "unknown", "target": "unknown", "error": "unknown"}

    op_part, error_part = parts[0].strip(), " = ".join(parts[1:]).strip()
    op_match = re.match(r"^(\w+)", op_part)
    operation = op_match.group(1) if op_match else "unknown"
    
    target = "unknown"
    ip_match = re.search(r"inet_addr\(\"([\d.]+)\"\)", op_part)
    port_match = re.search(r"sin_port=htons\((\d+)\)", op_part)
    host_match = re.search(r"host=\"([^\" ]+)\"", op_part) or re.search(r"\"([a-zA-Z0-9.-]+\.[a-zA-Z]+)\"", op_part)
    
    if host_match:
        target = host_match.group(1)
    elif ip_match:
        target = ip_match.group(1)
    if port_match:
        target += f":{port_match.group(1)}"

    return {
        "raw_line": line, "operation": operation, "target": target, "error": error_part
    }


def _run_local_network_tracking(
    pid: int, output_file: Optional[str] = None, duration: int = 30, trace_dns: bool = True
) -> Dict:
    """本地跟踪：排查网络连接和通信问题"""
    # 根据配置获取语言
    is_zh = StraceCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    
    result = {
        "success": False, "message": "", "output_file": output_file or f"strace_network_local_{pid}.log",
        "target_pid": pid, "host": "localhost", "errors": None
    }

    validate_msg = _validate_local_process(pid)
    if validate_msg:
        result["message"] = validate_msg
        return result

    trace_ops = list(NETWORK_OPERATIONS)
    if not trace_dns:
        trace_ops = [op for op in trace_ops if op not in {"getaddrinfo", "gethostbyname", "gethostbyname2"}]

    strace_cmd = [
        "strace", "-p", str(pid), "-e", f"trace={','.join(trace_ops)}",
        "-o", result["output_file"], "-s", "4096"
    ]

    try:
        subprocess.run(["timeout", str(duration)] + strace_cmd, capture_output=True, text=True)

        if not os.path.exists(result["output_file"]):
            result["message"] = (
                "跟踪完成但未生成日志文件，可能进程无网络操作" 
                if is_zh else "Tracking completed but no log file generated, process may have no network operations"
            )
            result["success"] = True
            return result

        with open(result["output_file"], "r") as f:
            result["errors"] = _parse_network_errors(f.read())
        
        result["success"] = True
        error_counts = {k: len(v) for k, v in result["errors"].items()}
        
        result["message"] = (
            f"网络跟踪完成（{duration}秒），错误统计：\n"
            f"连接被拒绝: {error_counts['connection_refused']}，"
            f"超时: {error_counts['timeout']}，"
            f"主机不可达: {error_counts['host_unreachable']}\n"
            f"日志文件: {result['output_file']}"
            if is_zh else
            f"Network tracking completed ({duration}s), error statistics:\n"
            f"Connection refused: {error_counts['connection_refused']}, "
            f"Timeout: {error_counts['timeout']}, "
            f"Host unreachable: {error_counts['host_unreachable']}\n"
            f"Log file: {result['output_file']}"
        )

    except Exception as e:
        result["message"] = (
            f"本地网络跟踪失败：{str(e)}" 
            if is_zh else f"Local network tracking failed: {str(e)}"
        )

    return result


def _run_remote_network_tracking(
    pid: int, host: str, username: str, password: str, port: int = 22,
    output_file: Optional[str] = None, duration: int = 30, trace_dns: bool = True
) -> Dict:
    """远程跟踪：排查网络连接和通信问题"""
    # 根据配置获取语言
    is_zh = StraceCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    
    result = {
        "success": False, "message": "", "output_file": output_file or f"strace_network_remote_{pid}.log",
        "target_pid": pid, "host": host, "errors": None
    }

    ssh = _create_ssh_connection(host, port, username, password)
    if not ssh:
        result["message"] = (
            "SSH连接失败" 
            if is_zh else "SSH connection failed"
        )
        return result

    try:
        proc_msg = _validate_remote_process(ssh, pid)
        strace_msg = _check_strace_installed(ssh)
        if proc_msg or strace_msg:
            result["message"] = proc_msg or strace_msg
            return result

        remote_output = result["output_file"]
        trace_ops = list(NETWORK_OPERATIONS)
        if not trace_dns:
            trace_ops = [op for op in trace_ops if op not in {"getaddrinfo", "gethostbyname", "gethostbyname2"}]
        network_ops = ",".join(trace_ops)

        strace_cmd = f"timeout {duration} strace -p {pid} -e trace={network_ops} -o {remote_output} -s 4096"
        stdin, stdout, stderr = ssh.exec_command(strace_cmd, timeout=duration + 10)
        
        error_output = stderr.read().decode().strip()
        if error_output and "timed out" not in error_output.lower():
            result["message"] = (
                f"远程命令错误：{error_output}" 
                if is_zh else f"Remote command error: {error_output}"
            )
            return result

        stdin, stdout, stderr = ssh.exec_command(f"test -f {remote_output} && echo exists", timeout=5)
        if "exists" not in stdout.read().decode():
            result["message"] = (
                "未生成日志文件，可能进程无网络操作" 
                if is_zh else "No log file generated, process may have no network operations"
            )
            result["success"] = True
            return result

        sftp = ssh.open_sftp()
        sftp.get(remote_output, result["output_file"])
        sftp.close()

        with open(result["output_file"], "r") as f:
            result["errors"] = _parse_network_errors(f.read())
        
        result["success"] = True
        error_counts = {k: len(v) for k, v in result["errors"].items()}
        
        result["message"] = (
            f"远程网络跟踪完成（{duration}秒），错误统计：\n"
            f"连接被拒绝: {error_counts['connection_refused']}，"
            f"超时: {error_counts['timeout']}，"
            f"主机不可达: {error_counts['host_unreachable']}\n"
            f"本地日志: {result['output_file']}"
            if is_zh else
            f"Remote network tracking completed ({duration}s), error statistics:\n"
            f"Connection refused: {error_counts['connection_refused']}, "
            f"Timeout: {error_counts['timeout']}, "
            f"Host unreachable: {error_counts['host_unreachable']}\n"
            f"Local log file: {result['output_file']}"
        )

    except Exception as e:
        result["message"] = (
            f"远程网络跟踪异常：{str(e)}" 
            if is_zh else f"Remote network tracking exception: {str(e)}"
        )
    finally:
        if ssh:
            ssh.close()

    return result


# ------------------------------
# 功能4：定位进程卡顿的原因
# ------------------------------
BLOCKING_OPERATIONS = {
    "read", "write", "recv", "recvfrom", "send", "sendto",
    "accept", "connect", "select", "poll", "epoll_wait",
    "flock", "fcntl", "wait", "waitpid", "sem_wait", "pthread_mutex_lock",
    "open", "close", "stat", "fstat", "rename", "unlink"
}

DURATION_PATTERN = re.compile(r"<(\d+\.\d+)>")


def _parse_blocking_operations(log_content: str, slow_threshold: float = 0.5) -> Dict:
    """解析strace日志，识别耗时过长的阻塞操作"""
    # 根据配置获取语言
    is_zh = StraceCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    
    analysis = {
        "total_operations": 0, "slow_operations": [], "most_frequent_calls": {},
        "longest_duration": 0.0, "longest_operation": None,
        "blocking_categories": {"io": 0, "network": 0, "locking": 0, "sync": 0, "other": 0}
    }

    for line in log_content.splitlines():
        if "<" in line and ">" in line:
            duration_match = DURATION_PATTERN.search(line)
            if not duration_match:
                continue
                
            try:
                duration = float(duration_match.group(1))
            except ValueError:
                continue

            op_match = re.match(r"^<\d+\.\d+>\s*(\w+)", line)
            if not op_match:
                continue
            operation = op_match.group(1)

            if operation not in BLOCKING_OPERATIONS:
                continue

            analysis["total_operations"] += 1
            analysis["most_frequent_calls"][operation] = analysis["most_frequent_calls"].get(operation, 0) + 1

            # 分类统计
            if operation in {"read", "write", "open", "close", "stat", "rename", "unlink"}:
                analysis["blocking_categories"]["io"] += 1
            elif operation in {"recv", "recvfrom", "send", "sendto", "accept", "connect"}:
                analysis["blocking_categories"]["network"] += 1
            elif operation in {"flock", "fcntl", "pthread_mutex_lock"}:
                analysis["blocking_categories"]["locking"] += 1
            elif operation in {"wait", "waitpid", "sem_wait"}:
                analysis["blocking_categories"]["sync"] += 1
            else:
                analysis["blocking_categories"]["other"] += 1

            # 记录慢操作
            if duration >= slow_threshold:
                detail = _extract_operation_detail(line, operation)
                slow_op = {
                    "duration": duration, "operation": operation, "detail": detail, "raw_line": line
                }
                analysis["slow_operations"].append(slow_op)

                if duration > analysis["longest_duration"]:
                    analysis["longest_duration"] = duration
                    analysis["longest_operation"] = slow_op

    # 排序
    analysis["slow_operations"].sort(key=lambda x: x["duration"], reverse=True)
    analysis["most_frequent_calls"] = dict(
        sorted(analysis["most_frequent_calls"].items(), key=lambda x: x[1], reverse=True)
    )

    return analysis


def _extract_operation_detail(line: str, operation: str) -> str:
    """提取操作的关键详情"""
    # 根据配置获取语言
    is_zh = StraceCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    
    line_clean = re.sub(r"^<\d+\.\d+>\s*", "", line)
    param_match = re.search(r"\((.*?)\)", line_clean)
    if not param_match:
        return "无法解析详情" if is_zh else "Unable to parse details"
    
    params = param_match.group(1)
    if operation in {"open", "read", "write", "close"}:
        path_match = re.search(r'"([^"]+)"', params)
        return path_match.group(1) if path_match else params
    elif operation in {"connect", "sendto", "recvfrom"}:
        addr_match = re.search(r"(inet_addr\(\"[^\"]+\"|host=\"[^\"]+\")", params)
        port_match = re.search(r"sin_port=htons\((\d+)\)", params)
        addr = addr_match.group(1) if addr_match else ("未知地址" if is_zh else "Unknown address")
        port = f":{port_match.group(1)}" if port_match else ""
        return f"{addr}{port}"
    else:
        return params[:50] + ("..." if len(params) > 50 else "")


def _run_local_freeze_tracking(
    pid: int, output_file: Optional[str] = None, duration: int = 30, slow_threshold: float = 0.5
) -> Dict:
    """本地跟踪：定位进程卡顿原因"""
    # 根据配置获取语言
    is_zh = StraceCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    
    result = {
        "success": False, "message": "", "output_file": output_file or f"strace_freeze_local_{pid}.log",
        "target_pid": pid, "host": "localhost", "analysis": None
    }

    validate_msg = _validate_local_process(pid)
    if validate_msg:
        result["message"] = validate_msg
        return result

    strace_cmd = [
        "strace", "-p", str(pid), "-T", "-tt",
        "-e", f"trace={','.join(BLOCKING_OPERATIONS)}",
        "-o", result["output_file"], "-s", "2048"
    ]

    try:
        subprocess.run(["timeout", str(duration)] + strace_cmd, capture_output=True, text=True)

        if not os.path.exists(result["output_file"]):
            result["message"] = (
                "跟踪完成但未生成日志文件，可能进程无明显阻塞操作" 
                if is_zh else "Tracking completed but no log file generated, process may have no significant blocking operations"
            )
            result["success"] = True
            return result

        with open(result["output_file"], "r") as f:
            result["analysis"] = _parse_blocking_operations(f.read(), slow_threshold)
        
        result["success"] = True
        analysis = result["analysis"]
        
        if analysis["most_frequent_calls"]:
            most_freq_op, most_freq_count = list(analysis["most_frequent_calls"].items())[0]
        else:
            most_freq_op, most_freq_count = ("无", 0) if is_zh else ("None", 0)
        
        result["message"] = (
            f"卡顿跟踪完成（{duration}秒），分析结果：\n"
            f"总阻塞操作: {analysis['total_operations']} 次，"
            f"慢操作({slow_threshold}秒以上): {len(analysis['slow_operations'])} 次\n"
            f"最长耗时操作: {analysis['longest_duration']:.3f}秒 ({analysis['longest_operation']['operation']} {analysis['longest_operation']['detail']})\n"
            f"最频繁操作: {most_freq_op}（{most_freq_count}次）\n"
            f"日志文件: {result['output_file']}"
            if is_zh else
            f"Freeze tracking completed ({duration}s), analysis results:\n"
            f"Total blocking operations: {analysis['total_operations']}, "
            f"Slow operations (over {slow_threshold}s): {len(analysis['slow_operations'])}\n"
            f"Longest operation: {analysis['longest_duration']:.3f}s ({analysis['longest_operation']['operation']} {analysis['longest_operation']['detail']})\n"
            f"Most frequent operation: {most_freq_op} ({most_freq_count} times)\n"
            f"Log file: {result['output_file']}"
        )

    except Exception as e:
        result["message"] = (
            f"本地卡顿跟踪失败：{str(e)}" 
            if is_zh else f"Local freeze tracking failed: {str(e)}"
        )

    return result


def _run_remote_freeze_tracking(
    pid: int, host: str, username: str, password: str, port: int = 22,
    output_file: Optional[str] = None, duration: int = 30, slow_threshold: float = 0.5
) -> Dict:
    """远程跟踪：定位进程卡顿原因"""
    # 根据配置获取语言
    is_zh = StraceCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    
    result = {
        "success": False, "message": "", "output_file": output_file or f"strace_freeze_remote_{pid}.log",
        "target_pid": pid, "host": host, "analysis": None
    }

    ssh = _create_ssh_connection(host, port, username, password)
    if not ssh:
        result["message"] = (
            "SSH连接失败" 
            if is_zh else "SSH connection failed"
        )
        return result

    try:
        proc_msg = _validate_remote_process(ssh, pid)
        strace_msg = _check_strace_installed(ssh)
        if proc_msg or strace_msg:
            result["message"] = proc_msg or strace_msg
            return result

        remote_output = result["output_file"]
        blocking_ops = ",".join(BLOCKING_OPERATIONS)
        strace_cmd = f"timeout {duration} strace -p {pid} -T -tt -e trace={blocking_ops} -o {remote_output} -s 2048"
        
        stdin, stdout, stderr = ssh.exec_command(strace_cmd, timeout=duration + 10)
        error_output = stderr.read().decode().strip()
        if error_output and "timed out" not in error_output.lower():
            result["message"] = (
                f"远程命令错误：{error_output}" 
                if is_zh else f"Remote command error: {error_output}"
            )
            return result

        stdin, stdout, stderr = ssh.exec_command(f"test -f {remote_output} && echo exists", timeout=5)
        if "exists" not in stdout.read().decode():
            result["message"] = (
                "未生成日志文件，可能进程无明显阻塞操作" 
                if is_zh else "No log file generated, process may have no significant blocking operations"
            )
            result["success"] = True
            return result

        sftp = ssh.open_sftp()
        sftp.get(remote_output, result["output_file"])
        sftp.close()

        with open(result["output_file"], "r") as f:
            result["analysis"] = _parse_blocking_operations(f.read(), slow_threshold)
        
        result["success"] = True
        analysis = result["analysis"]
        
        if analysis["most_frequent_calls"]:
            most_freq_op, most_freq_count = list(analysis["most_frequent_calls"].items())[0]
        else:
            most_freq_op, most_freq_count = ("无", 0) if is_zh else ("None", 0)
        
        result["message"] = (
            f"远程卡顿跟踪完成（{duration}秒），分析结果：\n"
            f"总阻塞操作: {analysis['total_operations']} 次，"
            f"慢操作({slow_threshold}秒以上): {len(analysis['slow_operations'])} 次\n"
            f"最长耗时操作: {analysis['longest_duration']:.3f}秒 ({analysis['longest_operation']['operation']} {analysis['longest_operation']['detail']})\n"
            f"最频繁操作: {most_freq_op}（{most_freq_count}次）\n"
            f"本地日志: {result['output_file']}"
            if is_zh else
            f"Remote freeze tracking completed ({duration}s), analysis results:\n"
            f"Total blocking operations: {analysis['total_operations']}, "
            f"Slow operations (over {slow_threshold}s): {len(analysis['slow_operations'])}\n"
            f"Longest operation: {analysis['longest_duration']:.3f}s ({analysis['longest_operation']['operation']} {analysis['longest_operation']['detail']})\n"
            f"Most frequent operation: {most_freq_op} ({most_freq_count} times)\n"
            f"Local log file: {result['output_file']}"
        )

    except Exception as e:
        result["message"] = (
            f"远程卡顿跟踪异常：{str(e)}" 
            if is_zh else f"Remote freeze tracking exception: {str(e)}"
        )
    finally:
        if ssh:
            ssh.close()
    
    return result