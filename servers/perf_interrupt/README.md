| 工具名称 | 工具功能 | 核心输入参数 | 关键返回内容 |
| ---- | ---- | ---- | ---- |
| `perf_interrupt_health_check` | 检查系统中断统计信息以定位高频中断导致的CPU占用（支持本地与远程主机） | - `host`：远程主机名/IP（本地检测可不填） | - `irq_number`: 中断编号<br>- `total_count`: 总触发次数<br>- `device`: 设备名称<br>- `cpu_distribution`: 各CPU核心的中断分布<br>- `interrupt_type`: 中断类型 |