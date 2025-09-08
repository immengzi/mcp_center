| 工具名称 | 工具功能 | 核心输入参数 | 关键返回内容 |
| ---- | ---- | ---- | ---- |
| `perf_events_tool` | 利用 **perf record / report** 快速定位**系统或指定进程的 CPU 性能瓶颈**（本地或远程均可） | - `host`：远程主机名/IP（本地采集可不填）<br>- `pid`：目标进程 ID（整型，缺省时采集整个系统） | 性能分析结果（含`total_samples`总样本数、`event_count`事件计数（cycles 等）、`hot_functions`热点函数列表（默认 Top5，每条含`overhead`占比、`command`进程名、`shared_object`二进制对象、`symbol`函数名、`symbol_type`符号类型（`.`用户态/`k`内核态））） |