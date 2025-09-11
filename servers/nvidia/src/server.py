


from asyncio.log import logger
from typing import Any, Dict, Optional
from config.private.nvidia.config_loader import NvidiaSmiConfig
from config.public.base_config_loader import LanguageEnum
from mcp.server import FastMCP

from servers.nvidia.src.base import _format_gpu_info, _get_local_gpu_status, _get_remote_gpu_status, _run_local_nvidia_smi, _run_remote_nvidia_smi

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
    host: Optional[str] = None,
    port: int = 22,
    username: Optional[str] = None,
    password: Optional[str] = None,
    gpu_index: Optional[int] = None,
    include_processes: bool = False
) -> Dict:
    result = {
        "success": False,
        "message": "",
        "data": {}
    }

    # 远程查询条件判断
    if host and (not username or not password):
        result["message"] = "远程查询需提供username和password" if NvidiaSmiConfig().get_config().public_config.language == LanguageEnum.ZH else "Username and password are required for remote queries"
        return result

    try:
        # 获取GPU状态信息（本地/远程分支）
        if host and username and password:
            # 远程查询
            raw_info = _get_remote_gpu_status(host, username, password, port, gpu_index, include_processes,NvidiaSmiConfig().get_config().public_config.language)
            result["message"] = f"成功获取远程主机 {host} 的GPU状态信息" if NvidiaSmiConfig().get_config().public_config.language == LanguageEnum.ZH else f"Successfully obtained GPU status information for remote host {host}"
        else:
            # 本地查询
            raw_info = _get_local_gpu_status(gpu_index, include_processes,NvidiaSmiConfig().get_config().public_config.language)
            result["message"] = "成功获取本地主机的GPU状态信息" if NvidiaSmiConfig().get_config().public_config.language == LanguageEnum.ZH else "Successfully obtained GPU status information for the local host"

        # 格式化结果
        result["success"] = True
        result["data"] = _format_gpu_info(raw_info, host or "localhost", include_processes,NvidiaSmiConfig().get_config().public_config.language)

    except Exception as e:
        logger.error(f"获取GPU状态信息失败: {str(e)}" if NvidiaSmiConfig().get_config().public_config.language == LanguageEnum.ZH else f"Failed to obtain GPU status information: {str(e)}")
        result["message"] = f"获取GPU状态信息失败: {str(e)}" if NvidiaSmiConfig().get_config().public_config.language == LanguageEnum.ZH else f"Failed to obtain GPU status information: {str(e)}"

    return result

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
    # 获取当前语言配置
    language = "zh" if NvidiaSmiConfig().get_config().public_config.language == LanguageEnum.ZH else "en"
    result = {
        "success": False,
        "message": "",
        "data": {"host": host or "localhost", "raw_table": ""}
    }

    # 远程查询参数校验
    if host and (not username or not password):
        result["message"] = "远程查询需提供username和password" if language == "zh" else "Username and password are required for remote queries"
        return result

    try:
        # 执行本地/远程命令
        if host and username and password:
            raw_table = _run_remote_nvidia_smi(host, username, password, port, language)
            result["message"] = f"成功获取远程主机 {host} 的nvidia-smi原始表格" if language == "zh" else f"Successfully obtained nvidia-smi raw table from remote host {host}"
        else:
            raw_table = _run_local_nvidia_smi(language)
            result["message"] = "成功获取本地主机的nvidia-smi原始表格" if language == "zh" else "Successfully obtained nvidia-smi raw table from local host"

        # 填充结果
        result["success"] = True
        result["data"]["raw_table"] = raw_table

    except Exception as e:
        error_msg = f"获取nvidia-smi原始表格失败: {str(e)}" if language == "zh" else f"Failed to obtain nvidia-smi raw table: {str(e)}"
        logger.error(error_msg)
        result["message"] = error_msg

    return result
if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='sse')