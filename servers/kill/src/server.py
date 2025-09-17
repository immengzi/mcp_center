"""进程控制工具：整合自定义SSH连接逻辑"""
from asyncio.log import logger
import logging


import subprocess
from typing import Dict, List, Optional, Any

import paramiko
import psutil

from config.private.kill.config_loader import KillCommandConfig
from config.public.base_config_loader import LanguageEnum
from mcp.server import FastMCP

# 初始化日志（使用仓库默认配置）
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_language_config() -> bool:
    """获取语言配置（True为中文，False为英文）"""
    return KillCommandConfig().get_config().public_config.language == LanguageEnum.ZH


# 声明FastMCP实例（仓库核心规范）
mcp = FastMCP("kill MCP Server", host="0.0.0.0", port=KillCommandConfig().get_config().private_config.port)
@mcp.tool(
    name="pause_process" if get_language_config() else "pause_process",
    description="""
    通过kill指令暂停进程（远程操作需目标主机在配置中存在）
    1. 输入参数：
        - pid：需要暂停的进程PID（必选，正整数）
        - host：主机名称/IP（默认localhost，远程操作需在配置中存在）
    2. 返回值：
        - success：布尔值，操作是否成功
        - message：字符串，操作结果描述
        - data：字典，包含操作的host和pid
    """ if get_language_config() else """
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
    is_zh = get_language_config()

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
    name="resume_process" if get_language_config() else "resume_process",
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
    if get_language_config() else
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
    is_zh = get_language_config()
    
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
    name="get_kill_signals" if get_language_config() else "get_kill_signals",
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
    if get_language_config() else
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
    is_zh = get_language_config()

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


# -------------------------- 私有辅助函数（拆分逻辑，提升可读性） --------------------------
def _exec_local_signal_query() -> str:
    """执行本地kill信号量查询（通过kill -l命令）"""
    # 使用kill -l命令获取信号列表，-v参数显示详细描述（部分系统支持）
    try:
        # 优先尝试带详细描述的命令（如Linux）
        result = subprocess.run(
            ["kill", "-lv"],  # -l显示信号列表，-v显示详细描述
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8"
        )
        return result.stdout
    except subprocess.CalledProcessError:
        # 若不支持-v参数，退化为仅获取信号列表（如macOS）
        result = subprocess.run(
            ["kill", "-l"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8"
        )
        return result.stdout


def _exec_remote_signal_query(host: str, port: int, username: str, password: str) -> str:
    """执行远程kill信号量查询（通过SSH）"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        # 建立SSH连接
        ssh.connect(
            hostname=host,
            port=port,
            username=username,
            password=password,
            timeout=10
        )

        # 执行远程命令（逻辑同本地，优先带详细描述）
        try:
            stdin, stdout, stderr = ssh.exec_command("kill -lv")
            exit_code = stdout.channel.recv_exit_status()
            if exit_code != 0:
                raise subprocess.CalledProcessError(exit_code, "kill -lv", stderr.read())
            return stdout.read().decode("utf-8")
        except Exception:
            # 退化为仅获取信号列表
            stdin, stdout, stderr = ssh.exec_command("kill -l")
            exit_code = stdout.channel.recv_exit_status()
            if exit_code != 0:
                raise subprocess.CalledProcessError(exit_code, "kill -l", stderr.read())
            return stdout.read().decode("utf-8")
    finally:
        # 确保SSH连接关闭
        ssh.close()


def _format_raw_signals(raw_signals: str, is_zh: bool) -> List[Dict]:
    """格式化原始信号量输出为结构化列表（支持中英文描述）"""
    signal_list = []
    # 信号描述映射（覆盖常见信号，统一中英文）
    signal_desc_map = {
        "SIGHUP": {"zh": "挂起信号（终端关闭时发送）", "en": "Hangup (sent when terminal is closed)"},
        "SIGINT": {"zh": "中断信号（Ctrl+C触发）", "en": "Interrupt (triggered by Ctrl+C)"},
        "SIGQUIT": {"zh": "退出信号（Ctrl+\\触发，产生core dump）", "en": "Quit (triggered by Ctrl+\\, generates core dump)"},
        "SIGILL": {"zh": "非法指令信号（程序执行非法机器码）", "en": "Illegal instruction (program executes invalid machine code)"},
        "SIGTRAP": {"zh": "陷阱信号（调试时触发断点）", "en": "Trace trap (triggered by breakpoints during debugging)"},
        "SIGABRT": {"zh": "中止信号（abort()函数触发）", "en": "Abort (triggered by abort() function)"},
        "SIGBUS": {"zh": "总线错误信号（内存访问错误）", "en": "Bus error (memory access error)"},
        "SIGFPE": {"zh": "浮点异常信号（除零、溢出等）", "en": "Floating-point exception (division by zero, overflow, etc.)"},
        "SIGKILL": {"zh": "强制终止信号（无法忽略，必杀死进程）", "en": "Kill (cannot be ignored, forces process termination)"},
        "SIGUSR1": {"zh": "用户自定义信号1（用户程序可自定义处理）", "en": "User-defined signal 1 (custom handling by user program)"},
        "SIGSEGV": {"zh": "段错误信号（非法内存访问）", "en": "Segmentation fault (invalid memory access)"},
        "SIGUSR2": {"zh": "用户自定义信号2（用户程序可自定义处理）", "en": "User-defined signal 2 (custom handling by user program)"},
        "SIGPIPE": {"zh": "管道破裂信号（向关闭的管道写数据）", "en": "Broken pipe (writing to a closed pipe)"},
        "SIGALRM": {"zh": "闹钟信号（alarm()函数触发）", "en": "Alarm (triggered by alarm() function)"},
        "SIGTERM": {"zh": "终止信号（默认kill命令信号，可被忽略）", "en": "Terminate (default kill command signal, can be ignored)"},
        "SIGSTKFLT": {"zh": "栈溢出信号（栈空间不足）", "en": "Stack fault (insufficient stack space)"},
        "SIGCHLD": {"zh": "子进程状态变化信号（子进程退出/暂停时发送）", "en": "Child status change (sent when child exits/pauses)"},
        "SIGCONT": {"zh": "继续信号（恢复暂停的进程）", "en": "Continue (resumes a paused process)"},
        "SIGSTOP": {"zh": "停止信号（暂停进程，无法忽略）", "en": "Stop (pauses process, cannot be ignored)"},
        "SIGTSTP": {"zh": "终端停止信号（Ctrl+Z触发，可被忽略）", "en": "Terminal stop (triggered by Ctrl+Z, can be ignored)"},
        "SIGTTIN": {"zh": "后台进程读终端信号（后台进程尝试读终端时发送）", "en": "Background read from terminal (sent when background process tries to read terminal)"},
        "SIGTTOU": {"zh": "后台进程写终端信号（后台进程尝试写终端时发送）", "en": "Background write to terminal (sent when background process tries to write terminal)"},
        "SIGURG": {"zh": "紧急数据信号（socket收到紧急数据）", "en": "Urgent data (socket receives urgent data)"},
        "SIGXCPU": {"zh": "CPU时间超限信号（进程超过CPU时间限制）", "en": "CPU time limit exceeded (process exceeds CPU time limit)"},
        "SIGXFSZ": {"zh": "文件大小超限信号（进程超过文件大小限制）", "en": "File size limit exceeded (process exceeds file size limit)"},
        "SIGVTALRM": {"zh": "虚拟时钟信号（虚拟时间超时）", "en": "Virtual timer alarm (virtual time timeout)"},
        "SIGPROF": {"zh": "性能分析时钟信号（ profiling 时间超时）", "en": "Profiling timer alarm (profiling time timeout)"},
        "SIGWINCH": {"zh": "窗口大小变化信号（终端窗口大小改变时发送）", "en": "Window size change (sent when terminal window size changes)"},
        "SIGIO": {"zh": "I/O就绪信号（I/O操作就绪时发送）", "en": "I/O ready (sent when I/O operation is ready)"},
        "SIGPWR": {"zh": "电源故障信号（系统电源异常时发送）", "en": "Power failure (sent when system power is abnormal)"},
        "SIGSYS": {"zh": "非法系统调用信号（调用不存在的系统调用）", "en": "Bad system call (calling a non-existent system call)"}
    }

    # 解析原始输出（处理两种格式：1. " 1) SIGHUP"  2. "HUP 1"）
    for line in raw_signals.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        # 格式1：信号编号在前（如 " 1) SIGHUP"）
        if ")" in line:
            parts = line.split(")")
            if len(parts) < 2:
                continue
            num_str = parts[0].strip()
            name = parts[1].strip().split()[0]  # 避免包含额外描述
        # 格式2：信号名称在前（如 "HUP 1"）
        else:
            parts = line.split()
            if len(parts) < 2:
                continue
            # 判断哪部分是数字（处理 "SIG1" 或 "1" 格式）
            if parts[0].startswith("SIG"):
                name = parts[0]
                num_str = parts[1]
            else:
                name = f"SIG{parts[0]}" if not parts[0].startswith("SIG") else parts[0]
                num_str = parts[1]

        # 转换信号编号为整数
        try:
            number = int(num_str)
        except ValueError:
            continue

        # 获取信号描述（无匹配时显示默认信息）
        desc = signal_desc_map.get(name, {"zh": "未定义信号", "en": "Undefined signal"})
        signal_list.append({
            "number": number,
            "name": name,
            "description": desc["zh"] if is_zh else desc["en"]
        })

    # 按信号编号排序
    return sorted(signal_list, key=lambda x: x["number"])
if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='sse')