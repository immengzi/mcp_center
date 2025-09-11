from typing import Dict, Optional
from mcp.server import FastMCP

from config.private.strace.config_loader import StraceCommandConfig
from config.public.base_config_loader import LanguageEnum
from servers.strace.src.base import _run_local_error_tracking, _run_local_freeze_tracking, _run_local_network_tracking, _run_local_strace_track, _run_remote_error_tracking, _run_remote_freeze_tracking, _run_remote_network_tracking, _run_remote_strace_track
mcp = FastMCP("strace MCP Server", host="0.0.0.0", port=StraceCommandConfig().get_config().private_config.port)

@mcp.tool(
    name="strace_track_file_process"
    if StraceCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    else "strace_track_file_process",
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
        - message: 跟踪结果消息
        - strace_pid: strace进程ID，成功时返回
        - output_file: 跟踪日志文件路径
        - target_pid: 目标进程PID
        - host: 跟踪的主机
    """
    if StraceCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    else
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
        - message: Tracking result message
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
    # 根据配置获取语言
    is_zh = StraceCommandConfig().get_config().public_config.language == LanguageEnum.ZH

    # 基础参数校验
    if pid <= 0:
        return {
            "success": False,
            "message": "PID必须是正整数" if is_zh else "PID must be a positive integer",
            "target_pid": pid,
            "host": host or "localhost"
        }

    # 远程参数校验
    if host:
        if not username or not password:
            return {
                "success": False,
                "message": "远程跟踪需同时提供username和password" if is_zh else "Username and password must be provided for remote tracking",
                "target_pid": pid,
                "host": host
            }
        return _run_remote_strace_track(
            pid=pid, host=host, port=port, username=username, password=password,
            output_file=output_file, follow_children=follow_children, duration=duration
        )
    else:
        return _run_local_strace_track(
            pid=pid, output_file=output_file, follow_children=follow_children, duration=duration
        )
        
        
@mcp.tool(
    name="strace_check_permission_file"
    if StraceCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    else "strace_check_permission_file",
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
    if StraceCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    else
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
    # 根据配置获取语言
    is_zh = StraceCommandConfig().get_config().public_config.language == LanguageEnum.ZH

    if pid <= 0 or duration <= 0:
        return {
            "success": False, 
            "message": "PID和跟踪时长必须是正整数" if is_zh else "PID and tracking duration must be positive integers"
        }

    if host:
        if not username or not password:
            return {
                "success": False, 
                "message": "远程跟踪需提供username和password" if is_zh else "Username and password are required for remote tracking"
            }
        return _run_remote_error_tracking(
            pid=pid, host=host, port=port, username=username, password=password,
            output_file=output_file, duration=duration
        )
    else:
        return _run_local_error_tracking(
            pid=pid, output_file=output_file, duration=duration
        )
        

@mcp.tool(
    name="strace_check_network"
    if StraceCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    else "strace_check_network",
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
    if StraceCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    else
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

    # 根据配置获取语言
    is_zh = StraceCommandConfig().get_config().public_config.language == LanguageEnum.ZH

    if pid <= 0 or duration <= 0:
        return {
            "success": False,
            "message": "PID和跟踪时长必须是正整数" if is_zh else "PID and tracking duration must be positive integers"
        }

    if host:
        if not username or not password:
            return {
                "success": False,
                "message": "远程跟踪需提供username和password" if is_zh else "Username and password are required for remote tracking"
            }
        return _run_remote_network_tracking(
            pid=pid, host=host, port=port, username=username, password=password,
            output_file=output_file, duration=duration, trace_dns=trace_dns
        )
    else:
        return _run_local_network_tracking(
            pid=pid, output_file=output_file, duration=duration, trace_dns=trace_dns
        )

@mcp.tool(
    name="strace_locate_freeze"
    if StraceCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    else "strace_locate_freeze",
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
    if StraceCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    else
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
    """
    功能4：定位进程卡顿的原因
    """
# 根据配置获取语言
    is_zh = StraceCommandConfig().get_config().public_config.language == LanguageEnum.ZH

    if pid <= 0 or duration <= 0 or slow_threshold <= 0:
        return {
            "success": False,
            "message": "PID、跟踪时长和慢操作阈值必须是正数" 
            if is_zh else "PID, tracking duration and slow operation threshold must be positive numbers"
        }

    if host:
        if not username or not password:
            return {
                "success": False,
                "message": "远程跟踪需提供username和password" 
                if is_zh else "Username and password are required for remote tracking"
            }
        return _run_remote_freeze_tracking(
            pid=pid, host=host, port=port, username=username, password=password,
            output_file=output_file, duration=duration, slow_threshold=slow_threshold
        )
    else:
        return _run_local_freeze_tracking(
            pid=pid, output_file=output_file, duration=duration, slow_threshold=slow_threshold
        )


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='sse')