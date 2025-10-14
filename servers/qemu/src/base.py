import os
import paramiko
import subprocess
import re
from config.public.base_config_loader import LanguageEnum
from config.private.qemu.config_loader import QemuConfig
from typing import Dict, Optional, List
def get_language() -> bool:
    """获取语言配置：True=中文，False=英文"""
    return QemuConfig().get_config().public_config.language == LanguageEnum.ZH


def get_remote_auth(host: str) -> Optional[Dict]:
    """从配置获取远程主机认证信息"""
    remote_hosts = QemuConfig().get_config().public_config.remote_hosts
    for host_config in remote_hosts:
        if host in [host_config.host, host_config.name]:
            return {
                "host": host_config.host,
                "port": host_config.port,
                "username": host_config.username,
                "password": host_config.password,
                "qemu_path":"/usr/bin"  # QEMU工具路径
            }
    return None


def execute_remote_command(auth: Dict, command: str) -> Dict:
    """执行远程QEMU命令（通过SSH）"""
    result = {
        "success": False,
        "output": "",
        "error": ""
    }
    ssh_conn: Optional[paramiko.SSHClient] = None

    try:
        ssh_conn = paramiko.SSHClient()
        ssh_conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # 优先使用密钥认证
        if auth.get("key_path") and os.path.exists(auth["key_path"]):
            private_key = paramiko.RSAKey.from_private_key_file(auth["key_path"])
            ssh_conn.connect(
                hostname=auth["host"],
                port=auth["port"],
                username=auth["username"],
                pkey=private_key,
                timeout=15,
                banner_timeout=10
            )
        else:
            # 密码认证
            ssh_conn.connect(
                hostname=auth["host"],
                port=auth["port"],
                username=auth["username"],
                password=auth["password"],
                timeout=15,
                banner_timeout=10
            )
        
        # 添加QEMU路径到环境变量
        command = f"export PATH={auth['qemu_path']}:$PATH && {command}"
        stdin, stdout, stderr = ssh_conn.exec_command(command, timeout=120)  # QEMU操作超时较长
        result["output"] = stdout.read().decode("utf-8", errors="replace").strip()
        result["error"] = stderr.read().decode("utf-8", errors="replace").strip()
        
        # 判断成功：无错误输出或包含QEMU操作特征信息
        result["success"] = len(result["error"]) == 0 or (
            "created" in result["output"].lower() or 
            "started" in result["output"].lower() or 
            "stopped" in result["output"].lower() or
            "deleted" in result["output"].lower()
        )

    except Exception as e:
        result["error"] = str(e)
    finally:
        if ssh_conn and ssh_conn.get_transport() and ssh_conn.get_transport().is_active(): # type: ignore
            ssh_conn.close()

    return result


def execute_local_command(command: str) -> Dict:
    """执行本地QEMU命令"""
    result = {
        "success": False,
        "output": "",
        "error": ""
    }

    try:
        # 添加QEMU路径到环境变量（默认路径）
        qemu_path = "/usr/bin"
        command = f"export PATH={qemu_path}:$PATH && {command}"
        
        output = subprocess.check_output(
            command,
            shell=True,
            text=True,
            stderr=subprocess.STDOUT,
            timeout=120  # 虚拟机操作可能耗时较长
        )
        result["output"] = output.strip()
        result["success"] = True
    except subprocess.CalledProcessError as e:
        result["error"] = e.output.strip()
    except subprocess.TimeoutExpired:
        result["error"] = "命令执行超时（QEMU操作未完成）" if get_language() else "Command timeout (QEMU operation incomplete)"
    except Exception as e:
        result["error"] = str(e)

    return result


def parse_vm_list(output: str) -> List[Dict]:
    """解析虚拟机列表输出（基于ps和qemu信息）"""
    vms = []
    if not output:
        return vms
    
    # 匹配QEMU进程行（格式示例：qemu-system-x86_64 -name ubuntu-vm ...）
    qemu_pattern = re.compile(r'qemu-system-(\w+)\s+.*?-name\s+(\S+)\s+')
    for line in output.splitlines():
        match = qemu_pattern.search(line)
        if not match:
            continue
        
        arch = match.group(1)
        name = match.group(2).strip('"\'')  # 移除可能的引号
        
        # 提取内存信息（-m 4096 或 -m 4G）
        memory_match = re.search(r'-m\s+(\d+[GM]?)', line)
        memory = memory_match.group(1) if memory_match else "2G"
        
        # 提取vcpus信息（-smp 4）
        vcpus_match = re.search(r'-smp\s+cpus=?(\d+)', line)
        vcpus = vcpus_match.group(1) if vcpus_match else "2"
        
        # 提取磁盘信息
        disk_match = re.search(r'-drive\s+file=(\S+),?.*?size=(\d+)', line)
        disk_path = disk_match.group(1) if disk_match else ""
        disk_size = disk_match.group(2) + "M" if disk_match else ""
        
        vms.append({
            "name": name,
            "arch": arch,
            "vcpus": vcpus,
            "memory": memory,
            "disk": f"path={disk_path},size={disk_size}" if disk_path else "",
            "status": "running"
        })
    
    return vms


def parse_stopped_vms(vm_dir: str, host: str = "localhost", ssh_port: int = 22) -> List[Dict]:
    """解析已创建但未运行的虚拟机（基于磁盘文件）"""
    stopped_vms = []
    if not vm_dir:
        return stopped_vms
    
    # 构建查询磁盘文件的命令
    command = f"find {vm_dir} -name '*.qcow2' -o -name '*.raw'"
    if host in ["localhost", "127.0.0.1"]:
        exec_result = execute_local_command(command)
    else:
        auth = get_remote_auth(host)
        if not auth:
            return stopped_vms
        auth["port"] = ssh_port
        exec_result = execute_remote_command(auth, command)
    
    if not exec_result["success"] or not exec_result["output"]:
        return stopped_vms
    
    # 解析磁盘文件并提取虚拟机信息
    for disk_path in exec_result["output"].splitlines():
        # 从磁盘路径提取虚拟机名称（假设命名规范：{name}.qcow2）
        name = os.path.basename(disk_path).rsplit('.', 1)[0]
        if not name:
            continue
        
        # 获取磁盘大小
        size_command = f"qemu-img info --output json {disk_path} | grep 'virtual-size' | awk '{{print $2}}'"
        if host in ["localhost", "127.0.0.1"]:
            size_result = execute_local_command(size_command)
        else:
            size_result = execute_remote_command(auth, size_command)
        
        size = f"{int(size_result['output'])/1024/1024/1024:.1f}G" if size_result["success"] else ""
        
        stopped_vms.append({
            "name": name,
            "arch": "unknown",  # 停止状态无法直接获取架构，可从配置文件读取
            "vcpus": "unknown",
            "memory": "unknown",
            "disk": f"path={disk_path},size={size}",
            "status": "stopped"
        })
    
    return stopped_vms

