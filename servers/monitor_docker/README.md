| 工具名称 | 工具功能 | 核心输入参数 | 关键返回内容 |
| ---- | ---- | ---- | ---- |
| `monitor_docker` | 监控指定 Docker 容器的 NUMA 内存访问情况 | - `container_id`: 要监控的容器 ID 或名称 | `status`: 操作状态（success / error）<br>`message`: 操作结果信息<br>`output`: NUMA 内存访问统计信息（包含每个 NUMA 节点的内存使用情况） |