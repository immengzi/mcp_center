import os
import subprocess
from typing import Dict, Optional
from mcp.server import FastMCP
import paramiko
from config.private.strace.config_loader import StraceCommandConfig
from config.public.base_config_loader import LanguageEnum
from servers.strace.src.base import _parse_freeze_log, _parse_network_log, _parse_strace_log

def get_language_config() -> bool:
    """获取语言配置：True=中文，False=英文"""
    return StraceCommandConfig().get_config().public_config.language == LanguageEnum.ZH


mcp = FastMCP("strace MCP Server", host="0.0.0.0", port=StraceCommandConfig().get_config().private_config.port)

@mcp.tool(
    name="strace_track_file_process" if get_language_config() else "strace_track_file_process",
    description="""
    使用strace跟踪进程的文件操作和运行状态（支持本地/远程）
    1. 输入值如下：
        - pid: 目标进程PID，必填项
        - host: 远程主机IP/hostname，不提供则表示本地跟踪
        - port: SSH端口，默认22，远程连接时使用
        - username: SSH用户名，远程跟踪时必填
        - password: SSH密码，远程跟踪时必填
        - output_file: 跟踪日志文件路径，可选
        - follow_children: 是否跟踪子进程，默认False
        - duration: 跟踪时长（秒），可选，不填则持续跟踪
    2. 返回值为包含跟踪结果的字典，包含以下键
        - success: 布尔值，表示跟踪是否成功启动
        - message: 跟踪结果消息（含终端原始错误）
        - strace_pid: strace进程ID，成功时返回
        - output_file: 跟踪日志文件路径
        - target_pid: 目标进程PID
        - host: 跟踪的主机
    """
    if get_language_config() else
    """
    Use strace to track file operations and running status of processes (supports local/remote)
    1. Input values are as follows:
        - pid: Target process PID, required
        - host: Remote host IP/hostname, local tracking if not provided
        - port: SSH port, default 22, used for remote connection
        - username: SSH username, required for remote tracking
        - password: SSH password, required for remote tracking
        - output_file: Trace log file path, optional
        - follow_children: Whether to track child processes, default False
        - duration: Tracking duration (seconds), optional, continuous tracking if not specified
    2. The return value is a dictionary containing tracking results with the following keys
        - success: Boolean indicating whether tracking started successfully
        - message: Tracking result message (including original terminal error)
        - strace_pid: strace process ID, returned on success
        - output_file: Trace log file path
        - target_pid: Target process PID
        - host: Host being tracked
    """
)
def strace_track_file_process(
    pid: int,
    host: Optional[str] = None,
    port: int = 22,
    username: Optional[str] = None,
    password: Optional[str] = None,
    output_file: Optional[str] = None,
    follow_children: bool = False,
    duration: Optional[int] = None
) -> Dict:
    is_zh = get_language_config()
    target_host = host or "localhost"
    # 初始化返回结果（固定结构）
    result = {
        "success": False,
        "message": "",
        "strace_pid": None,
        "output_file": output_file,
        "target_pid": pid,
        "host": target_host
    }

    try:
        # 1. 仅保留PID基础校验（核心必选参数）
        if not isinstance(pid, int) or pid <= 0:
            result["message"] = "PID必须是正整数" if is_zh else "PID must be a positive integer"
            return result

        # 2. 构建strace命令（本地/远程通用，简化参数拼接）
        strace_cmd = ["strace", "-p", str(pid), "-e", "trace=file"]
        if follow_children:
            strace_cmd.append("-f")
        if output_file:
            strace_cmd.extend(["-o", output_file])
        if duration:
            strace_cmd = ["timeout", str(duration)] + strace_cmd

        # 3. 本地跟踪：无host则走本地逻辑，直接执行命令
        if not host:
            try:
                # 本地后台启动+获取strace PID（用shell执行后台命令）
                output = subprocess.check_output(
                    f"nohup {' '.join(strace_cmd)} > /dev/null 2>&1 & echo $!",
                    shell=True,
                    text=True,
                    stderr=subprocess.STDOUT
                )
                strace_pid = int(output.strip())
                # 填充成功结果
                result["success"] = True
                result["strace_pid"] = strace_pid
                base_msg = f"本地strace跟踪启动成功（PID：{strace_pid}），目标进程：{pid}" if is_zh else f"Local strace tracking started (PID: {strace_pid}), target process: {pid}"
                result["message"] = base_msg + (f"，日志文件：{output_file}" if output_file else "")
                return result
            except subprocess.CalledProcessError as e:
                # 直接返回终端原始错误（如strace未安装、进程不存在）
                result["message"] = f"本地跟踪失败：{e.output.strip()}" if is_zh else f"Local tracking failed: {e.output.strip()}"
                return result

        # 4. 远程跟踪：有host则走远程逻辑（取消单独参数校验，错误由终端返回）
        else:
            # 4.1 匹配远程配置（核心逻辑保留，简化赋值）
            matched_config = None
            for cfg in StraceCommandConfig().get_config().public_config.remote_hosts:
                if host in [cfg.name, cfg.host]:
                    matched_config = cfg
                    break

            # 4.2 整理连接信息（配置优先，无配置则用传入参数）
            remote_host = matched_config.host if matched_config else host
            remote_port = matched_config.port if (matched_config and matched_config.port) else port
            remote_user = matched_config.username if matched_config else username
            remote_pwd = matched_config.password if matched_config else password

            # 4.3 执行远程操作（直接连，缺参数/认证错由SSH返回）
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                # 连接SSH（缺用户/密码会直接抛异常）
                ssh.connect(
                    hostname=remote_host,
                    port=remote_port,
                    username=remote_user,
                    password=remote_pwd,
                    timeout=10
                )
                # 远程后台启动strace并获取PID
                remote_cmd = f"nohup {' '.join(strace_cmd)} > /dev/null 2>&1 & echo $!"
                stdin, stdout, stderr = ssh.exec_command(remote_cmd)
                stderr_msg = stderr.read().decode().strip()
                stdout_msg = stdout.read().decode().strip()

                # 处理远程结果：有错误返错误，无错误解析PID
                if stderr_msg:
                    result["message"] = f"远程跟踪失败：{stderr_msg}" if is_zh else f"Remote tracking failed: {stderr_msg}"
                elif stdout_msg.isdigit():
                    strace_pid = int(stdout_msg)
                    result["success"] = True
                    result["strace_pid"] = strace_pid
                    base_msg = f"远程strace跟踪启动成功（主机：{remote_host}，PID：{strace_pid}），目标进程：{pid}" if is_zh else f"Remote strace tracking started (host: {remote_host}, PID: {strace_pid}), target process: {pid}"
                    result["message"] = base_msg + (f"，日志文件：{output_file}" if output_file else "")
                else:
                    result["message"] = f"远程跟踪失败：无法获取strace PID，返回：{stdout_msg}" if is_zh else f"Remote tracking failed: Cannot get strace PID, return: {stdout_msg}"
                return result
            except Exception as e:
                # 直接返回SSH连接/执行错误（如缺密码、认证失败）
                result["message"] = f"远程操作失败：{str(e)}" if is_zh else f"Remote operation failed: {str(e)}"
                return result
            finally:
                ssh.close()

    except Exception as e:
        # 全局异常直接返回（简化处理）
        result["message"] = f"操作异常：{str(e)}" if is_zh else f"Operation exception: {str(e)}"
        return result
        
        
@mcp.tool(
    name="strace_check_permission_file" if get_language_config() else "strace_check_permission_file",
    description="""
    使用strace排查进程的'权限不足'和'文件找不到'问题（支持本地/远程）
    1. 输入值如下：
        - pid: 目标进程PID，必填项
        - host: 远程主机IP/hostname，不提供则表示本地排查
        - port: SSH端口，默认22，远程连接时使用
        - username: SSH用户名，远程排查时必填
        - password: SSH密码，远程排查时必填
        - output_file: 跟踪日志路径，可选
        - duration: 跟踪时长（秒），默认30
    2. 返回值为包含排查结果的字典，包含以下键
        - success: 布尔值，表示排查是否成功完成
        - message: 排查结果消息
        - output_file: 跟踪日志文件路径
        - target_pid: 目标进程PID
        - host: 排查的主机
        - errors: 错误统计字典，包含权限不足和文件找不到错误详情
    """
    if get_language_config() else
    """
    Use strace to troubleshoot 'permission denied' and 'file not found' issues of processes (supports local/remote)
    1. Input values are as follows:
        - pid: Target process PID, required
        - host: Remote host IP/hostname, local troubleshooting if not provided
        - port: SSH port, default 22, used for remote connection
        - username: SSH username, required for remote troubleshooting
        - password: SSH password, required for remote troubleshooting
        - output_file: Trace log path, optional
        - duration: Tracking duration (seconds), default 30
    2. The return value is a dictionary containing troubleshooting results with the following keys
        - success: Boolean indicating whether troubleshooting completed successfully
        - message: Troubleshooting result message
        - output_file: Trace log file path
        - target_pid: Target process PID
        - host: Host being troubleshooted
        - errors: Error statistics dictionary, including details of permission denied and file not found errors
    """
)
def strace_check_permission_file(
    pid: int, host: Optional[str] = None, port: int = 22,
    username: Optional[str] = None, password: Optional[str] = None,
    output_file: Optional[str] = None, duration: int = 30
) -> Dict:
    is_zh = get_language_config()
    target_host = host or "localhost"

    # 初始化返回结果（严格匹配模板定义的结构，无冗余字段）
    result = {
        "success": False,
        "message": "",
        "output_file": output_file,
        "target_pid": pid,
        "host": target_host,
        "errors": {
            "permission_denied": {"count": 0, "files": []},  # 权限不足错误
            "file_not_found": {"count": 0, "files": []}      # 文件找不到错误
        }
    }

    try:
        # 1. 仅保留核心参数校验（避免过度校验，其他错误由终端返回）
        if not isinstance(pid, int) or pid <= 0:
            result["message"] = "PID必须是正整数" if is_zh else "PID must be a positive integer"
            return result
        if not isinstance(duration, int) or duration <= 0:
            result["message"] = "跟踪时长必须是正整数（秒）" if is_zh else "Tracking duration must be a positive integer (seconds)"
            return result

        # 2. 处理日志文件路径（无则自动生成默认路径）
        if not output_file:
            default_filename = f"strace_perm_check_{pid}_{target_host.replace('.', '_')}.log"
            output_file = f"/tmp/{default_filename}"  # 本地/远程统一默认路径
            result["output_file"] = output_file

        # 3. 构建strace命令（核心：仅跟踪文件操作+记录错误）
        # -e trace=file：只跟踪文件相关系统调用；-e write=1：输出错误信息
        strace_cmd = [
            "strace", "-p", str(pid), "-e", "trace=file", "-e", "write=1",
            "-o", output_file, "timeout", str(duration)
        ]

        # 4. 本地排查逻辑（直接执行+解析日志）
        if not host:
            # 执行strace跟踪（阻塞到时长结束或进程退出）
            try:
                subprocess.run(
                    strace_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )
            except subprocess.CalledProcessError as e:
                # 忽略timeout正常退出（返回码124），其他错误返回终端信息
                if e.returncode != 124:
                    result["message"] = f"本地排查失败：{e.stderr.strip()}" if is_zh else f"Local troubleshooting failed: {e.stderr.strip()}"
                    return result

            # 解析日志文件，统计错误
            result["errors"] = _parse_strace_log(output_file)
            result["success"] = True
            result[
                "message"] = f"本地排查完成（时长：{duration}秒），日志文件：{output_file}" if is_zh else f"Local troubleshooting completed (duration: {duration}s), log file: {output_file}"
            return result

        # 5. 远程排查逻辑（配置优先+执行+拉取日志解析）
        else:
            # 5.1 匹配远程配置（核心逻辑保留，简化赋值）
            matched_config = None
            for cfg in StraceCommandConfig().get_config().public_config.remote_hosts:
                if host in [cfg.name, cfg.host]:
                    matched_config = cfg
                    break
            # 整理连接信息（配置优先，无配置用传入参数）
            remote_conn = {
                "host": matched_config.host if matched_config else host,
                "port": matched_config.port if (matched_config and matched_config.port) else port,
                "user": matched_config.username if matched_config else username,
                "pwd": matched_config.password if matched_config else password
            }

            # 5.2 建立SSH连接并执行远程strace
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                # 连接SSH（缺参数/认证错直接抛异常）
                ssh.connect(
                    hostname=remote_conn["host"],
                    port=remote_conn["port"],
                    username=remote_conn["user"],
                    password=remote_conn["pwd"],
                    timeout=10
                )

                # 执行远程strace命令（阻塞到完成）
                remote_cmd = " ".join(strace_cmd)
                stdin, stdout, stderr = ssh.exec_command(remote_cmd)
                stderr_msg = stderr.read().decode().strip()
                exit_code = stdout.channel.recv_exit_status()

                # 处理远程执行错误（忽略timeout正常退出码124）
                if exit_code != 0 and exit_code != 124 and stderr_msg:
                    result["message"] = f"远程排查失败：{stderr_msg}" if is_zh else f"Remote troubleshooting failed: {stderr_msg}"
                    return result

                # 拉取远程日志文件到本地临时路径（用于解析）
                local_temp_log = f"/tmp/remote_strace_{pid}_{remote_conn['host'].replace('.', '_')}.log"
                sftp = ssh.open_sftp()
                sftp.get(remote_conn["host"], local_temp_log)  # 从远程拉取日志
                sftp.close()

                # 解析拉取的日志，统计错误
                result["errors"] = _parse_strace_log(local_temp_log)
                os.remove(local_temp_log)  # 解析后删除本地临时文件

                # 填充成功结果
                result["success"] = True
                result[
                    "message"] = f"远程排查完成（主机：{remote_conn['host']}，时长：{duration}秒），远程日志文件：{output_file}" if is_zh else f"Remote troubleshooting completed (host: {remote_conn['host']}, duration: {duration}s), remote log file: {output_file}"
                return result

            except Exception as e:
                # 直接返回SSH连接/执行错误
                result["message"] = f"远程操作失败：{str(e)}" if is_zh else f"Remote operation failed: {str(e)}"
                return result
            finally:
                ssh.close()

    except Exception as e:
        # 全局异常直接返回（简化处理）
        result["message"] = f"操作异常：{str(e)}" if is_zh else f"Operation exception: {str(e)}"
        return result


@mcp.tool(
    name="strace_check_network" if get_language_config() else "strace_check_network",
    description="""
    使用strace排查进程的网络问题（连接失败、超时等），支持本地/远程
    1. 输入值如下：
        - pid: 目标进程PID，必填项
        - host: 远程主机IP/hostname，不提供则表示本地排查
        - port: SSH端口，默认22，远程连接时使用
        - username: SSH用户名，远程排查时必填
        - password: SSH密码，远程排查时必填
        - output_file: 跟踪日志路径，可选
        - duration: 跟踪时长（秒），默认30
        - trace_dns: 是否跟踪DNS相关调用，默认True
    2. 返回值为包含排查结果的字典，包含以下键
        - success: 布尔值，表示排查是否成功完成
        - message: 排查结果消息
        - output_file: 跟踪日志文件路径
        - target_pid: 目标进程PID
        - host: 排查的主机
        - errors: 网络错误统计字典，包含连接被拒绝、超时等错误详情
    """
    if get_language_config() else
    """
    Use strace to troubleshoot process network issues (connection failures, timeouts, etc.), supporting local/remote
    1. Input values are as follows:
        - pid: Target process PID, required
        - host: Remote host IP/hostname, local troubleshooting if not provided
        - port: SSH port, default 22, used for remote connection
        - username: SSH username, required for remote troubleshooting
        - password: SSH password, required for remote troubleshooting
        - output_file: Trace log path, optional
        - duration: Tracking duration (seconds), default 30
        - trace_dns: Whether to track DNS-related calls, default True
    2. The return value is a dictionary containing troubleshooting results with the following keys
        - success: Boolean indicating whether troubleshooting completed successfully
        - message: Troubleshooting result message
        - output_file: Trace log file path
        - target_pid: Target process PID
        - host: Host being troubleshooted
        - errors: Network error statistics dictionary, including details of connection refused, timeout and other errors
    """
)
def strace_check_network(
    pid: int, host: Optional[str] = None, port: int = 22,
    username: Optional[str] = None, password: Optional[str] = None,
    output_file: Optional[str] = None, duration: int = 30, trace_dns: bool = True
) -> Dict:
    is_zh = get_language_config()
    target_host = host or "localhost"

    # 初始化返回结果：严格匹配模板定义的结构，包含所有必填键
    result = {
        "success": False,
        "message": "",
        "output_file": output_file,
        "target_pid": pid,
        "host": target_host,
        "errors": {
            "connection_refused": {"count": 0, "details": []},  # 连接被拒绝
            "connection_timeout": {"count": 0, "details": []},  # 连接超时
            "dns_failure": {"count": 0, "details": []},         # DNS解析失败
            "other_network_errors": {"count": 0, "details": []}  # 其他网络错误
        }
    }

    try:
        # 1. 核心参数校验：仅保留必选参数的基础判断（其他错误由终端返回）
        if not isinstance(pid, int) or pid <= 0:
            result["message"] = "PID必须是正整数" if is_zh else "PID must be a positive integer"
            return result
        if not isinstance(duration, int) or duration <= 0:
            result["message"] = "跟踪时长必须是正整数（秒）" if is_zh else "Tracking duration must be a positive integer (seconds)"
            return result

        # 2. 日志文件处理：无路径时自动生成默认路径（本地/远程统一）
        if not output_file:
            default_filename = f"strace_net_check_{pid}_{target_host.replace('.', '_')}.log"
            output_file = f"/tmp/{default_filename}"
            result["output_file"] = output_file

        # 3. 构建strace命令：聚焦网络相关系统调用，按需添加DNS跟踪
        # 核心跟踪调用：socket/connect/sendto/recvfrom（网络基础操作）
        trace_calls = "trace=socket,connect,sendto,recvfrom,bind,listen,accept"
        if trace_dns:
            trace_calls += ",getaddrinfo,gethostbyname,gethostbyname2"  # 追加DNS调用

        strace_cmd = [
            "strace", "-p", str(pid), "-e", trace_calls,  # 仅跟踪网络相关调用
            "-e", "write=1",  # 强制输出错误信息
            "-o", output_file,  # 日志写入文件
            "timeout", str(duration)  # 时长控制
        ]

        # 4. 本地排查逻辑：直接执行+解析日志
        if not host:
            try:
                # 执行strace：阻塞到时长结束（timeout返回124为正常退出）
                subprocess.run(
                    strace_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )
            except subprocess.CalledProcessError as e:
                # 忽略timeout正常退出，其他错误返回终端原始信息
                if e.returncode != 124:
                    result["message"] = f"本地排查失败：{e.stderr.strip()}" if is_zh else f"Local troubleshooting failed: {e.stderr.strip()}"
                    return result

            # 解析日志，统计网络错误
            result["errors"] = _parse_network_log(output_file)
            result["success"] = True
            result[
                "message"] = f"本地网络排查完成（时长：{duration}秒），日志：{output_file}" if is_zh else f"Local network troubleshooting completed (duration: {duration}s), log: {output_file}"
            return result

        # 5. 远程排查逻辑：配置优先+SSH执行+日志拉取解析
        else:
            # 5.1 匹配远程配置（保留核心逻辑，简化判断）
            matched_config = None
            for cfg in StraceCommandConfig().get_config().public_config.remote_hosts:
                if host in [cfg.name, cfg.host]:
                    matched_config = cfg
                    break

            # 5.2 整理连接信息：配置优先，无配置则用传入参数
            remote_conn = {
                "host": matched_config.host if matched_config else host,
                "port": matched_config.port if (matched_config and matched_config.port) else port,
                "user": matched_config.username if matched_config else username,
                "pwd": matched_config.password if matched_config else password
            }

            # 5.3 SSH执行远程排查
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                # 建立SSH连接（缺参数/认证错直接抛异常）
                ssh.connect(
                    hostname=remote_conn["host"],
                    port=remote_conn["port"],
                    username=remote_conn["user"],
                    password=remote_conn["pwd"],
                    timeout=10
                )

                # 执行远程strace命令
                remote_cmd = " ".join(strace_cmd)
                stdin, stdout, stderr = ssh.exec_command(remote_cmd)
                stderr_msg = stderr.read().decode().strip()
                exit_code = stdout.channel.recv_exit_status()

                # 处理执行错误：忽略timeout正常退出
                if exit_code != 0 and exit_code != 124 and stderr_msg:
                    result["message"] = f"远程排查失败：{stderr_msg}" if is_zh else f"Remote troubleshooting failed: {stderr_msg}"
                    return result

                # 拉取远程日志到本地临时路径（用于解析）
                local_temp_log = f"/tmp/remote_strace_net_{pid}_{remote_conn['host'].replace('.', '_')}.log"
                sftp = ssh.open_sftp()
                sftp.get(output_file, local_temp_log)  # 从远程拉取日志文件
                sftp.close()

                # 解析日志并统计错误，解析后删除临时文件
                result["errors"] = _parse_network_log(local_temp_log)
                os.remove(local_temp_log)

                # 填充成功结果
                result["success"] = True
                result[
                    "message"] = f"远程网络排查完成（主机：{remote_conn['host']}，时长：{duration}秒），远程日志：{output_file}" if is_zh else f"Remote network troubleshooting completed (host: {remote_conn['host']}, duration: {duration}s), remote log: {output_file}"
                return result

            except Exception as e:
                # 直接返回SSH相关错误（如缺密码、连接超时）
                result["message"] = f"远程操作失败：{str(e)}" if is_zh else f"Remote operation failed: {str(e)}"
                return result
            finally:
                ssh.close()

    except Exception as e:
        # 全局异常：直接返回原始错误信息
        result["message"] = f"操作异常：{str(e)}" if is_zh else f"Operation exception: {str(e)}"
        return result


@mcp.tool(
    name="strace_locate_freeze"
    if get_language_config() else "strace_locate_freeze",
    description="""
    使用strace定位进程卡顿原因（如IO阻塞、锁等待等），支持本地/远程
    1. 输入值如下：
        - pid: 目标进程PID，必填项
        - host: 远程主机IP/hostname，不提供则表示本地定位
        - port: SSH端口，默认22，远程连接时使用
        - username: SSH用户名，远程定位时必填
        - password: SSH密码，远程定位时必填
        - output_file: 跟踪日志路径，可选
        - duration: 跟踪时长（秒），默认30
        - slow_threshold: 慢操作阈值（秒），默认0.5
    2. 返回值为包含定位结果的字典，包含以下键
        - success: 布尔值，表示定位是否成功完成
        - message: 定位结果消息
        - output_file: 跟踪日志文件路径
        - target_pid: 目标进程PID
        - host: 定位的主机
        - analysis: 卡顿分析字典，包含慢操作、阻塞分类等详细信息
    """
    if get_language_config() else
    """
    Use strace to locate the cause of process freeze (such as IO blocking, lock waiting, etc.), supporting local/remote
    1. Input values are as follows:
        - pid: Target process PID, required
        - host: Remote host IP/hostname, local location if not provided
        - port: SSH port, default 22, used for remote connection
        - username: SSH username, required for remote location
        - password: SSH password, required for remote location
        - output_file: Trace log path, optional
        - duration: Tracking duration (seconds), default 30
        - slow_threshold: Slow operation threshold (seconds), default 0.5
    2. The return value is a dictionary containing location results with the following keys
        - success: Boolean indicating whether location completed successfully
        - message: Location result message
        - output_file: Trace log file path
        - target_pid: Target process PID
        - host: Host being located
        - analysis: Freeze analysis dictionary, including details such as slow operations and blocking categories
    """
)
def strace_locate_freeze(
    pid: int, host: Optional[str] = None, port: int = 22,
    username: Optional[str] = None, password: Optional[str] = None,
    output_file: Optional[str] = None, duration: int = 30, slow_threshold: float = 0.5
) -> Dict:
    is_zh = get_language_config()
    target_host = host or "localhost"

    # 初始化返回结果：严格匹配模板定义的结构，包含所有必填键
    result = {
        "success": False,
        "message": "",
        "output_file": output_file,
        "target_pid": pid,
        "host": target_host,
        "analysis": {
            "slow_operations": {"count": 0, "details": []},  # 慢操作（超阈值）
            "blocking_categories": {  # 阻塞类型分类统计
                "io_block": {"count": 0, "details": []},    # IO阻塞（文件/网络）
                "lock_wait": {"count": 0, "details": []},   # 锁等待（如pthread_mutex_lock）
                "syscall_block": {"count": 0, "details": []}  # 系统调用阻塞（其他）
            },
            "total_syscalls": 0  # 总跟踪系统调用数
        }
    }

    try:
        # 1. 核心参数校验：仅保留必选参数的基础判断（其他错误由终端返回）
        if not isinstance(pid, int) or pid <= 0:
            result["message"] = "PID必须是正整数" if is_zh else "PID must be a positive integer"
            return result
        if not isinstance(duration, int) or duration <= 0:
            result["message"] = "跟踪时长必须是正整数（秒）" if is_zh else "Tracking duration must be a positive integer (seconds)"
            return result
        if not isinstance(slow_threshold, (int, float)) or slow_threshold <= 0:
            result[
                "message"] = "慢操作阈值必须是正数（秒）" if is_zh else "Slow operation threshold must be a positive number (seconds)"
            return result

        # 2. 日志文件处理：无路径时自动生成默认路径（本地/远程统一）
        if not output_file:
            default_filename = f"strace_freeze_{pid}_{target_host.replace('.', '_')}.log"
            output_file = f"/tmp/{default_filename}"
            result["output_file"] = output_file

        # 3. 构建strace命令：关键添加时间戳（-t）和系统调用耗时（-r），用于卡顿分析
        strace_cmd = [
            "strace", "-p", str(pid),
            "-t",  # 记录命令执行时间（格式：HH:MM:SS）
            "-r",  # 记录系统调用耗时（单位：秒，精确到微秒）
            "-e", "trace=all",  # 跟踪所有系统调用（卡顿可能来自任意调用）
            "-o", output_file,  # 日志写入文件
            "timeout", str(duration)  # 时长控制
        ]

        # 4. 本地定位逻辑：直接执行+解析日志（聚焦耗时与阻塞）
        if not host:
            try:
                # 执行strace：阻塞到时长结束（timeout返回124为正常退出）
                subprocess.run(
                    strace_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )
            except subprocess.CalledProcessError as e:
                # 忽略timeout正常退出，其他错误返回终端原始信息
                if e.returncode != 124:
                    result["message"] = f"本地定位失败：{e.stderr.strip()}" if is_zh else f"Local location failed: {e.stderr.strip()}"
                    return result

            # 解析日志：统计慢操作和阻塞类型
            result["analysis"] = _parse_freeze_log(output_file, slow_threshold)
            result["success"] = True
            result[
                "message"] = f"本地卡顿定位完成（时长：{duration}秒，阈值：{slow_threshold}秒），日志：{output_file}" if is_zh else f"Local freeze location completed (duration: {duration}s, threshold: {slow_threshold}s), log: {output_file}"
            return result

        # 5. 远程定位逻辑：配置优先+SSH执行+日志拉取解析
        else:
            # 5.1 匹配远程配置（保留核心逻辑，简化判断）
            matched_config = None
            for cfg in StraceCommandConfig().get_config().public_config.remote_hosts:
                if host in [cfg.name, cfg.host]:
                    matched_config = cfg
                    break

            # 5.2 整理连接信息：配置优先，无配置则用传入参数
            remote_conn = {
                "host": matched_config.host if matched_config else host,
                "port": matched_config.port if (matched_config and matched_config.port) else port,
                "user": matched_config.username if matched_config else username,
                "pwd": matched_config.password if matched_config else password
            }

            # 5.3 SSH执行远程定位
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                # 建立SSH连接（缺参数/认证错直接抛异常）
                ssh.connect(
                    hostname=remote_conn["host"],
                    port=remote_conn["port"],
                    username=remote_conn["user"],
                    password=remote_conn["pwd"],
                    timeout=10
                )

                # 执行远程strace命令
                remote_cmd = " ".join(strace_cmd)
                stdin, stdout, stderr = ssh.exec_command(remote_cmd)
                stderr_msg = stderr.read().decode().strip()
                exit_code = stdout.channel.recv_exit_status()

                # 处理执行错误：忽略timeout正常退出
                if exit_code != 0 and exit_code != 124 and stderr_msg:
                    result["message"] = f"远程定位失败：{stderr_msg}" if is_zh else f"Remote location failed: {stderr_msg}"
                    return result

                # 拉取远程日志到本地临时路径（用于解析）
                local_temp_log = f"/tmp/remote_strace_freeze_{pid}_{remote_conn['host'].replace('.', '_')}.log"
                sftp = ssh.open_sftp()
                sftp.get(output_file, local_temp_log)  # 从远程拉取日志文件
                sftp.close()

                # 解析日志并统计卡顿信息，解析后删除临时文件
                result["analysis"] = _parse_freeze_log(local_temp_log, slow_threshold)
                os.remove(local_temp_log)

                # 填充成功结果
                result["success"] = True
                result[
                    "message"] = f"远程卡顿定位完成（主机：{remote_conn['host']}，时长：{duration}秒，阈值：{slow_threshold}秒），远程日志：{output_file}" if is_zh else f"Remote freeze location completed (host: {remote_conn['host']}, duration: {duration}s, threshold: {slow_threshold}s), remote log: {output_file}"
                return result

            except Exception as e:
                # 直接返回SSH相关错误（如缺密码、连接超时）
                result["message"] = f"远程操作失败：{str(e)}" if is_zh else f"Remote operation failed: {str(e)}"
                return result
            finally:
                ssh.close()

    except Exception as e:
        # 全局异常：直接返回原始错误信息
        result["message"] = f"操作异常：{str(e)}" if is_zh else f"Operation exception: {str(e)}"
        return result
if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='sse')