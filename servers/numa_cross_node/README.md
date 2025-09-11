| 工具名称 | 工具功能 | 核心输入参数 | 关键返回内容 |
| ---- | ---- | ---- | ---- |
| `numa_cross_node` | 自动检测 NUMA 跨节点访问异常的进程（支持本地与远程主机） | - `host`：远程主机名/IP（本地检测可不填） | - `overall_conclusion`: 总体结论，包括是否有问题(`has_issue`)、严重程度(`severity`)和摘要(`summary`)<br>- `anomaly_processes`: 异常进程列表，每个进程包括PID、本地内存、远程内存、跨节点比例、进程名称和命令行 |