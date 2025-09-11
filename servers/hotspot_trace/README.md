| 工具名称 | 工具功能 | 核心输入参数 | 关键返回内容 |
| ---- | ---- | ---- | ---- |
| `hotspot_trace_tool` | 利用 **perf record -g** 在 30 秒内采集**指定进程**的函数调用栈耗时（本地或远程均可） | - `pid`：目标进程 PID（必填）<br>- `host`：远程主机名/IP（本地采集可不填） | 函数性能分析结果（含`top_functions`函数列表，每个函数包含：`function`函数名、`self_percent`自身耗时占比、`total_percent`总耗时占比（含子函数）、`call_stack`调用栈路径） |