import logging
import time
import os
from typing import Dict  
from config.private.qemu.config_loader import QemuConfig
from servers.qemu.src.base import get_language, get_remote_auth, execute_remote_command, execute_local_command, parse_vm_list, parse_stopped_vms
from mcp.server import FastMCP

# 初始化MCP服务
mcp = FastMCP(
    "QEMU Virtual Machine Management MCP",
    host="0.0.0.0",
    port=QemuConfig().get_config().private_config.port
)

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)



@mcp.tool(
    name="manage_vm" if get_language() else "manage_vm",
    description="""
    虚拟机全生命周期管理（创建/启动/停止/删除/修改配置）
    
    参数:
        -name: 虚拟机名称（必填，唯一标识）
        -action: 操作类型（create/start/stop/delete/modify，必填）
        -arch: CPU架构（create时必填，x86_64/arm64/ppc64）
        -memory: 内存大小（create/modify可选，如2G/4096M，默认2G）
        -disk: 磁盘配置（create/modify可选，格式"path=/data/vm/disk.qcow2,size=20G"）
        -iso: 系统镜像路径（create可选，如/data/iso/ubuntu.iso）
        -vcpus: CPU核心数（create/modify可选，默认2核）
        -vm_dir: 虚拟机存储目录（create可选，默认/var/lib/qemu）
        -host: 远程主机名/IP（默认localhost）
        -ssh_port: SSH端口（默认22）
    
    返回:
        -success: 操作是否成功
        -message: 操作结果描述
        -data: 虚拟机操作信息
    """ if get_language() else """
    Virtual machine lifecycle management (create/start/stop/delete/modify configuration)
    
    Parameters:
        -name: VM name (required, unique identifier)
        -action: Operation type (create/start/stop/delete/modify, required)
        -arch: CPU architecture (required for create, x86_64/arm64/ppc64)
        -memory: Memory size (optional for create/modify, e.g., 2G/4096M, default 2G)
        -disk: Disk configuration (optional for create/modify, format "path=/data/vm/disk.qcow2,size=20G")
        -iso: System image path (optional for create, e.g., /data/iso/ubuntu.iso)
        -vcpus: Number of CPU cores (optional for create/modify, default 2)
        -vm_dir: VM storage directory (optional for create, default /var/lib/qemu)
        -host: Remote hostname/IP (default localhost)
        -ssh_port: SSH port (default 22)
    
    Returns:
        -success: Operation success status
        -message: Operation result description
        -data: VM operation information
    """
)
def manage_vm(
    name: str,
    action: str,
    arch: str = "",
    memory: str = "2G",
    disk: str = "",
    iso: str = "",
    vcpus: int = 2,
    vm_dir: str = "/var/lib/qemu",
    host: str = "localhost",
    ssh_port: int = 22
) -> Dict:
    is_zh = get_language()
    result = {
        "success": False,
        "message": "",
        "data": {
            "host": host,
            "vm_name": name,
            "action": action
        }
    }

    # 参数校验
    valid_actions = ["create", "start", "stop", "delete", "modify"]
    if action not in valid_actions:
        result["message"] = f"操作类型必须是{valid_actions}之一" if is_zh else f"Action must be one of {valid_actions}"
        return result
    
    valid_arch = ["x86_64", "arm64", "ppc64"]
    if action == "create" and (not arch or arch not in valid_arch):
        result["message"] = f"创建虚拟机必须指定架构（{valid_arch}）" if is_zh else f"Architecture ({valid_arch}) is required for create"
        return result
    
    if vcpus < 1:
        result["message"] = "CPU核心数必须≥1" if is_zh else "Number of vCPUs must be ≥1"
        return result
    
    # 解析磁盘参数
    disk_path = ""
    disk_size = ""
    if disk:
        disk_parts = dict(p.split('=') for p in disk.split(','))
        disk_path = disk_parts.get("path", "")
        disk_size = disk_parts.get("size", "")
        if not disk_path and action == "create":
            # 自动生成磁盘路径
            disk_path = f"{vm_dir}/{name}.qcow2"
            disk = f"path={disk_path},size={disk_size or '20G'}"

    # 构建QEMU命令
    command = ""
    qemu_bin = f"qemu-system-{arch}" if arch else "qemu-system-x86_64"  # 默认x86_64
    vm_pid_file = f"/var/run/qemu/{name}.pid"  # PID文件路径

    if action == "create":
        # 创建磁盘（如果不存在）
        if not disk_path:
            disk_path = f"{vm_dir}/{name}.qcow2"
            disk_size = disk_size or "20G"
        create_disk_cmd = f"qemu-img create -f qcow2 {disk_path} {disk_size}" if not os.path.exists(disk_path) else ""
        
        # 构建启动命令（后台运行）
        iso_param = f"-cdrom {iso}" if iso else ""
        start_cmd = (
            f"{qemu_bin} -name {name} -m {memory} -smp cpus={vcpus} "
            f"-drive file={disk_path},format=qcow2 {iso_param} "
            f"-daemonize -pidfile {vm_pid_file} -enable-kvm"
        )
        
        command = f"{create_disk_cmd} && {start_cmd}" if create_disk_cmd else start_cmd

    elif action == "start":
        # 启动已存在的虚拟机
        # 先查找磁盘文件确定架构
        find_disk_cmd = f"find {vm_dir} -name '{name}.qcow2' -o -name '{name}.raw' | head -n 1"
        if host in ["localhost", "127.0.0.1"]:
            disk_result = execute_local_command(find_disk_cmd)
        else:
            auth = get_remote_auth(host)
            if not auth:
                result["message"] = f"未找到远程主机{host}的认证配置" if is_zh else f"Auth config for {host} not found"
                return result
            auth["port"] = ssh_port
            disk_result = execute_remote_command(auth, find_disk_cmd)
        
        if not disk_result["success"] or not disk_result["output"]:
            result["message"] = f"未找到虚拟机{name}的磁盘文件" if is_zh else f"Disk file for VM {name} not found"
            return result
        
        disk_path = disk_result["output"].strip()
        iso_param = f"-cdrom {iso}" if iso else ""
        command = (
            f"{qemu_bin} -name {name} -m {memory} -smp cpus={vcpus} "
            f"-drive file={disk_path},format=qcow2 {iso_param if 'iso' in locals() else ''} "
            f"-daemonize -pidfile {vm_pid_file} -enable-kvm"
        )

    elif action == "stop":
        # 停止虚拟机（通过PID文件）
        command = f"if [ -f {vm_pid_file} ]; then kill $(cat {vm_pid_file}) && rm -f {vm_pid_file}; fi"

    elif action == "delete":
        # 删除虚拟机（停止进程+删除磁盘）
        stop_cmd = f"if [ -f {vm_pid_file} ]; then kill $(cat {vm_pid_file}) && rm -f {vm_pid_file}; fi"
        delete_disk_cmd = f"find {vm_dir} -name '{name}.qcow2' -o -name '{name}.raw' | xargs rm -f"
        command = f"{stop_cmd} && {delete_disk_cmd}"

    elif action == "modify":
        # 修改配置需要先停止再重新启动
        if not memory and not disk and not vcpus:
            result["message"] = "修改操作至少需指定memory/disk/vcpus中的一项" if is_zh else "Modify requires at least one of memory/disk/vcpus"
            return result
        
        # 先停止虚拟机
        stop_cmd = f"if [ -f {vm_pid_file} ]; then kill $(cat {vm_pid_file}) && rm -f {vm_pid_file}; sleep 2; fi"
        
        # 处理磁盘扩容
        modify_disk_cmd = ""
        if disk and disk_size:
            modify_disk_cmd = f"qemu-img resize {disk_path} {disk_size}" if disk_path else ""
        
        # 重新启动（应用新配置）
        start_cmd = (
            f"{qemu_bin} -name {name} -m {memory} -smp cpus={vcpus} "
            f"-drive file={disk_path},format=qcow2 -daemonize -pidfile {vm_pid_file} -enable-kvm"
        )
        
        command_parts = [stop_cmd, modify_disk_cmd, start_cmd]
        command = " && ".join(filter(None, command_parts))

    # 执行命令
    if host in ["localhost", "127.0.0.1"]:
        exec_result = execute_local_command(command)
    else:
        auth = get_remote_auth(host)
        if not auth:
            result["message"] = f"未找到远程主机{host}的认证配置" if is_zh else f"Auth config for {host} not found"
            return result
        auth["port"] = ssh_port
        exec_result = execute_remote_command(auth, command)

    if exec_result["success"]:
        result["success"] = True
        result["message"] = f"虚拟机{name} {action}成功" if is_zh else f"VM {name} {action} succeeded"
        result["data"]["details"] = exec_result["output"]
    else:
        result["message"] = f"虚拟机{name} {action}失败：{exec_result['error']}" if is_zh else f"VM {name} {action} failed: {exec_result['error']}"

    return result


@mcp.tool(
    name="list_vms" if get_language() else "list_vms",
    description="""
    虚拟机列表查询（支持按状态、架构、名称筛选）
    
    参数:
        -status: 状态筛选（running/stopped/all，默认all）
        -arch: 架构筛选（x86_64/arm64/ppc64，可选）
        -filter_name: 名称模糊筛选（可选）
        -vm_dir: 虚拟机存储目录（默认/var/lib/qemu）
        -host: 远程主机名/IP（默认localhost）
        -ssh_port: SSH端口（默认22）
    
    返回:
        -success: 操作是否成功
        -message: 操作结果描述
        -data: 虚拟机列表及统计信息
    """ if get_language() else """
    VM list query (supports filtering by status, architecture, name)
    
    Parameters:
        -status: Status filter (running/stopped/all, default all)
        -arch: Architecture filter (x86_64/arm64/ppc64, optional)
        -filter_name: Name fuzzy filter (optional)
        -vm_dir: VM storage directory (default /var/lib/qemu)
        -host: Remote hostname/IP (default localhost)
        -ssh_port: SSH port (default 22)
    
    Returns:
        -success: Operation success status
        -message: Operation result description
        -data: VM list and statistics
    """
)
def list_vms(
    status: str = "all",
    arch: str = "",
    filter_name: str = "",
    vm_dir: str = "/var/lib/qemu",
    host: str = "localhost",
    ssh_port: int = 22
) -> Dict:
    is_zh = get_language()
    result = {
        "success": False,
        "message": "",
        "data": {
            "host": host,
            "vm_count": 0,
            "vms": [],
            "filter": {
                "status": status,
                "arch": arch,
                "filter_name": filter_name
            }
        }
    }

    # 参数校验
    valid_status = ["running", "stopped", "all"]
    if status not in valid_status:
        result["message"] = f"状态筛选必须是{valid_status}之一" if is_zh else f"Status must be one of {valid_status}"
        return result

    # 获取运行中的虚拟机
    running_vms = []
    if status in ["running", "all"]:
        # 通过ps命令查找QEMU进程
        command = "ps aux | grep 'qemu-system-' | grep -v grep"
        if host in ["localhost", "127.0.0.1"]:
            exec_result = execute_local_command(command)
        else:
            auth = get_remote_auth(host)
            if not auth:
                result["message"] = f"未找到远程主机{host}的认证配置" if is_zh else f"Auth config for {host} not found"
                return result
            auth["port"] = ssh_port
            exec_result = execute_remote_command(auth, command)
        
        if exec_result["success"]:
            running_vms = parse_vm_list(exec_result["output"])

    # 获取停止的虚拟机
    stopped_vms = []
    if status in ["stopped", "all"]:
        stopped_vms = parse_stopped_vms(vm_dir, host, ssh_port)

    # 合并并筛选虚拟机列表
    all_vms = running_vms + stopped_vms
    
    # 应用筛选条件
    filtered_vms = []
    for vm in all_vms:
        # 状态筛选
        if status != "all" and vm["status"] != status:
            continue
        # 架构筛选
        if arch and vm["arch"] != arch:
            continue
        # 名称筛选
        if filter_name and filter_name.lower() not in vm["name"].lower():
            continue
        filtered_vms.append(vm)

    # 去重（同名虚拟机只保留一个，以运行状态优先）
    unique_vms = {}
    for vm in filtered_vms:
        if vm["name"] not in unique_vms or vm["status"] == "running":
            unique_vms[vm["name"]] = vm
    filtered_vms = list(unique_vms.values())

    result["data"]["vms"] = filtered_vms
    result["data"]["vm_count"] = len(filtered_vms)
    result["success"] = True
    result["message"] = f"成功获取{status}虚拟机，共{len(filtered_vms)}个" if is_zh else f"Successfully obtained {status} VMs, total {len(filtered_vms)}"

    return result


@mcp.tool(
    name="monitor_vm_status" if get_language() else "monitor_vm_status",
    description="""
    虚拟机实时状态监控（CPU/内存/磁盘/网络）
    
    参数:
        -name: 虚拟机名称（必填）
        -metrics: 监控指标（cpu/memory/disk/network/all，默认all）
        -interval: 采样间隔（秒，默认5，最小1）
        -count: 采样次数（默认1，0表示持续采样直到停止）
        -host: 远程主机名/IP（默认localhost）
        -ssh_port: SSH端口（默认22）
    
    返回:
        -success: 操作是否成功
        -message: 操作结果描述
        -data: 监控指标数据
    """ if get_language() else """
    VM real-time status monitoring (CPU/memory/disk/network)
    
    Parameters:
        -name: VM name (required)
        -metrics: Monitoring metrics (cpu/memory/disk/network/all, default all)
        -interval: Sampling interval (seconds, default 5, min 1)
        -count: Sampling times (default 1, 0 means continuous sampling until stopped)
        -host: Remote hostname/IP (default localhost)
        -ssh_port: SSH port (default 22)
    
    Returns:
        -success: Operation success status
        -message: Operation result description
        -data: Monitoring metrics data
    """
)
def monitor_vm_status(
    name: str,
    metrics: str = "all",
    interval: int = 5,
    count: int = 1,
    host: str = "localhost",
    ssh_port: int = 22
) -> Dict:
    is_zh = get_language()
    result = {
        "success": False,
        "message": "",
        "data": {
            "host": host,
            "vm_name": name,
            "timestamp": [],
            "metrics_data": {}
        }
    }

    # 参数校验
    valid_metrics = ["cpu", "memory", "disk", "network", "all"]
    if metrics not in valid_metrics:
        result["message"] = f"监控指标必须是{valid_metrics}之一" if is_zh else f"Metrics must be one of {valid_metrics}"
        return result
    
    if interval < 1:
        result["message"] = "采样间隔必须≥1秒" if is_zh else "Sampling interval must be ≥1 second"
        return result
    
    if count < 0:
        result["message"] = "采样次数不能为负数" if is_zh else "Sampling count cannot be negative"
        return result
    
    # 检查虚拟机是否运行
    list_result = list_vms(status="running", filter_name=name, host=host, ssh_port=ssh_port)
    running_vm = next((vm for vm in list_result["data"]["vms"] if vm["name"] == name), None)
    if not running_vm:
        result["message"] = f"虚拟机{name}未运行，无法监控" if is_zh else f"VM {name} is not running, cannot monitor"
        return result

    # 准备监控命令和结果存储
    metrics_to_collect = valid_metrics[:-1] if metrics == "all" else [metrics]
    for metric in metrics_to_collect:
        result["data"]["metrics_data"][metric] = []
    
    sample_count = 0
    max_samples = count if count > 0 else float('inf')
    
    # 采样循环
    while sample_count < max_samples:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        result["data"]["timestamp"].append(timestamp)
        
        # 获取QEMU进程PID
        pid_command = f"ps aux | grep 'qemu-system-' | grep -v grep | grep '{name}' | awk '{{print $2}}' | head -n 1"
        if host in ["localhost", "127.0.0.1"]:
            pid_result = execute_local_command(pid_command)
        else:
            auth = get_remote_auth(host)
            if not auth:
                result["message"] = f"未找到远程主机{host}的认证配置" if is_zh else f"Auth config for {host} not found"
                return result
            auth["port"] = ssh_port
            pid_result = execute_remote_command(auth, pid_command)
        
        if not pid_result["success"] or not pid_result["output"]:
            result["message"] = f"无法获取虚拟机{name}的进程ID" if is_zh else f"Cannot get PID for VM {name}"
            return result
        
        vm_pid = pid_result["output"].strip()
        
        # 收集各指标数据
        for metric in metrics_to_collect:
            if metric == "cpu":
                # CPU使用率（基于进程占用）
                cmd = f"ps -p {vm_pid} -o %cpu --no-headers"
            elif metric == "memory":
                # 内存使用率
                cmd = f"ps -p {vm_pid} -o %mem --no-headers"
            elif metric == "disk":
                # 磁盘IO（简化版，实际可使用iostat）
                cmd = f"iostat -p {vm_pid} 1 1 | grep -v '^$' | tail -n 1 | awk '{{print $4+$5}}'"
            elif metric == "network":
                # 网络流量（简化版，实际可使用iftop）
                cmd = f"iftop -p {vm_pid} -t 1 1 | grep 'Total send' | awk '{{print $3}}' && iftop -p {vm_pid} -t 1 1 | grep 'Total receive' | awk '{{print $3}}'"
            
            # 执行监控命令
            if host in ["localhost", "127.0.0.1"]:
                metric_result = execute_local_command(cmd)
            else:
                metric_result = execute_remote_command(auth, cmd)
            
            # 解析结果
            value = metric_result["output"].strip() or "0"
            result["data"]["metrics_data"][metric].append(value)
        
        sample_count += 1
        if sample_count < max_samples:
            time.sleep(interval)
    
    result["success"] = True
    result["message"] = f"成功获取{name}的{sample_count}次监控数据" if is_zh else f"Successfully obtained {sample_count} monitoring data for {name}"
    return result

if __name__ == "__main__":
    mcp.run(transport="sse")

    