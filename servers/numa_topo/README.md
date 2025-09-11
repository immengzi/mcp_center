| 工具名称 | 工具功能 | 核心输入参数 | 关键返回内容 |
| ---- | ---- | ---- | ---- |
| `numa_topo_tool` | 获取目标设备（本地/远程）的 NUMA 硬件拓扑与系统配置 | - `host`：远程主机名/IP（本地采集可不填） | `nodes_total`总节点数、`nodes`节点信息列表，每个节点包含`node_id`节点 ID、`cpus`该节点上的 CPU 列表、`size_mb`内存大小（MB）、`free_mb`空闲内存（MB） |