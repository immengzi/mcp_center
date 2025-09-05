| 工具名称 | 工具功能 | 核心输入参数 | 关键返回内容 |
| ---- | ---- | ---- | ---- |
| `numa_rebind_tool` | 修改目标设备（本地/远程）上已运行进程的 NUMA 内存绑定 | - `host`：远程主机名/IP（本地采集可不填）、`pid`进程 ID、`from_node`当前内存所在的 NUMA 节点编号、`to_node`目标 NUMA 节点编号 | `status`操作状态（success / error）、`message`操作结果信息、`output`命令的原始输出（如有） |