import logging
import subprocess
import os
import time
from typing import Dict, List
import stat
from scp import SCPClient
from config.private.file_transfer.config_loader import FileTransferConfig
from servers.file_transfer.src.base import get_language, validate_local_path, get_remote_config, create_ssh_connection
from mcp.server import FastMCP

# 初始化MCP服务
mcp = FastMCP(
    "File Transfer Management MCP",
    host="0.0.0.0",
    port=FileTransferConfig().get_config().private_config.port
)

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@mcp.tool(
    name="http_download" if get_language() else "http_download",
    description="""
    通过HTTP/HTTPS/FTP链接下载文件（使用curl或wget）
    
    参数:
        -url: 下载链接（必填，如https://example.com/file.zip）
        -output_path: 本地保存路径（必填，如/tmp/file.zip）
        -tool: 下载工具（可选，curl/wget，默认自动选择）
    
    返回:
        -success: 操作是否成功
        -message: 结果描述
        -data: 包含下载详情的字典
    """ if get_language() else """
    Download files via HTTP/HTTPS/FTP links (using curl or wget)
    
    Parameters:
        -url: Download URL (required, e.g., https://example.com/file.zip)
        -output_path: Local save path (required, e.g., /tmp/file.zip)
        -tool: Download tool (optional, curl/wget, auto-select by default)
    
    Returns:
        -success: Operation success status
        -message: Result description
        -data: Dictionary with download details
    """
)
def http_download(url: str, output_path: str, tool: str = "") -> Dict:
    is_zh = get_language()
    result: Dict = {
        "success": False,
        "message": "",
        "data": {
            "url": url,
            "output_path": output_path,
            "file_size": 0,
            "transfer_time": 0.0
        }
    }

    # 参数校验
    if not url:
        result["message"] = "下载链接不能为空" if is_zh else "Download URL cannot be empty"
        return result
        
    valid, msg = validate_local_path(output_path)
    if not valid:
        result["message"] = f"输出路径无效：{msg}" if is_zh else f"Invalid output path: {msg}"
        return result

    # 检查可用工具
    available_tools: List[str] = []
    for tool_name in ["curl", "wget"]:
        try:
            subprocess.run(
                [tool_name, "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            available_tools.append(tool_name)
        except Exception as e:
            logger.warning(f"检查工具{tool_name}时发生意外错误: {str(e)}")
            continue
            
    if not available_tools:
        result["message"] = "未安装curl或wget工具" if is_zh else "curl or wget is not installed"
        return result

    # 选择工具
    selected_tool = tool if tool in available_tools else available_tools[0]

    # 构建命令
    start_time = time.time()
    try:
        if selected_tool == "curl":
            cmd = ["curl", "-f", "-L", url, "-o", output_path]
        else:  # wget
            cmd = ["wget", url, "-O", output_path]

        # 执行下载
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        # 计算结果
        file_size = os.path.getsize(output_path)
        transfer_time = time.time() - start_time
        
        result["success"] = True
        result["message"] = f"文件已通过{selected_tool}下载至{output_path}" if is_zh else f"File downloaded to {output_path} via {selected_tool}"
        result["data"]["file_size"] = file_size
        result["data"]["transfer_time"] = round(transfer_time, 2)

    except subprocess.CalledProcessError as e:
        result["message"] = f"{selected_tool}下载失败：{e.output}" if is_zh else f"{selected_tool} download failed: {e.output}"
    except Exception as e:
        result["message"] = f"下载错误：{str(e)}" if is_zh else f"Download error: {str(e)}"
    finally:
        # 清理失败的文件
        if not result["success"] and os.path.exists(output_path):
            try:
                os.remove(output_path)
            except Exception as e:  
                logger.warning(f"清理临时文件失败: {str(e)}") 

    return result


@mcp.tool(
    name="scp_transfer" if get_language() else "scp_transfer",
    description="""
    通过SCP协议传输文件/目录（本地与远程之间）
    
    参数:
        -src: 源路径（必填，本地路径或远程路径）
        -dst: 目标路径（必填，本地路径或远程路径）
        -host: 远程主机名/IP（必填）
        -recursive: 是否递归传输目录（可选，默认False）
    
    返回:
        -success: 操作是否成功
        -message: 结果描述
        -data: 包含传输详情的字典
    """ if get_language() else """
    Transfer files/directories via SCP protocol (local & remote)
    
    Parameters:
        -src: Source path (required, local or remote path)
        -dst: Destination path (required, local or remote path)
        -host: Remote hostname/IP (required)
        -recursive: Transfer directories recursively (optional, default False)
    
    Returns:
        -success: Operation success status
        -message: Result description
        -data: Dictionary with transfer details
    """
)
def scp_transfer(src: str, dst: str, host: str, recursive: bool = False) -> Dict:
    is_zh = get_language()
    result: Dict = {
        "success": False,
        "message": "",
        "data": {
            "src": src,
            "dst": dst,
            "file_count": 0,
            "transfer_time": 0.0
        }
    }

    # 参数校验
    if not src or not dst:
        result["message"] = "源路径和目标路径不能为空" if is_zh else "Source and destination paths cannot be empty"
        return result
        
    if not host:
        result["message"] = "远程主机名/IP不能为空" if is_zh else "Remote host cannot be empty"
        return result

    # 验证本地路径（如果源是本地）
    remote_config = get_remote_config(host)
    if not remote_config:
        result["message"] = f"未找到主机{host}的配置信息" if is_zh else f"No configuration found for host {host}"
        return result
    if not src.startswith(f"{host}:") and not src.startswith(f"{remote_config['username']}@"):
        is_dir = recursive and os.path.isdir(src)
        valid, msg = validate_local_path(src, is_dir)
        if not valid:
            result["message"] = f"源路径无效：{msg}" if is_zh else f"Invalid source path: {msg}"
            return result

    # 创建SSH连接
    ssh = create_ssh_connection(host)
    if not ssh:
        result["message"] = f"无法连接到远程主机{host}" if is_zh else f"Failed to connect to remote host {host}"
        return result

    try:
        # 检查传输通道
        transport = ssh.get_transport()
        if not transport:
            result["message"] = "SSH传输通道创建失败" if is_zh else "SSH transport channel creation failed"
            return result

        start_time = time.time()
        file_count = 0

        with SCPClient(transport) as scp:
            # 本地到远程
            if os.path.exists(src):
                # 确保远程目录存在
                remote_dir = os.path.dirname(dst) if ":" in dst else f"{host}:{os.path.dirname(dst)}"
                ssh.exec_command(f"mkdir -p {remote_dir.split(':')[-1]}")
                
                scp.put(src, dst, recursive=recursive)
                file_count = 1 if os.path.isfile(src) else sum(len(f) for _, _, f in os.walk(src))
            
            # 远程到本地
            elif ":" in src:
                # 确保本地目录存在
                local_dir = os.path.dirname(dst)
                if not os.path.exists(local_dir):
                    os.makedirs(local_dir, exist_ok=True)
                
                scp.get(src, dst, recursive=recursive)
                file_count = 1 if not recursive else len(os.listdir(dst))

        # 计算结果
        transfer_time = time.time() - start_time
        result["success"] = True
        result["message"] = f"SCP传输成功：{src} -> {dst}" if is_zh else f"SCP transfer successful: {src} -> {dst}"
        result["data"]["file_count"] = file_count
        result["data"]["transfer_time"] = round(transfer_time, 2)

    except Exception as e:
        result["message"] = f"SCP传输失败：{str(e)}" if is_zh else f"SCP transfer failed: {str(e)}"
    finally:
        try:
            ssh.close()
        except Exception as e:
            logger.debug(f"SSH连接关闭失败: {str(e)}")

    return result


@mcp.tool(
    name="sftp_transfer" if get_language() else "sftp_transfer",
    description="""
    通过SFTP协议传输文件/目录（本地与远程之间）
    
    参数:
        -operation: 操作类型（必填，put/get）
        -src: 源路径（必填）
        -dst: 目标路径（必填）
        -host: 远程主机名/IP（必填）
        -create_dir: 是否自动创建目录（可选，默认True）
    
    返回:
        -success: 操作是否成功
        -message: 结果描述
        -data: 包含传输详情的字典
    """ if get_language() else """
    Transfer files/directories via SFTP protocol (local & remote)
    
    Parameters:
        -operation: Operation type (required, put/get)
        -src: Source path (required)
        -dst: Destination path (required)
        -host: Remote hostname/IP (required)
        -create_dir: Auto-create directories (optional, default True)
    
    Returns:
        -success: Operation success status
        -message: Result description
        -data: Dictionary with transfer details
    """
)
def sftp_transfer(operation: str, src: str, dst: str, host: str, create_dir: bool = True) -> Dict:
    is_zh = get_language()
    result: Dict = {
        "success": False,
        "message": "",
        "data": {
            "operation": operation,
            "src": src,
            "dst": dst,
            "file_size": 0,
            "transfer_time": 0.0
        }
    }

    # 参数校验
    if operation not in ["put", "get"]:
        result["message"] = "操作类型必须是put或get" if is_zh else "Operation must be put or get"
        return result
        
    if not src or not dst:
        result["message"] = "源路径和目标路径不能为空" if is_zh else "Source and destination paths cannot be empty"
        return result
        
    if not host:
        result["message"] = "远程主机名/IP不能为空" if is_zh else "Remote host cannot be empty"
        return result

    # 验证本地路径
    if operation == "put":
        # 上传：源是本地
        is_dir = os.path.isdir(src)
        valid, msg = validate_local_path(src, is_dir)
        if not valid:
            result["message"] = f"源路径无效：{msg}" if is_zh else f"Invalid source path: {msg}"
            return result
    else:
        # 下载：目标是本地
        valid, msg = validate_local_path(dst, True)
        if not valid:
            result["message"] = f"目标路径无效：{msg}" if is_zh else f"Invalid destination path: {msg}"
            return result

    # 创建SSH连接
    ssh = create_ssh_connection(host)
    if not ssh:
        result["message"] = f"无法连接到远程主机{host}" if is_zh else f"Failed to connect to remote host {host}"
        return result

    try:
        sftp = ssh.open_sftp()
        start_time = time.time()
        total_size = 0

        # 自动创建目录
        if create_dir:
            if operation == "put":
                # 创建远程目录
                remote_dir = os.path.dirname(dst)
                dir_components = remote_dir.split('/')
                current_dir = ""
                for comp in dir_components:
                    if comp:
                        current_dir += f"/{comp}"
                        try:
                            sftp.stat(current_dir)
                        except FileNotFoundError:
                            sftp.mkdir(current_dir)
            else:
                # 创建本地目录
                local_dir = os.path.dirname(dst)
                if not os.path.exists(local_dir):
                    os.makedirs(local_dir, exist_ok=True)

        # 执行传输
        if operation == "put":
            # 上传文件/目录
            if os.path.isfile(src):
                sftp.put(src, dst)
                total_size = os.path.getsize(src)
            else:
                # 递归上传目录
                for root, _, files in os.walk(src):
                    rel_path = os.path.relpath(root, src)
                    remote_root = os.path.join(dst, rel_path) if rel_path != "." else dst
                    
                    try:
                        sftp.stat(remote_root)
                    except FileNotFoundError:
                        sftp.mkdir(remote_root)
                    
                    for file in files:
                        local_path = os.path.join(root, file)
                        remote_path = os.path.join(remote_root, file)
                        sftp.put(local_path, remote_path)
                        total_size += os.path.getsize(local_path)
        else:
            # 下载文件/目录
            try:
                # 获取远程路径属性
                stat_result = sftp.stat(src)
                st_mode = stat_result.st_mode if stat_result.st_mode is not None else 0
                is_dir = stat.S_ISDIR(st_mode) 
            except FileNotFoundError:
                result["message"] = f"远程路径不存在: {src}" if is_zh else f"Remote path not found: {src}"
                return result
            except Exception as e:
                result["message"] = f"获取远程路径属性失败: {str(e)}" if is_zh else f"Failed to get remote path stats: {str(e)}"
                return result

            if not is_dir:
                sftp.get(src, dst)
                attr = sftp.stat(src)
                total_size = attr.st_size if attr.st_size is not None else 0
            else:
                # 递归下载目录
                if not os.path.exists(dst):
                    os.makedirs(dst)

                def download_recursive(remote_dir: str, local_dir: str) -> None:
                    nonlocal total_size
                    for entry in sftp.listdir_attr(remote_dir):
                        if entry.filename in ('.', '..'):
                            continue
                            
                        remote_path = os.path.join(remote_dir, entry.filename)
                        local_path = os.path.join(local_dir, entry.filename)
                        entry_mode = entry.st_mode if entry.st_mode is not None else 0
                        
                        if stat.S_ISDIR(entry_mode):
                            if not os.path.exists(local_path):
                                os.makedirs(local_path)
                            download_recursive(remote_path, local_path)
                        else:
                            sftp.get(remote_path, local_path)
                            total_size += entry.st_size if entry.st_size is not None else 0

                download_recursive(src, dst)

        # 计算结果
        transfer_time = time.time() - start_time
        result["success"] = True
        result["message"] = f"SFTP{operation}成功：{src} -> {dst}" if is_zh else f"SFTP {operation} successful: {src} -> {dst}"
        result["data"]["file_size"] = total_size
        result["data"]["transfer_time"] = round(transfer_time, 2)

    except Exception as e:
        result["message"] = f"SFTP{operation}失败：{str(e)}" if is_zh else f"SFTP {operation} failed: {str(e)}"
    finally:
        try:
            sftp.close()
        except Exception as e:
            logger.debug(f"SFTP连接关闭失败: {str(e)}")  # 调试日志记录细节
        
        try:
            ssh.close()
        except Exception as e:
            logger.debug(f"SSH连接关闭失败: {str(e)}")

    return result
    
if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='sse')