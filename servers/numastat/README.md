| 工具名称 | 工具功能 | 核心输入参数 | 关键返回内容 |
| ---- | ---- | ---- | ---- |
| `numastat_info_tool` | 使用 **numastat** 获取目标设备（本地/远程）的 **NUMA 节点访问统计** | - `host`：远程主机名/IP（本地采集可不填） | NUMA 统计字典（含`numa_hit`命中次数、`numa_miss`未命中次数、`numa_foreign`跨节点访问次数、`interleave_hit`交错命中次数、`local_node`本地节点访问次数、`other_node`其他节点访问次数） |