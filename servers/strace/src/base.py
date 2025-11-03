
import re
import os
from typing import Dict, Optional



def _parse_strace_log(log_path: str) -> Dict[str, Dict]:
    """解析strace日志，统计'权限不足'和'文件找不到'错误（通用工具函数）"""
    error_stats = {
        "permission_denied": {"count": 0, "files": []},
        "file_not_found": {"count": 0, "files": []}
    }

    if not os.path.exists(log_path):
        return error_stats

    # 读取日志并匹配错误关键字
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # 匹配"权限不足"错误（对应EACCES）
            if "EACCES" in line:
                file_path = _extract_file_path(line)
                if file_path and file_path not in error_stats["permission_denied"]["files"]:
                    error_stats["permission_denied"]["files"].append(file_path)
                    error_stats["permission_denied"]["count"] += 1
            # 匹配"文件找不到"错误（对应ENOENT）
            elif "ENOENT" in line:
                file_path = _extract_file_path(line)
                if file_path and file_path not in error_stats["file_not_found"]["files"]:
                    error_stats["file_not_found"]["files"].append(file_path)
                    error_stats["file_not_found"]["count"] += 1

    return error_stats


def _extract_file_path(strace_line: str) -> Optional[str]:
    """从strace日志行中提取文件路径（简化正则，适配常见格式）"""
    import re
    # 匹配常见格式：openat("/path/to/file", ...) 或 access("/path/to/file", ...)
    match = re.search(r'(\w+)\("([^"]+)"', strace_line)
    if match and match.group(2):
        return match.group(2)
    return None


def _parse_network_log(log_path: str) -> Dict[str, Dict]:
    """解析strace网络日志，统计常见网络错误（通用工具函数）"""
    error_stats = {
        "connection_refused": {"count": 0, "details": []},
        "connection_timeout": {"count": 0, "details": []},
        "dns_failure": {"count": 0, "details": []},
        "other_network_errors": {"count": 0, "details": []}
    }

    # 日志不存在时返回空统计
    if not os.path.exists(log_path):
        return error_stats

    # 错误关键字映射：strace错误码 -> 错误类型
    error_keywords = {
        "ECONNREFUSED": ("connection_refused", "连接被拒绝"),
        "ETIMEDOUT": ("connection_timeout", "连接超时"),
        "EAI_FAIL": ("dns_failure", "DNS解析失败"),
        "EAI_NONAME": ("dns_failure", "DNS域名不存在"),
        "ENETUNREACH": ("other_network_errors", "网络不可达"),
        "EHOSTUNREACH": ("other_network_errors", "主机不可达")
    }

    # 读取日志并匹配错误
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            # 匹配已知错误类型
            matched = False
            for err_code, (err_type, err_desc) in error_keywords.items():
                if err_code in line:
                    # 提取关键信息：目标IP/端口（connect）或域名（DNS）
                    detail = _extract_network_detail(line, err_type)
                    if detail not in error_stats[err_type]["details"]:
                        error_stats[err_type]["details"].append(detail)
                        error_stats[err_type]["count"] += 1
                    matched = True
                    break

            # 其他网络错误（未匹配到已知错误码，但包含网络调用失败）
            if not matched and ("connect(" in line or "sendto(" in line) and "= -1" in line:
                detail = line[:100]  # 截取前100字符避免过长
                if detail not in error_stats["other_network_errors"]["details"]:
                    error_stats["other_network_errors"]["details"].append(detail)
                    error_stats["other_network_errors"]["count"] += 1

    return error_stats


def _extract_network_detail(log_line: str, err_type: str) -> str:
    """从日志行中提取网络错误详情（IP/端口或域名）"""
    # DNS错误：提取域名（如getaddrinfo("example.com", ...)）
    if err_type == "dns_failure":
        dns_match = re.search(r'get(addrinfo|hostbyname2?)\("([^"]+)"', log_line)
        if dns_match:
            return f"域名：{dns_match.group(2)}"
    # 连接错误：提取IP和端口（如connect(3, {sa_family=2, sin_port=htons(80), sin_addr=inet_addr("1.2.3.4")}, ...)）
    elif err_type in ["connection_refused", "connection_timeout"]:
        ip_match = re.search(r'inet_addr\("([\d.]+)"', log_line)
        port_match = re.search(r'sin_port=htons\((\d+)\)', log_line)
        if ip_match and port_match:
            return f"IP：{ip_match.group(1)}，端口：{port_match.group(1)}"
    # 其他错误：返回原始调用片段
    return log_line[:80] + "..." if len(log_line) > 80 else log_line


def _parse_freeze_log(log_path: str, slow_threshold: float) -> Dict[str, Dict]:
    """解析strace卡顿日志：统计慢操作、阻塞类型、总调用数"""
    analysis = {
        "slow_operations": {"count": 0, "details": []},
        "blocking_categories": {
            "io_block": {"count": 0, "details": []},
            "lock_wait": {"count": 0, "details": []},
            "syscall_block": {"count": 0, "details": []}
        },
        "total_syscalls": 0
    }

    # 日志不存在时返回空分析
    if not os.path.exists(log_path):
        return analysis

    # 阻塞类型映射：系统调用 -> 阻塞分类
    blocking_syscalls = {
        # IO阻塞相关调用（文件/网络/管道）
        "io_block": ["open", "read", "write", "recv", "send", "accept", "connect", "poll", "select", "epoll_wait"],
        # 锁等待相关调用
        "lock_wait": ["futex", "pthread_mutex_lock", "pthread_rwlock_lock"],
        # 其他系统调用阻塞
        "syscall_block": ["waitpid", "sleep", "nanosleep", "clock_nanosleep"]
    }

    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            # 提取系统调用耗时（strace -r输出的第一列，格式：0.000123）
            time_match = re.match(r'^(\d+\.\d+)', line)
            if not time_match:
                continue  # 非系统调用行（如进程退出信息）

            syscall_time = float(time_match.group(1))
            analysis["total_syscalls"] += 1  # 累计总调用数

            # 1. 统计慢操作（耗时超阈值）
            if syscall_time >= slow_threshold:
                # 提取时间、调用名、关键参数（前120字符避免过长）
                time_str = re.search(r'(\d+:\d+:\d+)', line)
                time_str = time_str.group(1) if time_str else "未知时间"
                syscall_name = re.search(r' (\w+)\(', line)
                syscall_name = syscall_name.group(1) if syscall_name else "未知调用"
                detail = f"时间：{time_str}，调用：{syscall_name}，耗时：{syscall_time:.6f}秒，详情：{line[:120]}"
                analysis["slow_operations"]["details"].append(detail)
                analysis["slow_operations"]["count"] += 1

            # 2. 统计阻塞类型（按系统调用分类）
            syscall_name = re.search(r' (\w+)\(', line)
            if not syscall_name:
                continue
            syscall_name = syscall_name.group(1)

            # 匹配IO阻塞
            if syscall_name in blocking_syscalls["io_block"]:
                detail = f"调用：{syscall_name}，耗时：{syscall_time:.6f}秒，详情：{line[:100]}"
                analysis["blocking_categories"]["io_block"]["details"].append(detail)
                analysis["blocking_categories"]["io_block"]["count"] += 1
            # 匹配锁等待
            elif syscall_name in blocking_syscalls["lock_wait"]:
                detail = f"调用：{syscall_name}，耗时：{syscall_time:.6f}秒，详情：{line[:100]}"
                analysis["blocking_categories"]["lock_wait"]["details"].append(detail)
                analysis["blocking_categories"]["lock_wait"]["count"] += 1
            # 匹配其他系统调用阻塞
            elif syscall_name in blocking_syscalls["syscall_block"]:
                detail = f"调用：{syscall_name}，耗时：{syscall_time:.6f}秒，详情：{line[:100]}"
                analysis["blocking_categories"]["syscall_block"]["details"].append(detail)
                analysis["blocking_categories"]["syscall_block"]["count"] += 1

    return analysis
