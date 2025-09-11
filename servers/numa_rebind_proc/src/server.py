from typing import Dict, Any
import subprocess
from mcp.server import FastMCP
from config.public.base_config_loader import LanguageEnum
from config.private.numa_rebind_proc.config_loader import NumaRebindProcConfig

mcp = FastMCP("NUMA Rebind MCP Server", host="0.0.0.0", port=NumaRebindProcConfig().get_config().private_config.port)

@mcp.tool(
    name="numa_rebind_proc_tool"
    if NumaRebindProcConfig().get_config().public_config.language == LanguageEnum.ZH
    else "numa_rebind_proc_tool",
    description='''
    修改已运行进程的 NUMA 内存绑定。使用 migratepages 工具将进程的内存从一个 NUMA 节点迁移到另一个节点。
    
    1. 输入参数：
        - pid: 进程 ID
        - from_node: 当前内存所在的 NUMA 节点编号
        - to_node: 目标 NUMA 节点编号
    
    2. 返回值：
        - status: 操作状态（success / error）
        - message: 操作结果信息
        - output: 命令的原始输出（如有）
    '''
    if NumaRebindProcConfig().get_config().public_config.language == LanguageEnum.ZH
    else 
    '''
    Rebind the NUMA memory of a running process. Use the migratepages tool to migrate memory from one NUMA node to another.

    1. Input parameters:
        - pid: Process ID
        - from_node: Current NUMA node number where memory is located
        - to_node: Target NUMA node number
    
    2. Return value:
        - status: Operation status (success / error)
        - message: Result information
        - output: Raw output of the command (if any)
    '''
)
def numa_rebind_proc_tool(pid: int, from_node: int, to_node: int) -> Dict[str, Any]:
    """
    使用 migratepages 工具将进程的内存从一个 NUMA 节点迁移到另一个节点。
    """
    try:
        command = ["sudo", "migratepages", str(pid), str(from_node), str(to_node)]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )

        return {
            "status": "success",
            "message": f"Memory for PID {pid} has been migrated from node {from_node} to node {to_node}.",
            "output": result.stdout
        }

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() or "Command execution failed."
        if NumaRebindProcConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise RuntimeError(f"迁移失败: {error_msg}")
        else:
            raise RuntimeError(f"Migration failed: {error_msg}")
    except FileNotFoundError:
        if NumaRebindProcConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise RuntimeError("未找到 migratepages 工具，请安装 numactl 包。")
        else:
            raise RuntimeError("migratepages tool not found. Please install the numactl package.")
    except Exception as e:
        if NumaRebindProcConfig().get_config().public_config.language == LanguageEnum.ZH:
            raise RuntimeError(f"发生未知错误: {str(e)}")
        else:
            raise RuntimeError(f"An unknown error occurred: {str(e)}")


if __name__ == "__main__":
    # 启动服务
    mcp.run(transport='sse')