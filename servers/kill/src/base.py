import subprocess
from asyncio.log import logger
import socket
from typing import Dict, Optional, Tuple
import paramiko
from paramiko.ssh_exception import (
    SSHException, AuthenticationException, NoValidConnectionsError
)

from config.private.kill.config_loader import KillCommandConfig
from config.public.base_config_loader import LanguageEnum
class ProcessControlUtil:
    """进程控制工具类（封装核心逻辑，无外部模块依赖）"""

    @staticmethod
    def _resolve_host(host: str) -> str:
        """解析主机到IP（纯标准库实现，无外部依赖）"""
        # 根据配置获取语言
        is_zh = KillCommandConfig().get_config().public_config.language == LanguageEnum.ZH
        try:
            return socket.gethostbyname(host)
        except socket.gaierror:
            logger.warning("主机解析失败，返回原始主机名" if is_zh else "Host resolution failed, returning original hostname")
            return host  # 解析失败返回原始值

    @staticmethod
    def _is_local(host: str) -> bool:
        # 根据配置获取语言
        is_zh = KillCommandConfig().get_config().public_config.language == LanguageEnum.ZH
        logger.info("判断是否为本地主机" if is_zh else "Checking if it's a local host")
        """判断是否为本地主机（仓库风格：简洁实现）"""
        if host is None:
            return True
        
        local_ips = {"localhost", "127.0.0.1", socket.gethostname()}
        try:
            local_ips.add(socket.gethostbyname(socket.gethostname()))
        except socket.gaierror:
            logger.warning("获取本地主机IP失败" if is_zh else "Failed to get local host IP")
            pass
        return host in local_ips or ProcessControlUtil._resolve_host(host) in local_ips

    @staticmethod
    def _validate_pid(pid: int) -> Tuple[bool, str]:
        """验证PID（仓库参数校验风格）"""
        # 根据配置获取语言
        is_zh = KillCommandConfig().get_config().public_config.language == LanguageEnum.ZH
        if not isinstance(pid, int) or pid <= 0:
            return False, "PID必须是正整数" if is_zh else "PID must be a positive integer"
        return True, ""

    @staticmethod
    def _ssh_connect(host: str, port: int, user: str, pwd: str) -> Tuple[Optional[paramiko.SSHClient], str]:
        """SSH连接（仓库网络工具实现风格）"""
        # 根据配置获取语言
        is_zh = KillCommandConfig().get_config().public_config.language == LanguageEnum.ZH
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=host,
                port=port,
                username=user,
                password=pwd,
                timeout=10  # 仓库默认超时设置
            )
            return ssh, ""
        except AuthenticationException:
            return None, "认证失败（用户名/密码错误）" if is_zh else "Authentication failed (username/password error)"
        except SSHException:
            return None, "连接超时（10秒）" if is_zh else "Connection timed out (10 seconds)"
        except Exception as e:
            return None, f"连接失败: {str(e)}" if is_zh else f"Connection failed: {str(e)}"

    @staticmethod
    def _exec_ssh_cmd(ssh: paramiko.SSHClient, cmd: str) -> Tuple[str, str]:
        """执行SSH命令（仓库命令执行风格）"""
        # 根据配置获取语言
        is_zh = KillCommandConfig().get_config().public_config.language == LanguageEnum.ZH
        try:
            stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
            return stdout.read().decode().strip(), stderr.read().decode().strip()
        except Exception as e:
            return "", f"命令执行失败: {str(e)}" if is_zh else f"Command execution failed: {str(e)}"
        


def _get_local_signals() -> str:
    """获取本地服务器的信号量信息"""
    # 根据配置获取语言
    is_zh = KillCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    try:
        # 执行kill -l获取信号列表
        kill_result = subprocess.run(
            ["kill", "-l"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )
        if kill_result.stderr:
            return (f"本地获取信号列表失败: {kill_result.stderr}" 
                    if is_zh else f"Failed to get local signal list: {kill_result.stderr}")

        # 执行man kill获取详细说明
        man_result = subprocess.run(
            ["man", "kill"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        
        return (f"信号量列表:\n{kill_result.stdout}\n\n详细说明:\n{man_result.stdout}"
                if is_zh else f"Signal list:\n{kill_result.stdout}\n\nDetailed description:\n{man_result.stdout}")
        
    except Exception as e:
        return (f"本地获取信号信息出错: {str(e)}"
                if is_zh else f"Error getting local signal info: {str(e)}")


def _get_remote_signals(
    host: str,
    username: str,
    password: str,
    port: int = 22
) -> str:
    """获取远程服务器的信号量信息"""
    # 根据配置获取语言
    is_zh = KillCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    ssh: Optional[paramiko.SSHClient] = None
    try:
        # 建立SSH连接
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=host,
            port=port,
            username=username,
            password=password,
            timeout=10
        )

        # 远程执行kill -l获取信号列表
        stdin, stdout, stderr = ssh.exec_command("kill -l", timeout=5)
        signal_list = stdout.read().decode()
        error = stderr.read().decode()
        if error:
            return (f"远程获取信号列表失败: {error}"
                    if is_zh else f"Failed to get remote signal list: {error}")

        # 远程执行man kill获取详细说明
        stdin, stdout, stderr = ssh.exec_command("man kill", timeout=10)
        man_output = stdout.read().decode()
        man_error = stderr.read().decode()
        if man_error:
            return (f"远程获取详细说明失败: {man_error}\n信号量列表:\n{signal_list}"
                    if is_zh else f"Failed to get remote details: {man_error}\nSignal list:\n{signal_list}")

        return (f"信号量列表:\n{signal_list}\n\n详细说明:\n{man_output}"
                if is_zh else f"Signal list:\n{signal_list}\n\nDetailed description:\n{man_output}")

    except AuthenticationException:
        return "SSH认证失败（用户名/密码错误）" if is_zh else "SSH authentication failed (username/password error)"
    except NoValidConnectionsError:
        return (f"无法连接到远程主机 {host}:{port}"
                if is_zh else f"Could not connect to remote host {host}:{port}")
    except SSHException as e:
        return (f"SSH协议错误或者连接超时: {str(e)}"
                if is_zh else f"SSH protocol error or connection timeout: {str(e)}")
    except Exception as e:
        return (f"远程获取信号信息出错: {str(e)}"
                if is_zh else f"Error getting remote signal info: {str(e)}")
    finally:
        if ssh:
            ssh.close()


def _format_signal_info(raw_info: str, host: str) -> Dict:
    """格式化信号量信息"""
    # 根据配置获取语言
    is_zh = KillCommandConfig().get_config().public_config.language == LanguageEnum.ZH
    
    # 预定义常见信号量（作为备份）
    common_signals = {
        1: ("SIGHUP - 挂起信号，通常用于重新加载配置" 
            if is_zh else "SIGHUP - Hangup signal, usually used to reload configuration"),
        2: ("SIGINT - 中断信号，相当于Ctrl+C" 
            if is_zh else "SIGINT - Interrupt signal, equivalent to Ctrl+C"),
        3: ("SIGQUIT - 退出信号，通常会产生核心转储" 
            if is_zh else "SIGQUIT - Quit signal, usually produces core dump"),
        9: ("SIGKILL - 强制终止信号，进程无法捕获或忽略" 
            if is_zh else "SIGKILL - Force termination signal, cannot be caught or ignored"),
        15: ("SIGTERM - 终止信号，进程可以捕获并优雅退出（默认信号）" 
            if is_zh else "SIGTERM - Termination signal, process can catch and exit gracefully (default)"),
        18: ("SIGCONT - 继续信号，用于恢复被暂停的进程" 
            if is_zh else "SIGCONT - Continue signal, used to resume paused processes"),
        19: ("SIGSTOP - 暂停信号，进程无法捕获或忽略" 
            if is_zh else "SIGSTOP - Stop signal, cannot be caught or ignored"),
        20: ("SIGTSTP - 终端暂停信号，相当于Ctrl+Z" 
            if is_zh else "SIGTSTP - Terminal stop signal, equivalent to Ctrl+Z")
    }

    # 提取完整信号列表
    raw_lines = raw_info.split("\n")
    signal_list_line = ""
    for i, line in enumerate(raw_lines):
        signal_list_keyword = "信号量列表:" if is_zh else "Signal list:"
        if signal_list_keyword in line and i + 1 < len(raw_lines):
            signal_list_line = raw_lines[i + 1].strip()

    return {
        "common_signals": common_signals,
        "full_signal_list": (signal_list_line if signal_list_line 
                           else ("获取信号列表失败" if is_zh else "Failed to get signal list")),
        "detailed_description": raw_info,
        "note": ("信号量编号可能因系统略有差异，SIGKILL(9)和SIGSTOP(19)无法被进程捕获" 
                if is_zh else "Signal numbers may vary slightly by system; SIGKILL(9) and SIGSTOP(19) cannot be caught"),
        "host": host  # 标识信息来源主机
    }