| 工具名称 | 工具功能 | 核心输入参数 | 关键返回内容 |
| ---- | ---- | ---- | ---- |
| `numa_hardware` | 获取 **NUMA 架构硬件监控信息**（支持本地或远程主机） | - `host`：远程主机名/IP（本地采集可不填）<br>- `timeout`：命令执行超时时间（默认30秒） | - `real_time_frequencies`：各CPU核心实时频率（MHz）<br>- `specifications`：CPU型号/最大最小频率<br>- `numa_topology`：NUMA节点与CPU核心映射关系 |