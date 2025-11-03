import time
import subprocess
from typing import Dict, Optional
import paramiko
from config.private.nohup.config_loader import NohupCommandConfig
from mcp.server import FastMCP
from config.public.base_config_loader import LanguageEnum
from servers.nohup.src.base import _is_local_process_exist, _is_remote_process_exist
mcp = FastMCP("nohup MCP Server", host="0.0.0.0", port=NohupCommandConfig().get_config().private_config.port)


def get_language_config() -> bool:
    """获取语言配置：True=中文，False=英文（避免重复调用配置类）"""
    return NohupCommandConfig().get_config().public_config.language == LanguageEnum.ZH


@mcp.tool(
    name="run_with_nohup" if get_language_config() else "run_with_nohup",
    description="""
    在本地或远程服务器使用nohup运行命令（远程需提供SSH信息）
    1. 输入值如下：
        - command: 要执行的命令，必填项
        - host: 远程主机IP或hostname，不提供则表示本地执行
        - port: SSH端口，默认22，远程连接时使用
        - username: SSH用户名，远程连接时需要
        - password: SSH密码，远程连接时需要
        - output_file: 输出日志文件路径，可选
        - working_dir: 工作目录，可选
    2. 返回值为包含执行结果的字典，包含以下键
        - success: 布尔值，表示执行是否成功
        - message: 执行结果消息
        - pid: 进程ID，成功时返回
        - output_file: 输出日志文件路径
        - command: 执行的命令
        - host: 执行命令的主机
    """
    if get_language_config() else
    """
    Run commands using nohup on local or remote servers (SSH information required for remote execution)
    1. Input values are as follows:
        - command: The command to execute, required
        - host: Remote host IP or hostname, local execution if not provided
        - port: SSH port, default 22, used for remote connection
        - username: SSH username, required for remote connection
        - password: SSH password, required for remote connection
        - output_file: Output log file path, optional
        - working_dir: Working directory, optional
    2. The return value is a dictionary containing execution results with the following keys
        - success: Boolean indicating whether execution was successful
        - message: Execution result message
        - pid: Process ID, returned on success
        - output_file: Output log file path
        - command: Executed command
        - host: Host where the command was executed
    """
)
def run_with_nohup(
    command: str,
    host: Optional[str] = None,
    port: int = 22,
    username: Optional[str] = None,
    password: Optional[str] = None,
    output_file: Optional[str] = None,
    working_dir: Optional[str] = None
) -> Dict:
    is_zh = get_language_config()
    target_host = host or "localhost"

    # 初始化返回结果：严格匹配模板定义的所有键，结构固定
    result = {
        "success": False,
        "message": "",
        "pid": None,
        "output_file": output_file,
        "command": command.strip(),
        "host": target_host
    }

    try:
        # 1. 基础参数校验：仅保留核心必选校验（其他错误由终端直接返回）
        if not result["command"]:
            result["message"] = "命令不能为空" if is_zh else "Command cannot be empty"
            return result

        # 2. 处理日志文件：无路径时自动生成默认路径（本地/远程统一规则）
        if not output_file:
            default_filename = f"nohup_output_{int(time.time())}_{target_host.replace('.', '_')}.log"
            output_file = f"/tmp/{default_filename}"
            result["output_file"] = output_file

        # 3. 构建nohup命令：统一格式（包含日志重定向、工作目录切换）
        nohup_cmd = ["nohup"]
        # 若指定工作目录，先切换目录
        if working_dir:
            nohup_cmd.extend(["cd", working_dir, "&&"])
        # 追加目标命令+日志重定向（覆盖模式）
        nohup_cmd.extend([result["command"], ">", output_file, "2>&1", "&", "echo", "$!"])

        # 4. 本地执行逻辑：直接调用subprocess，返回原始错误
        if not host:
            try:
                # 执行命令并获取进程PID（shell=True支持命令组合）
                output = subprocess.check_output(
                    " ".join(nohup_cmd),
                    shell=True,
                    text=True,
                    stderr=subprocess.STDOUT  # 合并 stderr 到 stdout，统一捕获错误
                )
                # 解析PID（nohup后台运行后echo $!的输出）
                pid = output.strip()
                if not pid.isdigit():
                    raise RuntimeError(f"无法解析进程PID，命令输出：{output}")

                # 验证PID是否存在（确保进程启动成功）
                if not _is_local_process_exist(int(pid)):
                    raise RuntimeError(f"进程PID {pid} 启动后立即退出")

                # 填充成功结果
                result["success"] = True
                result["pid"] = int(pid)
                result[
                    "message"] = f"本地nohup命令启动成功（PID：{pid}），日志文件：{output_file}" if is_zh else f"Local nohup command started successfully (PID: {pid}), log file: {output_file}"
                return result

            except subprocess.CalledProcessError as e:
                # 直接返回终端错误（如命令不存在、权限不足）
                result["message"] = f"本地执行失败：{e.output.strip()}" if is_zh else f"Local execution failed: {e.output.strip()}"
                return result
            except Exception as e:
                result["message"] = f"本地执行异常：{str(e)}" if is_zh else f"Local execution exception: {str(e)}"
                return result

        # 5. 远程执行逻辑：配置优先+SSH连接，简化错误处理
        else:
            # 5.1 匹配远程配置（优先使用NohupCommandConfig中的主机信息）
            matched_config = None
            for cfg in NohupCommandConfig().get_config().public_config.remote_hosts:
                if host in [cfg.name, cfg.host]:
                    matched_config = cfg
                    break
            # 整理连接信息：配置存在则覆盖手动传入参数
            remote_conn = {
                "host": matched_config.host if matched_config else host,
                "port": matched_config.port if (matched_config and matched_config.port) else port,
                "user": matched_config.username if matched_config else username,
                "pwd": matched_config.password if matched_config else password
            }

            # 5.2 校验远程连接参数（避免空值）
            if not (remote_conn["user"] and remote_conn["pwd"]):
                result["message"] = "远程执行需提供username和password" if is_zh else "Username and password are required for remote execution"
                return result

            # 5.3 建立SSH连接并执行命令
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # 自动接受未知主机密钥
            try:
                # 连接SSH（超时10秒，避免长时间阻塞）
                ssh.connect(
                    hostname=remote_conn["host"],
                    port=remote_conn["port"],
                    username=remote_conn["user"],
                    password=remote_conn["pwd"],
                    timeout=10
                )

                # 执行远程nohup命令（拼接为字符串，支持工作目录切换）
                remote_cmd = " ".join(nohup_cmd)
                stdin, stdout, stderr = ssh.exec_command(remote_cmd)
                # 读取输出和错误（需等待命令执行完成）
                stdout_msg = stdout.read().decode("utf-8").strip()
                stderr_msg = stderr.read().decode("utf-8").strip()

                # 处理执行结果
                if stderr_msg:
                    result["message"] = f"远程执行失败：{stderr_msg}" if is_zh else f"Remote execution failed: {stderr_msg}"
                    return result

                # 解析远程进程PID
                if not stdout_msg.isdigit():
                    result["message"] = f"无法解析远程PID，命令输出：{stdout_msg}" if is_zh else f"Cannot parse remote PID, command output: {stdout_msg}"
                    return result
                remote_pid = int(stdout_msg)

                # 验证远程PID是否存在（通过ps命令确认）
                if not _is_remote_process_exist(ssh, remote_pid):
                    result["message"] = f"远程进程PID {remote_pid} 启动后立即退出" if is_zh else f"Remote process PID {remote_pid} exited immediately after startup"
                    return result

                # 填充远程执行成功结果
                result["success"] = True
                result["pid"] = remote_pid
                result[
                    "message"] = f"远程nohup命令启动成功（主机：{remote_conn['host']}，PID：{remote_pid}），日志文件：{output_file}" if is_zh else f"Remote nohup command started successfully (host: {remote_conn['host']}, PID: {remote_pid}), log file: {output_file}"
                return result

            except Exception as e:
                # 直接返回SSH相关错误（连接超时、认证失败等）
                result["message"] = f"远程操作异常：{str(e)}" if is_zh else f"Remote operation exception: {str(e)}"
                return result
            finally:
                # 确保SSH连接关闭，避免资源泄漏
                ssh.close()

    except Exception as e:
        # 全局异常捕获：直接返回原始错误信息
        result["message"] = f"操作异常：{str(e)}" if is_zh else f"Operation exception: {str(e)}"
        return result




if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='sse')