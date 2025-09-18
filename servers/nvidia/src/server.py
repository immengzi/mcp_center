
from typing import Any, Dict, Optional, Union

import paramiko
from config.private.nvidia.config_loader import NvidiaSmiConfig
from config.public.base_config_loader import LanguageEnum
from mcp.server import FastMCP

from servers.nvidia.src.base import _format_gpu_info, _get_local_gpu_status, _get_remote_gpu_status_via_ssh, _run_local_nvidia_smi, _run_remote_nvidia_smi

mcp = FastMCP("Nvidia MCP Server", host="0.0.0.0", port=NvidiaSmiConfig().get_config().private_config.port)
@mcp.tool(
    name="nvidia_smi_status"
    if NvidiaSmiConfig().get_config().public_config.language == LanguageEnum.ZH
    else "nvidia_smi_status",
    description=
    """
    使用nvidia-smi获取本地或远程服务器的GPU状态信息（远程需提供SSH信息）。返回GPU的利用率、显存使用量、温度等关键指标。
    支持本地和远程的GPU状态查询工具
    
    本地查询：不填host、username、password即可
    远程查询：必须提供host、username、password（port可选，默认22）
    
    1. 输入值如下：
        - host：远程主机IP或hostname，不填则查询本地
        - port：SSH端口，默认22
        - username：SSH用户名，远程查询时必填
        - password：SSH密码，远程查询时必填
        - gpu_index：GPU索引（0-based，可选，不填则查询所有GPU）
        - include_processes：是否包含占用GPU的进程信息（默认False）
    
    2. 返回值为包含查询结果的字典
        - success：布尔值，表示查询是否成功
        - message：字符串，描述查询结果（成功信息或错误原因）
        - data：字典，包含GPU状态详细信息
            - host：查询的主机（本地为"localhost"）
            - gpus：列表，每个元素为GPU信息字典
                - index：GPU索引（整数）
                - name：GPU型号名称
                - utilization_gpu：GPU利用率（百分比）
                - utilization_memory：显存利用率（百分比）
                - temperature：温度（摄氏度）
                - memory_total：总显存（MB）
                - memory_used：已用显存（MB）
                - memory_free：空闲显存（MB）
                - processes：占用进程列表（仅当include_processes=True时返回）
                    - pid：进程ID
                    - name：进程名称
                    - memory_used：进程占用显存（MB）
    """
    if NvidiaSmiConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    """
    GPU status query tool supporting local and remote servers using nvidia-smi
    
    Local query: Leave host, username, password empty
    Remote query: Must provide host, username, password (port is optional, default 22)
    
    1. Input values are as follows:
        - host: Remote host IP or hostname, leave empty for local query
        - port: SSH port, default 22
        - username: SSH username, required for remote query
        - password: SSH password, required for remote query
        - gpu_index: GPU index (0-based, optional, all GPUs if not specified)
        - include_processes: Whether to include GPU-using processes (default False)
    
    2. Return value is a dictionary containing query results
        - success: Boolean, indicating whether the query was successful
        - message: String, describing the query result (success information or error reason)
        - data: Dictionary, containing detailed GPU status information
            - host: Queried host ("localhost" for local)
            - gpus: List, each element is a GPU information dictionary
                - index: GPU index (integer)
                - name: GPU model name
                - utilization_gpu: GPU utilization (percentage)
                - utilization_memory: Memory utilization (percentage)
                - temperature: Temperature (celsius)
                - memory_total: Total memory (MB)
                - memory_used: Used memory (MB)
                - memory_free: Free memory (MB)
                - processes: List of using processes (returned only if include_processes=True)
                    - pid: Process ID
                    - name: Process name
                    - memory_used: Memory used by process (MB)
    """
)
def nvidia_smi_status(
    host: Union[str, None] = None,
    gpu_index: Optional[int] = None,
    include_processes: bool = False
) -> Dict[str, Any]:
    """获取GPU状态信息（支持双语提示，严格复刻模板结构）"""
    result = {
        "success": False,
        "message": "",
        "data": {}
    }
    # 获取当前语言配置（全局复用）
    lang = NvidiaSmiConfig().get_config().public_config.language

    # 1. 本地查询分支（host为空）
    if host is None:
        try:
            raw_info = _get_local_gpu_status(gpu_index, include_processes, lang)
            formatted_data = _format_gpu_info(raw_info, "localhost", include_processes, lang)

            result["success"] = True
            result["message"] = "成功获取本地主机的GPU状态信息" if lang == LanguageEnum.ZH else "Successfully obtained GPU status information for the local host"
            result["data"] = formatted_data
            return result
        except Exception as e:
            error_msg = f"获取本地GPU状态信息失败: {str(e)}" if lang == LanguageEnum.ZH else f"Failed to obtain local GPU status information: {str(e)}"
            result["message"] = error_msg
            return result

    # 2. 远程查询分支（host不为空）
    else:
        for host_config in NvidiaSmiConfig().get_config().public_config.remote_hosts:
            if host == host_config.name or host == host_config.host:
                try:
                    # 建立SSH连接
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh.connect(
                        hostname=host_config.host,
                        port=host_config.port,
                        username=host_config.username,
                        password=host_config.password
                    )

                    # 远程查询GPU状态
                    raw_info = _get_remote_gpu_status_via_ssh(ssh, gpu_index, include_processes, lang)
                    ssh.close()

                    # 格式化结果
                    formatted_data = _format_gpu_info(raw_info, host_config.host, include_processes, lang)
                    result["success"] = True
                    result["message"] = f"成功获取远程主机 {host_config.host} 的GPU状态信息" if lang == LanguageEnum.ZH else f"Successfully obtained GPU status information for remote host {host_config.host}"
                    result["data"] = formatted_data
                    return result

                except paramiko.AuthenticationException:
                    # 认证失败（双语提示）
                    if 'ssh' in locals():
                        ssh.close()
                    err_msg = "SSH认证失败，请检查用户名和密码" if lang == LanguageEnum.ZH else "SSH authentication failed, please check username and password"
                    result["message"] = err_msg
                    return result
                except Exception as e:
                    # 其他远程执行异常（双语提示）
                    if 'ssh' in locals():
                        ssh.close()
                    err_msg = f"远程主机 {host_config.host} 查询异常: {str(e)}" if lang == LanguageEnum.ZH else f"Remote host {host_config.host} query error: {str(e)}"
                    result["message"] = err_msg
                    return result

        # 未匹配到远程主机（双语异常）
        if lang == LanguageEnum.ZH:
            raise ValueError(f"未找到远程主机配置: {host}")
        else:
            raise ValueError(f"Remote host configuration not found: {host}")


@mcp.tool(
    name="nvidia_smi_raw_table"
    if NvidiaSmiConfig().get_config().public_config.language == LanguageEnum.ZH
    else "nvidia_smi_raw_table",
    description=
    """
    执行nvidia-smi命令并返回原生表格格式输出（支持本地/远程）。输出与直接在终端执行nvidia-smi的表格样式完全一致，包含GPU型号、状态、进程等完整信息。
    
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
        - data：字典，包含原始表格信息
            - host：查询的主机（本地为"localhost"）
            - raw_table：nvidia-smi输出的原始表格字符串（保留换行和格式）
    """
    if NvidiaSmiConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    """
    Execute nvidia-smi command and return raw table format output (supports local/remote). The output is identical to the table style when executing nvidia-smi directly in the terminal, including complete information such as GPU model, status, processes, etc.
    
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
        - data: Dictionary, containing raw table information
            - host: Queried host ("localhost" for local)
            - raw_table: Raw table string output by nvidia-smi (preserves line breaks and format)
    """
)
def nvidia_smi_raw_table(
    host: Optional[str] = None,
    port: int = 22,
    username: Optional[str] = None,
    password: Optional[str] = None
) -> Dict[str, Any]:
    """获取nvidia-smi原始表格数据（遵循模板逻辑，支持双语）"""
    # 获取当前语言配置
    lang = NvidiaSmiConfig().get_config().public_config.language
    language = "zh" if lang == LanguageEnum.ZH else "en"

    result = {
        "success": False,
        "message": "",
        "data": {"host": host or "localhost", "raw_table": ""}
    }

    # 1. 本地查询分支（host为空）
    if host is None:
        try:
            raw_table = _run_local_nvidia_smi(language)
            result["success"] = True
            result["message"] = "成功获取本地主机的nvidia-smi原始表格" if language == "zh" else "Successfully obtained nvidia-smi raw table from local host"
            result["data"]["raw_table"] = raw_table
            return result
        except Exception as e:
            error_msg = f"获取本地nvidia-smi原始表格失败: {str(e)}" if language == "zh" else f"Failed to obtain local nvidia-smi raw table: {str(e)}"
            result["message"] = error_msg
            return result

    # 2. 远程查询分支（host不为空）
    else:
        # 从配置匹配远程主机信息
        matched_config = None
        for host_config in NvidiaSmiConfig().get_config().public_config.remote_hosts:
            if host == host_config.name or host == host_config.host:
                matched_config = host_config
                break

        # 未匹配到配置时使用手动传入的认证信息
        if not matched_config:
            if not username or not password:
                result["message"] = "远程查询需提供username和password" if language == "zh" else "Username and password are required for remote queries"
                return result
            # 使用手动传入的参数
            remote_host = host
            remote_port = port
            remote_username = username
            remote_password = password
        else:
            # 使用配置中的参数
            remote_host = matched_config.host
            remote_port = matched_config.port if matched_config.port else port
            remote_username = matched_config.username
            remote_password = matched_config.password

        try:
            # 执行远程查询
            raw_table = _run_remote_nvidia_smi(remote_host, remote_username, remote_password, remote_port, language)
            result["success"] = True
            result["message"] = f"成功获取远程主机 {remote_host} 的nvidia-smi原始表格" if language == "zh" else f"Successfully obtained nvidia-smi raw table from remote host {remote_host}"
            result["data"]["raw_table"] = raw_table
            return result
        except paramiko.AuthenticationException:
            err_msg = "SSH认证失败，请检查用户名和密码" if language == "zh" else "SSH authentication failed, please check username and password"
            result["message"] = err_msg
            return result
        except Exception as e:
            err_msg = f"获取远程nvidia-smi原始表格失败: {str(e)}" if language == "zh" else f"Failed to obtain remote nvidia-smi raw table: {str(e)}"
            result["message"] = err_msg
            return result
    return result
if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='sse')