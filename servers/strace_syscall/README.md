| 工具名称 | 工具功能 | 核心输入参数 | 关键返回内容 |
| ---- | ---- | ---- | ---- |
| `strace_syscall` | 利用 **strace -c** 在指定时间内采集**指定进程**的系统调用统计信息（本地或远程均可） | - `pid`：目标进程 PID（必填）<br>- `host`：远程主机名/IP（本地采集可不填）<br>- `timeout`：采集超时时间（默认10秒） | 系统调用统计结果（含`syscall`系统调用名称、`total_time`总耗时、`call_count`调用次数、`avg_time`平均耗时、`error_count`错误次数） |