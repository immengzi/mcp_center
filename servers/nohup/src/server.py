from typing import Dict, Optional
from config.private.nohup.config_loader import NohupCommandConfig
from mcp.server import FastMCP

from config.public.base_config_loader import LanguageEnum
from servers.nohup.src.base import _run_local_nohup, _run_remote_nohup
mcp = FastMCP("nohup MCP Server", host="0.0.0.0", port=NohupCommandConfig().get_config().private_config.port)

@mcp.tool(
    name="run_with_nohup"
    if NohupCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    else "run_with_nohup",
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
    if NohupCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    else
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
    # 基础参数校验
    is_zh = NohupCommandConfig().get_config().public_config.language == LanguageEnum.ZH

    if not command.strip():
        return {
            "success": False,
            "message": "命令不能为空" if is_zh else "Command cannot be empty",
            "pid": None,
            "host": host or "localhost"
        }

    # 远程执行条件判断（必须提供host、username、password）
    if host and (not username or not password):
        return {
            "success": False,
            "message": "远程执行需提供username和password" if is_zh else "Username and password are required for remote execution",
            "pid": None,
            "host": host
        }

    # 执行逻辑分支
    if host and username and password:
        # 远程执行
        return _run_remote_nohup(
            command=command,
            host=host,
            port=port,
            username=username,
            password=password,
            output_file=output_file,
            working_dir=working_dir
        )
    else:
        # 本地执行
        return _run_local_nohup(
            command=command,
            output_file=output_file,
            working_dir=working_dir
        )

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='sse')