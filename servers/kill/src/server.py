"""进程控制工具：整合自定义SSH连接逻辑"""
from asyncio.log import logger
import logging


from typing import Dict, Tuple, Optional, Union

import psutil

from config.private.kill.config_loader import KillCommandConfig
from config.public.base_config_loader import LanguageEnum
from servers.kill.src.base import ProcessControlUtil, _format_signal_info, _get_local_signals, _get_remote_signals
from mcp.server import FastMCP

# 初始化日志（使用仓库默认配置）
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 声明FastMCP实例（仓库核心规范）
mcp = FastMCP("kill MCP Server", host="0.0.0.0", port=KillCommandConfig().get_config().private_config.port)
@mcp.tool(
    name="pause_process"    
    if KillCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "pause_process",
    description=
    """
    通过kill指令来暂停进程（支持本地/远程，发送SIGSTOP信号）
    1.输入值如下：
        - pid：需要暂停的进程 PID，必须为正整数
        - host: 远程主机名称或 IP 地址，默认值为 "localhost"（表示操作本机）
        - port: SSH 连接端口，默认值为 22
        - username: SSH 登录用户名，默认值为 "root"，远程操作时需指定
        - password: SSH 登录密码，远程操作时为必填项
    2.返回值包含操作结果的字典
        - success: 布尔值，表示操作是否成功
        - message: 字符串，描述操作结果（成功信息或错误原因）
        - data:字典，回显本次操作的host和pid
            -host：本次操作主机名称或 IP 地址
            -pid：本次暂停的进程
        
    """
    if KillCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    """Use kill to pause process tool (repository function implementation style: concise and direct)
    1. Input values are as follows:
        - pid: PID of the process to pause, must be a positive integer
        - host: Remote host name or IP address, default is "localhost" (indicates local operation)
        - port: SSH connection port, default is 22
        - username: SSH login username, default is "root", required for remote operations
        - password: SSH login password, mandatory for remote operations
    
    2. Return value is a dictionary containing operation results
        - success: Boolean, indicating whether the operation was successful
        - message: String, describing the operation result (success information or error reason)
        - data: Dictionary, echoing the host and pid of this operation
            - host: Host name or IP address of this operation
            - pid: Process paused in this operation
    """
    ,
)
def pause_process(
    pid: int,
    host: str = "localhost",
    port: int = 22,
    username: str = "root",
    password: str = ""
) -> Dict:
    is_zh = KillCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    
    result = {
        "success": False,
        "message": "",
        "data": {
            "host": host,
            "pid": pid,
        }
    }

    try:
        # 1. 参数校验
        valid, msg = ProcessControlUtil._validate_pid(pid)
        if not valid:
            result["message"] = msg
            return result

        if not username:
            result["message"] = "用户名不能为空" if is_zh else "Username cannot be empty"
            return result

        # 2. 本地/远程处理
        if ProcessControlUtil._is_local(host):
            # 本地进程暂停
            if not psutil.pid_exists(pid):
                result["message"] = f"本地进程{pid}不存在" if is_zh else f"Local process {pid} does not exist"
                return result

            proc = psutil.Process(pid)
            proc.suspend()

            if proc.status() in (psutil.STATUS_STOPPED):
                result["success"] = True
                result["message"] = f"本地进程{pid}已暂停" if is_zh else f"Local process {pid} has been paused"
            else:
                result["message"] = f"本地进程{pid}暂停失败" if is_zh else f"Failed to pause local process {pid}"

        else:
            # 远程进程暂停
            ssh, err = ProcessControlUtil._ssh_connect(host, port, username, password)
            if not ssh:
                result["message"] = err
                return result

            try:
                # 检查进程是否存在
                check_cmd = f"ps -p {pid} >/dev/null 2>&1 && echo 1 || echo 0"
                out, err = ProcessControlUtil._exec_ssh_cmd(ssh, check_cmd)
                if err:
                    result["message"] = (f"检查进程失败: {err}" if is_zh 
                                       else f"Failed to check process: {err}")
                    return result
                if out.strip() != "1":
                    result["message"] = (f"远程进程{pid}不存在" if is_zh 
                                       else f"Remote process {pid} does not exist")
                    return result

                # 执行暂停命令
                pause_cmd = f"kill -STOP {pid}"
                _, err = ProcessControlUtil._exec_ssh_cmd(ssh, pause_cmd)
                if err:
                    result["message"] = (f"暂停失败: {err}" if is_zh 
                                       else f"Failed to pause: {err}")
                    return result

                # 验证状态
                status_cmd = f"ps -p {pid} -o state | grep -q T && echo 1 || echo 0"
                out, _ = ProcessControlUtil._exec_ssh_cmd(ssh, status_cmd)
                if out.strip() == "1":
                    result["success"] = True
                    result["message"] = (f"远程进程{pid}已暂停" if is_zh 
                                       else f"Remote process {pid} has been paused")
                else:
                    result["message"] = (f"远程进程{pid}暂停失败" if is_zh 
                                       else f"Failed to pause remote process {pid}")

            finally:
                ssh.close()

    except Exception as e:
        logger.error(f"pause_process异常: {str(e)}" if is_zh else f"pause_process exception: {str(e)}")
        result["message"] = (f"操作异常: {str(e)}" if is_zh 
                           else f"Operation exception: {str(e)}")

    return result

@mcp.tool(
    name="resume_process"
    if KillCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "resume_process",
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
    if KillCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    else
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
    """恢复进程工具（与暂停工具风格保持一致致）"""
    # 根据配置获取语言
    is_zh = KillCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    
    result = {
        "success": False,
        "message": "",
        "data": {
            "pid": pid,
            "host": host,
        }
    }

    try:
        # 参数校验
        valid, msg = ProcessControlUtil._validate_pid(pid)
        if not valid:
            result["message"] = msg
            return result

        if not username:
            result["message"] = "用户名不能为空" if is_zh else "Username cannot be empty"
            return result

        # 本地/远程处理
        if ProcessControlUtil._is_local(host):
            # 本地进程恢复
            if not psutil.pid_exists(pid):
                result["message"] = f"本地进程{pid}不存在" if is_zh else f"Local process {pid} does not exist"
                return result

            proc = psutil.Process(pid)
            proc.resume()

            if proc.status() not in (psutil.STATUS_STOPPED):
                result["success"] = True
                result["message"] = f"本地进程{pid}已恢复" if is_zh else f"Local process {pid} has been resumed"
            else:
                result["message"] = f"本地进程{pid}恢复失败" if is_zh else f"Failed to resume local process {pid}"

        else:
            # 远程进程恢复
            ssh, err = ProcessControlUtil._ssh_connect(host, port, username, password)
            if not ssh:
                result["message"] = err
                return result

            try:
                # 检查进程是否存在
                check_cmd = f"ps -p {pid} >/dev/null 2>&1 && echo 1 || echo 0"
                out, err = ProcessControlUtil._exec_ssh_cmd(ssh, check_cmd)
                if err:
                    result["message"] = f"检查进程失败: {err}" if is_zh else f"Failed to check process: {err}"
                    return result
                if out.strip() != "1":
                    result["message"] = f"远程进程{pid}不存在" if is_zh else f"Remote process {pid} does not exist"
                    return result

                # 执行恢复命令
                resume_cmd = f"kill -CONT {pid}"
                _, err = ProcessControlUtil._exec_ssh_cmd(ssh, resume_cmd)
                if err:
                    result["message"] = f"恢复失败: {err}" if is_zh else f"Failed to resume: {err}"
                    return result

                # 验证状态
                status_cmd = f"ps -p {pid} -o state | grep -q T && echo 0 || echo 1"
                out, _ = ProcessControlUtil._exec_ssh_cmd(ssh, status_cmd)
                if out.strip() == "1":
                    result["success"] = True
                    result["message"] = f"远程进程{pid}已恢复" if is_zh else f"Remote process {pid} has been resumed"
                else:
                    result["message"] = f"远程进程{pid}恢复失败" if is_zh else f"Failed to resume remote process {pid}"

            finally:
                ssh.close()

    except Exception as e:
        logger.error(f"resume_process异常: {str(e)}" if is_zh else f"resume_process exception: {str(e)}")
        result["message"] = f"操作异常: {str(e)}" if is_zh else f"Operation exception: {str(e)}"

    return result



@mcp.tool(
    name="get_kill_signals"
    if KillCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "get_kill_signals",
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
    if KillCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    else
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
    result = {
        "success": False,
        "message": "",
        "data": {}
    }

    # 远程查询条件判断
    if host and (not username or not password):
        result["message"] = "远程查询需提供username和password" if KillCommandConfig().get_config().public_config.language == LanguageEnum.ZH else "Username and password are required for remote queries"
        return result

    try:
        # 获取信号量信息（本地/远程分支）
        if host and username and password:
            # 远程查询
            raw_info = _get_remote_signals(host, username, password, port)
            result["message"] = f"成功获取远程主机 {host} 的信号量信息"if KillCommandConfig().get_config().public_config.language == LanguageEnum.ZH else f"Successfully obtained semaphore information for remote host {host}"
        else:
            # 本地查询
            raw_info = _get_local_signals()
            result["message"] = "成功获取本地主机的信号量信息"if KillCommandConfig().get_config().public_config.language == LanguageEnum.ZH else "Successfully obtained semaphore information for the local host"

        # 格式化结果
        result["success"] = True
        result["data"] = _format_signal_info(raw_info, host or "localhost")

    except Exception as e:
        logger.error(f"获取信号量信息失败: {str(e)}"if KillCommandConfig().get_config().public_config.language == LanguageEnum.ZH else f"Failed to obtain semaphore information: {str(e)}")
        result["message"] = f"获取信号量信息失败: {str(e)}"if KillCommandConfig().get_config().public_config.language == LanguageEnum.ZH else f"Failed to obtain semaphore information: {str(e)}"

    return result
if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='sse')