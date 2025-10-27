"""进程控制工具：整合自定义SSH连接逻辑"""
from asyncio.log import logger
import logging


import re
import subprocess
from typing import Dict, List, Optional, Any

import paramiko
import psutil

from config.private.kill.config_loader import KillCommandConfig
from mcp.server import FastMCP

from servers.kill.src.base import _exec_local_signal_query, _exec_remote_signal_query, _format_raw_signals, create_ssh_connection, execute_local_command, execute_remote_command, get_language

# 初始化日志（使用仓库默认配置）
logging.basicConfig(level=logging.INFO)



# 声明FastMCP实例（仓库核心规范）
mcp = FastMCP("kill MCP Server", host="0.0.0.0", port=KillCommandConfig().get_config().private_config.port)
@mcp.tool(
    name="pause_process" if get_language() else "pause_process",
    description="""
    通过kill指令暂停进程（远程操作需目标主机在配置中存在）
    1. 输入参数：
        - pid：需要暂停的进程PID（必选，正整数）
        - host：主机名称/IP（默认localhost，远程操作需在配置中存在）
    2. 返回值：
        - success：布尔值，操作是否成功
        - message：字符串，操作结果描述
        - data：字典，包含操作的host和pid
    """ if get_language() else """
    Pause process via kill command (remote host must exist in configuration)
    1. Input parameters:
        - pid: PID of process to pause (required, positive integer)
        - host: Host name/IP (default localhost, remote host must be in config)
    2. Return value:
        - success: Boolean, operation success status
        - message: String, operation result description
        - data: Dictionary, contains host and pid of operation
    """,
)
def pause_process(
    pid: int,
    host: str = "localhost"
) -> Dict[str, Any]:
    # 初始化返回结果（完全遵循模板格式）
    result = {
        "success": False,
        "message": "",
        "data": {
            "host": host,
            "pid": pid
        }
    }
    is_zh = get_language()

    # 1. 参数校验
    if not isinstance(pid, int) or pid <= 0:
        result["message"] = "PID必须是正整数" if is_zh else "PID must be a positive integer"
        return result

    # 2. 本地操作逻辑
    if host in ["localhost", "127.0.0.1", "0.0.0.0"]:
        if not psutil.pid_exists(pid):
            result["message"] = f"本地进程{pid}不存在" if is_zh else f"Local process {pid} does not exist"
            return result

        try:
            proc = psutil.Process(pid)
            proc.suspend()

            if proc.status() == psutil.STATUS_STOPPED:
                result["success"] = True
                result["message"] = f"本地进程{pid}已暂停" if is_zh else f"Local process {pid} paused"
            else:
                result["message"] = f"本地进程{pid}暂停失败" if is_zh else f"Failed to pause local process {pid}"

        except psutil.AccessDenied:
            result["message"] = f"无权限暂停进程{pid}" if is_zh else f"No permission to pause process {pid}"
        except Exception as e:
            logger.error(f"本地暂停异常: {str(e)}")
            result["message"] = f"操作异常: {str(e)}" if is_zh else f"Operation error: {str(e)}"

        return result

    # 3. 远程操作逻辑（核心：先检索配置）
    else:
        # 3.1 查找远程主机配置
        matched_config = None
        for host_config in KillCommandConfig().get_config().public_config.remote_hosts:
            if host == host_config.name or host == host_config.host:
                matched_config = host_config
                break

        if not matched_config:
            result["message"] = f"未找到远程主机「{host}」的配置" if is_zh else f"Remote host「{host}」not found in config"
            return result

        # 3.2 建立SSH连接
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh.connect(
                hostname=matched_config.host,
                port=matched_config.port,
                username=matched_config.username,
                password=matched_config.password,
                timeout=10
            )
        except Exception as e:
            result["message"] = f"SSH连接失败: {str(e)}" if is_zh else f"SSH connection failed: {str(e)}"
            return result

        # 3.3 执行远程暂停操作
        try:
            # 检查进程是否存在
            check_cmd = f"ps -p {pid} >/dev/null 2>&1 && echo 1 || echo 0"
            stdin, stdout, stderr = ssh.exec_command(check_cmd)
            if stdout.read().decode().strip() != "1":
                result["message"] = f"远程进程{pid}不存在" if is_zh else f"Remote process {pid} does not exist"
                return result

            # 执行暂停命令
            pause_cmd = f"kill -STOP {pid}"
            stdin, stdout, stderr = ssh.exec_command(pause_cmd)
            err = stderr.read().decode().strip()
            if err:
                result["message"] = f"暂停失败: {err}" if is_zh else f"Pause failed: {err}"
                return result

            # 验证暂停状态
            verify_cmd = f"ps -p {pid} -o state | grep -q T && echo 1 || echo 0"
            stdin, stdout, stderr = ssh.exec_command(verify_cmd)
            if stdout.read().decode().strip() == "1":
                result["success"] = True
                result["message"] = f"远程进程{pid}已暂停" if is_zh else f"Remote process {pid} paused"
            else:
                result["message"] = f"远程进程{pid}暂停失败" if is_zh else f"Failed to pause remote process {pid}"

        finally:
            ssh.close()

        return result

@mcp.tool(
    name="resume_process" if get_language() else "resume_process",
    description=
    """
    通过kill指令来恢复进程（支持本地/远程，发送SIGCONT信号）
    
    1. 输入值如下：
        - pid：需要恢复的进程PID，必须为正整数
        - host：远程主机名称或IP地址，默认值为"localhost"（表示操作本机）
        - port：SSH连接端口，默认值为22
        - username：SSH登录用户名，默认值为"root"，远程操作时需指定
        - password：SSH登录密码，远程操作时为必填项
    
    2. 返回值为包含操作结果的字典
        - success：布尔值，表示操作是否成功
        - message：字符串，描述操作结果（成功信息或错误原因）
        - data：字典，回显本次操作的关键信息
            - host：本次操作的主机名称或IP地址
            - pid：本次恢复的进程PID
    
    """
    if get_language() else
    """
    Resume process (supports local/remote, sends SIGCONT signal). 
    Sends SIGCONT signal via kill command to resume a paused process, 
    applicable for restarting local or remote paused processes
    1. Input values are as follows:
        - pid: PID of the process to resume, must be a positive integer
        - host: Remote host name or IP address, default is "localhost" (indicates local operation)
        - port: SSH connection port, default is 22
        - username: SSH login username, default is "root", required for remote operations
        - password: SSH login password, mandatory for remote operations
    
    2. Return value is a dictionary containing operation results
        - success: Boolean, indicating whether the operation was successful
        - message: String, describing the operation result (success information or error reason)
        - data: Dictionary, echoing key information of this operation
            - host: Host name or IP address of this operation
            - pid: PID of the process resumed in this operation
    """
    ,
)
def resume_process(
    pid: int,
    host: str = "localhost",
    port: int = 22,
    username: str = "root",
    password: str = ""
) -> Dict:
    """恢复进程工具（严格遵循模板逻辑：配置检索优先，返回值结构统一）"""
    is_zh = get_language()
    
    # 初始化返回结果（与模板完全一致的结构）
    result = {
        "success": False,
        "message": "",
        "data": {
            "pid": pid,
            "host": host,
        }
    }

    try:
        # -------------------------- 1. 参数校验（优先级最高，提前返回） --------------------------
        # 校验PID合法性（替代工具类，逻辑直观）
        if not isinstance(pid, int) or pid <= 0:
            result["message"] = "PID必须是正整数" if is_zh else "PID must be a positive integer"
            return result

        # 校验用户名非空
        if not username.strip():
            result["message"] = "用户名不能为空" if is_zh else "Username cannot be empty"
            return result

        # 远程操作时校验密码（必填）
        if host not in ["localhost", "127.0.0.1", "0.0.0.0"] and not password.strip():
            result["message"] = "远程操作需提供SSH登录密码" if is_zh else "SSH login password is required for remote operation"
            return result

        # -------------------------- 2. 本地进程恢复逻辑 --------------------------
        if host in ["localhost", "127.0.0.1", "0.0.0.0"]:
            # 检查进程是否存在
            if not psutil.pid_exists(pid):
                result["message"] = f"本地进程{pid}不存在" if is_zh else f"Local process {pid} does not exist"
                return result

            try:
                # 恢复进程（发送SIGCONT信号）
                proc = psutil.Process(pid)
                proc.resume()

                # 验证恢复结果：状态不再是"停止"（STOPPED）
                if proc.status() != psutil.STATUS_STOPPED:
                    result["success"] = True
                    result["message"] = f"本地进程{pid}已恢复" if is_zh else f"Local process {pid} has been resumed"
                else:
                    result["message"] = f"本地进程{pid}恢复失败" if is_zh else f"Failed to resume local process {pid}"

            except psutil.AccessDenied:
                result["message"] = f"无权限恢复本地进程{pid}" if is_zh else f"No permission to resume local process {pid}"
            except psutil.NoSuchProcess:
                result["message"] = f"本地进程{pid}已退出" if is_zh else f"Local process {pid} has exited"
            except Exception as e:
                logger.error(f"Local resume error: {str(e)}")
                result["message"] = f"本地恢复异常: {str(e)}" if is_zh else f"Local resume exception: {str(e)}"

            return result

        # -------------------------- 3. 远程进程恢复逻辑（核心：先检索配置） --------------------------
        else:
            # 3.1 检索目标主机是否在KillCommandConfig配置中（模板核心逻辑）
            matched_config = None
            for host_config in KillCommandConfig().get_config().public_config.remote_hosts:
                if host == host_config.name or host == host_config.host:
                    matched_config = host_config
                    break

            # 未匹配到配置：直接返回错误
            if not matched_config:
                result["message"] = f"未找到远程主机「{host}」的配置" if is_zh else f"Remote host「{host}」not found in config"
                return result

            # 3.2 建立SSH连接（使用配置中的认证信息）
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                ssh.connect(
                    hostname=matched_config.host,
                    port=matched_config.port,
                    username=matched_config.username,
                    password=matched_config.password,
                    timeout=10
                )
            except paramiko.AuthenticationException:
                result["message"] = "SSH认证失败，请检查配置中的用户名和密码" if is_zh else "SSH auth failed, check username/password in config"
                return result
            except TimeoutError:
                result["message"] = f"连接远程主机「{matched_config.host}」超时" if is_zh else f"Timeout connecting to remote host「{matched_config.host}」"
                return result
            except Exception as e:
                result["message"] = f"SSH连接失败: {str(e)}" if is_zh else f"SSH connection failed: {str(e)}"
                return result

            # 3.3 执行远程恢复操作
            try:
                # 检查远程进程是否存在
                check_cmd = f"ps -p {pid} >/dev/null 2>&1 && echo 1 || echo 0"
                stdin, stdout, stderr = ssh.exec_command(check_cmd)
                check_out = stdout.read().decode().strip()
                check_err = stderr.read().decode().strip()
                if check_err:
                    result["message"] = f"检查远程进程失败: {check_err}" if is_zh else f"Failed to check remote process: {check_err}"
                    return result
                if check_out != "1":
                    result["message"] = f"远程进程{pid}不存在" if is_zh else f"Remote process {pid} does not exist"
                    return result

                # 执行恢复命令（kill -CONT）
                resume_cmd = f"kill -CONT {pid}"
                stdin, stdout, stderr = ssh.exec_command(resume_cmd)
                resume_err = stderr.read().decode().strip()
                if resume_err:
                    result["message"] = f"恢复远程进程失败: {resume_err}" if is_zh else f"Failed to resume remote process: {resume_err}"
                    return result

                # 验证恢复结果：进程状态不再是"T"（Stopped）
                verify_cmd = f"ps -p {pid} -o state | grep -q T && echo 0 || echo 1"
                stdin, stdout, stderr = ssh.exec_command(verify_cmd)
                verify_out = stdout.read().decode().strip()
                if verify_out == "1":
                    result["success"] = True
                    result["message"] = f"远程进程{pid}已恢复" if is_zh else f"Remote process {pid} has been resumed"
                else:
                    result["message"] = f"远程进程{pid}恢复失败" if is_zh else f"Failed to resume remote process {pid}"

            finally:
                ssh.close()

            return result

    # -------------------------- 4. 全局异常捕获 --------------------------
    except Exception as e:
        logger.error(f"resume_process global exception: {str(e)}")
        result["message"] = f"操作异常: {str(e)}" if is_zh else f"Operation exception: {str(e)}"
        return result



@mcp.tool(
    name="get_kill_signals" if get_language() else "get_kill_signals",
    description=
    """
    查看本地或远程服务器的kill信号量含义（远程需提供SSH信息）。返回系统支持的所有kill信号及其描述，包括信号编号、名称和功能说明。
    支持本地和远程的信号量查询工具
    
    本地查询：不填host、username、password即可
    远程查询：必须提供host、username、password（port可选，默认22）
    
    1. 输入值如下：
        - host：远程主机IP或hostname，不填则查询本地
        - port：SSH端口，默认22
        - username：SSH用户名，远程查询时必填
        - password：SSH密码，远程查询时必填
    
    2. 返回值为包含查询结果的字典
        - success：布尔值，表示查询是否成功
        - message：字符串，描述查询结果（成功信息或错误原因）
        - data：字典，包含信号量详细信息
            - host：查询的主机（本地为"localhost"）
            - signals：列表，每个元素为信号量信息字典
                - number：信号编号（整数）
                - name：信号名称（如"SIGTERM"）
                - description：信号功能说明   
    """
    if get_language() else
    """
    Signal query tool supporting local and remote servers
    
    Local query: Leave host, username, password empty
    Remote query: Must provide host, username, password (port is optional, default 22)
    
    1. Input values are as follows:
        - host: Remote host IP or hostname, leave empty for local query
        - port: SSH port, default 22
        - username: SSH username, required for remote query
        - password: SSH password, required for remote query
    
    2. Return value is a dictionary containing query results
        - success: Boolean, indicating whether the query was successful
        - message: String, describing the query result (success information or error reason)
        - data: Dictionary, containing detailed signal information
            - host: Queried host ("localhost" for local)
            - signals: List, each element is a signal information dictionary
                - number: Signal number (integer)
                - name: Signal name (e.g., "SIGTERM")
                - description: Signal function explanation
    """
    ,
)
def get_kill_signals(
    host: Optional[str] = None,
    port: int = 22,
    username: Optional[str] = None,
    password: Optional[str] = None
) -> Dict:
    """查询kill信号量工具（严格遵循模板逻辑：配置检索优先，返回值结构统一）"""
    is_zh = get_language()

    # 初始化返回结果（与模板完全一致的结构）
    result = {
        "success": False,
        "message": "",
        "data": {
            "host": host or "localhost",
            "signals": []
        }
    }

    try:
        # -------------------------- 1. 参数校验与配置匹配（远程场景核心） --------------------------
        # 场景1：远程查询（host不为空）
        if host is not None:
            # 1.1 先检索KillCommandConfig配置（模板核心逻辑）
            matched_config = None
            for host_config in KillCommandConfig().get_config().public_config.remote_hosts:
                if host == host_config.name or host == host_config.host:
                    matched_config = host_config
                    # logger.info(f"Matched remote host config: {matched_config}")
                    break

            # 1.2 处理配置匹配结果
            if matched_config:
                # 使用配置中的认证信息（覆盖手动传入参数，确保配置优先）
                remote_host = matched_config.host
                remote_port = matched_config.port if matched_config.port else port
                remote_user = matched_config.username
                remote_pwd = matched_config.password
            else:
                # 未匹配到配置：校验手动传入的认证信息
                if not username or not password:
                    logger.info("No matched_config and missing username/password for remote query")
                    result["message"] = "远程查询需提供username和password" if is_zh else "Username and password are required for remote queries"
                    return result
                remote_host = host
                remote_port = port
                remote_user = username
                remote_pwd = password

            # 1.3 执行远程信号量查询
            raw_signals = _exec_remote_signal_query(remote_host, remote_port, remote_user, remote_pwd)
            result["message"] = f"成功获取远程主机 {remote_host} 的信号量信息" if is_zh else f"Successfully obtained signal info for remote host {remote_host}"

        # 场景2：本地查询（host为空）
        else:
            # 执行本地信号量查询
            raw_signals = _exec_local_signal_query()
            result["message"] = "成功获取本地主机的信号量信息" if is_zh else "Successfully obtained signal info for local host"

        # -------------------------- 2. 格式化信号量结果 --------------------------
        result["data"]["signals"] = _format_raw_signals(raw_signals, is_zh)
        result["success"] = True
        return result

    # -------------------------- 3. 异常捕获与处理 --------------------------
    except subprocess.CalledProcessError as e:
        err_msg = f"命令执行失败: {e.stderr.decode().strip()}" if is_zh else f"Command execution failed: {e.stderr.decode().strip()}"
        logger.error(err_msg)
        result["message"] = err_msg
    except paramiko.AuthenticationException:
        err_msg = "SSH认证失败，请检查用户名和密码" if is_zh else "SSH authentication failed, check username and password"
        logger.error(err_msg)
        result["message"] = err_msg
    except paramiko.SSHException as e:
        err_msg = f"SSH连接异常: {str(e)}" if is_zh else f"SSH connection exception: {str(e)}"
        logger.error(err_msg)
        result["message"] = err_msg
    except Exception as e:
        err_msg = f"获取信号量信息失败: {str(e)}" if is_zh else f"Failed to obtain signal info: {str(e)}"
        logger.error(err_msg)
        result["message"] = err_msg

    return result

@mcp.tool(
    name="kill_process" if get_language() else "kill_process",
    description="""
    通过kill命令发送信号终止进程（支持本地/远程）
    
    参数:
        -pid: 进程PID（正整数，必填）
        -signal: 信号量（可选，默认SIGTERM(15)，常用值：9(SIGKILL)、15(SIGTERM)）
        -host: 远程主机名/IP（本地操作可不填）
    
    返回:
        -success: 操作是否成功
        -message: 结果描述
        -data: 包含操作详情的字典
    """ if get_language() else """
    Terminate process by sending signal via kill command (supports local/remote)
    
    Parameters:
        -pid: Process PID (positive integer, required)
        -signal: Signal number (optional, default SIGTERM(15), common values: 9(SIGKILL), 15(SIGTERM))
        -host: Remote hostname/IP (optional for local operation)
    
    Returns:
        -success: Whether the operation is successful
        -message: Result description
        -data: Dictionary containing operation details
    """
)
def kill_process(pid: int, signal: int = 15, host: str = "") -> Dict:
    is_zh = get_language()
    result: Dict = {
        "success": False,
        "message": "",
        "data": {
            "pid": pid,
            "signal": signal,
            "host": host or "localhost"
        }
    }

    # 参数校验
    if not isinstance(pid, int) or pid <= 0:
        result["message"] = "PID必须是正整数" if is_zh else "PID must be a positive integer"
        return result

    if not isinstance(signal, int) or signal < 1 or signal > 64:
        result["message"] = "信号量必须是1-64之间的整数" if is_zh else "Signal must be an integer between 1-64"
        return result

    # 构建命令
    command = f"kill -{signal} {pid}"

    # 执行命令（本地/远程）
    if not host or host in ["localhost", "127.0.0.1"]:
        # 本地操作
        success, stdout, stderr = execute_local_command(command)
        if success:
            result["success"] = True
            result["message"] = f"已向进程{pid}发送信号{signal}" if is_zh else f"Sent signal {signal} to process {pid}"
        else:
            result["message"] = f"操作失败: {stderr}" if is_zh else f"Operation failed: {stderr}"
    else:
        # 远程操作
        ssh = create_ssh_connection(host)
        if not ssh:
            result["message"] = f"无法连接到远程主机{host}" if is_zh else f"Failed to connect to remote host {host}"
            return result

        try:
            success, stdout, stderr = execute_remote_command(ssh, command)
            if success and not stderr:
                result["success"] = True
                result["message"] = f"已向远程主机{host}的进程{pid}发送信号{signal}" if is_zh else f"Sent signal {signal} to process {pid} on {host}"
            else:
                result["message"] = f"远程操作失败: {stderr}" if is_zh else f"Remote operation failed: {stderr}"
        finally:
            try:
                ssh.close()
            except Exception as e:
                logger.warning(f"关闭SSH连接失败: {str(e)}")

    return result


@mcp.tool(
    name="check_process_status" if get_language() else "check_process_status",
    description="""
    检查进程是否存在（支持本地/远程）
    
    参数:
        -pid: 进程PID（正整数，必填）
        -host: 远程主机名/IP（本地操作可不填）
    
    返回:
        -success: 查询是否成功
        -message: 结果描述
        -data: 包含进程状态的字典
    """ if get_language() else """
    Check if process exists (supports local/remote)
    
    Parameters:
        -pid: Process PID (positive integer, required)
        -host: Remote hostname/IP (optional for local operation)
    
    Returns:
        -success: Whether the query is successful
        -message: Result description
        -data: Dictionary containing process status
    """
)
def check_process_status(pid: int, host: str = "") -> Dict:
    is_zh = get_language()
    result: Dict = {
        "success": False,
        "message": "",
        "data": {
            "pid": pid,
            "host": host or "localhost",
            "exists": False,
            "name": ""
        }
    }

    # 参数校验
    if not isinstance(pid, int) or pid <= 0:
        result["message"] = "PID必须是正整数" if is_zh else "PID must be a positive integer"
        return result

    # 构建命令
    command = f"ps -p {pid} -o comm="  # 获取进程名

    # 执行命令（本地/远程）
    if not host or host in ["localhost", "127.0.0.1"]:
        success, stdout, stderr = execute_local_command(command)
        if success:
            result["success"] = True
            result["data"]["exists"] = len(stdout) > 0
            result["data"]["name"] = stdout.strip() if stdout else ""
            result["message"] = f"进程{pid} {'存在' if result['data']['exists'] else '不存在'}" if is_zh else f"Process {pid} {'exists' if result['data']['exists'] else 'does not exist'}"
        else:
            result["message"] = f"查询失败: {stderr}" if is_zh else f"Query failed: {stderr}"
    else:
        ssh = create_ssh_connection(host)
        if not ssh:
            result["message"] = f"无法连接到远程主机{host}" if is_zh else f"Failed to connect to remote host {host}"
            return result

        try:
            success, stdout, stderr = execute_remote_command(ssh, command)
            if success:
                result["success"] = True
                result["data"]["exists"] = len(stdout) > 0
                result["data"]["name"] = stdout.strip() if stdout else ""
                result["message"] = f"远程主机{host}的进程{pid} {'存在' if result['data']['exists'] else '不存在'}" if is_zh else f"Process {pid} on {host} {'exists' if result['data']['exists'] else 'does not exist'}"
            else:
                result["message"] = f"远程查询失败: {stderr}" if is_zh else f"Remote query failed: {stderr}"
        finally:
            try:
                ssh.close()
            except Exception as e:
                logger.warning(f"关闭SSH连接失败: {str(e)}")

    return result


@mcp.tool(
    name="get_signal_info" if get_language() else "get_signal_info",
    description="""
    获取系统支持的信号量信息（支持本地/远程）
    
    参数:
        -host: 远程主机名/IP（本地查询可不填）
    
    返回:
        -success: 查询是否成功
        -message: 结果描述
        -data: 包含信号量信息的字典
    """ if get_language() else """
    Get system-supported signal information (supports local/remote)
    
    Parameters:
        -host: Remote hostname/IP (optional for local query)
    
    Returns:
        -success: Whether the query is successful
        -message: Result description
        -data: Dictionary containing signal information
    """
)
def get_signal_info(host: str = "") -> Dict:
    is_zh = get_language()
    result: Dict = {
        "success": False,
        "message": "",
        "data": {
            "host": host or "localhost",
            "signals": []
        }
    }

    # 执行命令获取信号信息
    command = "kill -l | cat -n | awk '{print $1-1 \":\" $2}' | grep -E '^[0-9]+:[A-Z]+'"
    
    if not host or host in ["localhost", "127.0.0.1"]:
        success, stdout, stderr = execute_local_command(command)
    else:
        ssh = create_ssh_connection(host)
        if not ssh:
            result["message"] = f"无法连接到远程主机{host}" if is_zh else f"Failed to connect to remote host {host}"
            return result

        try:
            success, stdout, stderr = execute_remote_command(ssh, command)
        finally:
            try:
                ssh.close()
            except Exception as e:
                logger.warning(f"关闭SSH连接失败: {str(e)}")

    # 解析结果
    if success and stdout:
        signal_pattern = re.compile(r'^(\d+):([A-Z]+)$')
        signals: List[Dict] = []
        for line in stdout.split('\n'):
            line = line.strip()
            match = signal_pattern.match(line)
            if match:
                num = int(match.group(1))
                name = match.group(2)
                # 补充常用信号描述
                descriptions = {
                    9: "强制终止进程（不可捕获）",
                    15: "优雅终止进程（默认信号，可捕获）",
                    18: "恢复暂停的进程（SIGCONT）",
                    19: "暂停进程（SIGSTOP，不可捕获）"
                }
                en_descriptions = {
                    9: "Force terminate process (uncatchable)",
                    15: "Gracefully terminate process (default, catchable)",
                    18: "Resume paused process (SIGCONT)",
                    19: "Pause process (SIGSTOP, uncatchable)"
                }
                desc = descriptions.get(num, "") if is_zh else en_descriptions.get(num, "")
                signals.append({
                    "number": num,
                    "name": name,
                    "description": desc
                })
        result["data"]["signals"] = signals
        result["success"] = True
        result["message"] = f"共查询到{len(signals)}个信号量" if is_zh else f"Found {len(signals)} signals"
    else:
        result["message"] = f"查询信号量失败: {stderr}" if is_zh else f"Failed to query signals: {stderr}"

    return result

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='sse')