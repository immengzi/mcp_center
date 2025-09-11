| 工具名称 | 工具功能 | 核心输入参数 | 关键返回内容 |
| ---- | ---- | ---- | ---- |
| `lscpu_info_tool` | 获取目标设备（本地/远程）中 **CPU架构** 等核心静态信息 | - `host`：远程主机名/IP（本地采集可不填） | CPU架构信息（含`architecture`架构（如 x86_64）、`cpus_total`总CPU数量、`model_name`CPU型号名称、`cpu_max_mhz`CPU最大频率（MHz，浮点数）、`vulnerabilities`常见安全漏洞的缓解状态字典） |