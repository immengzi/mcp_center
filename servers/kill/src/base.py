from asyncio.log import logger
import subprocess
from typing import Dict, List, Optional, Tuple
import paramiko
from config.private.kill.config_loader import KillCommandConfig
from config.public.base_config_loader import LanguageEnum


def get_language() -> bool:
    """获取语言配置（True为中文，False为英文）"""
    return KillCommandConfig().get_config().public_config.language == LanguageEnum.ZH

def get_remote_config(host: str) -> Optional[Dict]:
    """从配置文件获取远程主机配置"""
    remote_hosts = KillCommandConfig().get_config().public_config.remote_hosts
    for host_config in remote_hosts:
        if host == host_config.host or host == host_config.name:
            return {
                "host": host_config.host,
                "port": host_config.port or 22,
                "username": host_config.username,
                "password": host_config.password
            }
    return None


def create_ssh_connection(host: str) -> Optional[paramiko.SSHClient]:
    """创建SSH连接（基于配置文件）"""
    config = get_remote_config(host)
    if not config:
        logger.error(f"未找到主机{host}的配置信息")
        return None

    required_fields = ["username", "password"]
    for field in required_fields:
        if not config.get(field):
            logger.error(f"主机{host}的配置缺少{field}")
            return None

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=config["host"],
            port=config["port"],
            username=config["username"],
            password=config["password"],
            banner_timeout=10
        )
        return ssh
    except paramiko.AuthenticationException:
        logger.error(f"主机{host}认证失败")
    except Exception as e:
        logger.error(f"连接主机{host}失败: {str(e)}")
    return None


def execute_local_command(command: str) -> Tuple[bool, str, str]:
    """执行本地命令"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return (
            result.returncode == 0,
            result.stdout.strip(),
            result.stderr.strip()
        )
    except Exception as e:
        return False, "", str(e)


def execute_remote_command(ssh: paramiko.SSHClient, command: str) -> Tuple[bool, str, str]:
    """执行远程命令"""
    try:
        stdin, stdout, stderr = ssh.exec_command(command)
        stdout_output = stdout.read().decode().strip()
        stderr_output = stderr.read().decode().strip()
        return True, stdout_output, stderr_output
    except Exception as e:
        return False, "", str(e)

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