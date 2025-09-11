# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""MCP Client"""

import asyncio
import logging
from contextlib import AsyncExitStack
from typing import TYPE_CHECKING, Union
from pydantic import BaseModel, Field
from enum import Enum
from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client


logger = logging.getLogger(__name__)


class MCPStatus(str, Enum):
    """MCP状态枚举"""
    UNINITIALIZED = "UNINITIALIZED"
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    ERROR = "ERROR"


class MCPClient:
    """MCP客户端基类"""

    def __init__(self, url: str, headers: dict[str, str]) -> None:
        """初始化MCP Client"""
        self.url = url
        self.headers = headers
        self.client: Union[ClientSession, None] = None
        self.status = MCPStatus.UNINITIALIZED

    async def _main_loop(
        self
    ) -> None:
        """
        创建MCP Client

        抽象函数；作用为在初始化的时候使用MCP SDK创建Client
        由于目前MCP的实现中Client和Session是1:1的关系，所以直接创建了 :class:`~mcp.ClientSession`
        """
        # 创建Client
        try:
            client = sse_client(
                url=self.url,
                headers=self.headers
            )
        except Exception as e:
            self.error_sign.set()
            err = f"创建Client失败，错误信息：{e}"
            print(err)
            raise Exception(err)
        # 创建Client、Session
        try:
            exit_stack = AsyncExitStack()
            read, write = await exit_stack.enter_async_context(client)
            self.client = ClientSession(read, write)
            session = await exit_stack.enter_async_context(self.client)
            # 初始化Client
            await session.initialize()
        except Exception:
            self.error_sign.set()
            self.status = MCPStatus.STOPPED
            err = f"初始化Client失败，错误信息：{e}"
            print(err)
            raise

        self.ready_sign.set()
        self.status = MCPStatus.RUNNING
        # 等待关闭信号
        await self.stop_sign.wait()

        # 关闭Client
        try:
            await exit_stack.aclose()  # type: ignore[attr-defined]
            self.status = MCPStatus.STOPPED
        except Exception:
            print(f"关闭Client失败，错误信息：{e}")

    async def init(self) -> None:
        """
        初始化 MCP Client类
        :return: None
        """
        # 初始化变量
        self.ready_sign = asyncio.Event()
        self.error_sign = asyncio.Event()
        self.stop_sign = asyncio.Event()

        # 创建协程
        self.task = asyncio.create_task(self._main_loop())

        # 等待初始化完成
        done, pending = await asyncio.wait(
            [asyncio.create_task(self.ready_sign.wait()),
             asyncio.create_task(self.error_sign.wait())],
            return_when=asyncio.FIRST_COMPLETED
        )
        if self.error_sign.is_set():
            self.status = MCPStatus.ERROR
            print("MCP Client 初始化失败")
            raise Exception("MCP Client 初始化失败")

    async def call_tool(self, tool_name: str, params: dict) -> "CallToolResult":
        """调用MCP Server的工具"""
        return await self.client.call_tool(tool_name, params)

    async def stop(self) -> None:
        """停止MCP Client"""
        self.stop_sign.set()
        try:
            await self.task
        except Exception as e:
            err = f"关闭MCP Client失败，错误信息：{e}"
            print(err)


async def main() -> None:
    """测试MCP Client"""
    url = "http://0.0.0.0:12101/sse"
    headers = {}
    client = MCPClient(url, headers)
    await client.init()
    result = await client.call_tool("cmd_generator_tool", {"goal": "生成一个shell命令来查看当前时间"})
    print(result)
    cmd = result.content[0].text
    print(f"生成的命令是: {cmd}")
    result = await client.call_tool("cmd_executor_tool", {"command": cmd})

    # cpu架构等静态信息收集
    # result = await client.call_tool("lscpu_info_tool", {})
    # 查询 NUMA 硬件拓扑与系统配置
    # result = await client.call_tool("numa_topo_tool", {})
    # 启动时绑定进程到指定 NUMA 节点
    # result = await client.call_tool("numa_bind_proc_tool", {
    #     "numa_node": 0,
    #     "memory_node": 0,
    #     "program_path": "/root/mcp_center/test/hello"
    # })
    # 修改已启动进程的 NUMA 绑定
    # result = await client.call_tool("numa_rebind_proc_tool", {
    #     "pid": 982, # firewalld
    #     "from_node": 0,
    #     "to_node": 0
    # })
    # 为 Docker 容器配置 NUMA 绑定
    # result = await client.call_tool("numa_bind_docker_tool", {
    #     "image": "nginx",
    #     "cpuset_cpus": "0-3",
    #     "cpuset_mems": "0",
    #     "detach": True
    # })
    # 用 NUMA 绑定控制测试变量
    # result = await client.call_tool("numa_perf_compare", {
    #     'benchmark': "/root/mcp_center/stream"
    # })
    # 用 NUMA 绑定定位硬件问题
    # result = await client.call_tool("numa_diagnose", {})
    # 查看系统整体 NUMA 内存访问状态
    # result = await client.call_tool("numastat_info_tool", {})
    # 定位跨节点内存访问过高的进程
    # result = await client.call_tool("numa_cross_node", {})
    # 监控 Docker 容器的 NUMA 内存访问
    # result = await client.call_tool("numa_container", {
    #     "container_id": "258b82ea"
    # })
    # 快速定位系统 / 进程的 CPU 性能瓶颈    
    # result = await client.call_tool("hotspot_trace_tool", {"pid": 995})
    # result = await client.call_tool("hotspot_trace_tool", {})
    # 定位 CPU 缓存失效导致的性能损耗
    # result = await client.call_tool("cache_miss_audit_tool", {})
    # 精准测量函数执行时间（含调用栈）
    # result = await client.call_tool("func_timing_trace_tool", {"pid": 995})
    # 排查不合理的系统调用（高频 / 耗时）
    # result = await client.call_tool("strace_syscall", {"pid": 1322})
    # 定位高频中断导致的 CPU 占用
    # result = await client.call_tool("perf_interrupt_health_check", {})    
    # 火焰图生成：可视化展示性能瓶颈
    # result = await client.call_tool("flame_graph", {
    #     'perf_data_path': "/root/mcp_center/perf.data",
    #     'output_path': "/root/mcp_center/cpu_flamegraph.svg",
    #     'flamegraph_path': "/root/mcp_center/FlameGraph"
    # })

    print(result)
    await client.stop()

if __name__ == "__main__":
    asyncio.run(main())
