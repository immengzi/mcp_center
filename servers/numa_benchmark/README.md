| 工具名称 | 工具功能 | 核心输入参数 | 关键返回内容 |
| ---- | ---- | ---- | ---- |
| `numa_benchmark` | 自动探测NUMA拓扑并执行不同绑定策略下的性能基准测试（本地或远程均可） | - `benchmark`：基准测试程序路径（必填）<br>- `host`：远程主机名/IP（本地测试可不填） | 测试结果字典，包含`numa_nodes`（NUMA节点数）、`test_results`（各场景测试结果，含`local_binding`本地绑定、`cross_node_binding`跨节点绑定、`no_binding`无绑定的命令、输出、返回码及指标）和`timestamp`（时间戳） |