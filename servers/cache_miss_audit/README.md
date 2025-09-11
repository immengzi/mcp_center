| 工具名称 | 工具功能 | 核心输入参数 | 关键返回内容 |
| ---- | ---- | ---- | ---- |
| `cache_miss_audit_tool` | 利用 **perf stat** 在 10 秒内采集**整系统**微架构级指标（本地或远程均可） | - `host`：远程主机名/IP（本地采集可不填） | 性能统计结果（含`cache_misses`缓存未命中次数、`cycles`CPU 周期数、`instructions`退休指令数、`ipc`每周期指令数（=instructions/cycles）、`seconds`实际采样时长） |