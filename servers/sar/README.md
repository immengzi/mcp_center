# Sar命令信息采集MCP（管理控制程序）规范文档
## 一、服务介绍
本服务是一款基于`sar`命令实现系统资源监控的MCP（管理控制程序），核心功能为​​系统资源监控与故障诊断​​，通过长期收集 CPU、内存、磁盘 I/O、网络等指标，分析资源的​​周期性规律，辅助容量规划与异常检测。可进行​历史分析​​，回溯过去某时段的性能问题​​。

## 二、核心工具信息
| 工具名称 | 工具功能 | 核心输入参数 | 关键返回内容 |
| ---- | ---- | ---- | ---- |
| `sar_cpu_collect_tool` | 分析cpu使用的周期性规律 | - `host`：远程主机名/IP（本地采集可不填）<br>- `interval`：监控的时间间隔、<br>- `count`：监控次数 | 采集指标列表：含`timestamp`采集时间点、`user`用户空间程序占用CPU的百分比、`nice`低优先级用户进程占用的CPU百分比、`system`内核空间程序占用CPU的百分比、`iowait`CPU等待磁盘I/O操作的时间百分比、`steal`虚拟化环境中，其他虚拟机占用的CPU时间百分比、`idle`CPU空闲时间百分比 |
| `sar_memory_collect_tool` | 分析内存资源使用的周期性规律 | - `host`：远程主机名/IP（本地采集可不填）<br>- `interval`：监控的时间间隔、<br>- `count`：监控次数 | 采集指标列表：含`timestamp`采集时间点、`kbmemfree`物理空闲内存量、`kbavail`实际可用内存、`kbmemused`已使用的物理内存、`memused`已用内存占总物理内存的百分比、`kbbuffers`内核缓冲区（Buffer）占用的内存、`kbcached`​内核缓存（Cache）占用的内存、`kbcommit`当前工作负载所需的总内存量、`commit`kbcommit占系统总可用内存百分比、`kbactive`活跃内存、`kbinact`非活跃内存、`kbdirty`等待写入磁盘的脏数据量 |
| `sar_disk_collect_tool` | 分析磁盘IO使用的周期性规律 | - `host`：远程主机名/IP（本地采集可不填）<br>- `interval`：监控的时间间隔、<br>- `count`：监控次数 | 采集指标列表：含`timestamp`采集时间点、`name`磁盘设备名称、`tps`每秒传输次数、`rkB_s`每秒读取的数据量、`wkB_s`每秒写入的数据量、`dkB_s`每秒丢弃的数据量、`areq-sz`平均每次 I/O 请求的数据大小、`aqu-sz`平均 I/O 请求队列长度、`await`平均每次 I/O 请求的等待时间、`util`设备带宽利用率 |
| `sar_network_collect_tool` | 分析网络流量的周期性规律 | - `host`：远程主机名/IP（本地采集可不填）<br>- `interval`：监控的时间间隔、<br>- `count`：监控次数 | 采集指标列表：含`timestamp`采集时间点、`iface`网络接口名称、`rxpck_s`每秒接收的数据包数量、`txpck_s`每秒发送的数据包数量、`rxkB_s`每秒接收的数据量、`txkB_s`每秒发送的数据量、`rxcmp_s`​每秒接收的压缩数据包数、`txcmp_s`​每秒发送的压缩数据包数、`rxmcst_s`每秒接收的多播数据包数、`ifutil`网络接口带宽利用率 |
| `sar_cpu_historicalinfo_collect_tool` | 进行历史状态分析，排查过去某时段cpu的性能问题 | - `host`：远程主机名/IP（本地查询可不填）<br>- `file`：sar要分析的log文件 <br>- `starttime`：分析开始的时间点<br>- `endtime`：分析结束的时间点 | 采集指标列表：`timestamp`采集时间点、含`user`用户空间程序占用CPU的百分比、`nice`低优先级用户进程占用的CPU百分比、`system`内核空间程序占用CPU的百分比、`iowait`CPU等待磁盘I/O操作的时间百分比、`steal`虚拟化环境中，其他虚拟机占用的CPU时间百分比、`idle`CPU空闲时间百分比 |
| `sar_memory_historicalinfo_collect_tool` | 进行历史状态分析，排查过去某时段内存的性能问题 | - `host`：远程主机名/IP（本地查询可不填）<br>- `file`：sar要分析的log文件 <br>- `starttime`：分析开始的时间点<br>- `endtime`：分析结束的时间点 | 采集指标列表：含`timestamp`采集时间点、`kbmemfree`物理空闲内存量、`kbavail`实际可用内存、`kbmemused`已使用的物理内存、`memused`已用内存占总物理内存的百分比、`kbbuffers`内核缓冲区（Buffer）占用的内存、`kbcached`​内核缓存（Cache）占用的内存、`kbcommit`当前工作负载所需的总内存量、`commit`kbcommit占系统总可用内存百分比、`kbactive`活跃内存、`kbinact`非活跃内存、`kbdirty`等待写入磁盘的脏数据量 |
| `sar_disk_historicalinfo_collect_tool` | 进行历史状态分析，排查过去某时段磁盘IO的性能问题 | - `host`：远程主机名/IP（本地查询可不填）<br>- `file`：sar要分析的log文件 <br>- `starttime`：分析开始的时间点<br>- `endtime`：分析结束的时间点 | 采集指标列表：含`timestamp`采集时间点、`name`磁盘设备名称、`tps`每秒传输次数、`rkB_s`每秒读取的数据量、`wkB_s`每秒写入的数据量、`dkB_s`每秒丢弃的数据量、`areq-sz`平均每次 I/O 请求的数据大小、`aqu-sz`平均 I/O 请求队列长度、`await`平均每次 I/O 请求的等待时间、`util`设备带宽利用率 |
| `sar_network_historicalinfo_collect_tool` | 进行历史状态分析，排查过去某时段网络的性能问题 | - `host`：远程主机名/IP（本地查询可不填）<br>- `file`：sar要分析的log文件 <br>- `starttime`：分析开始的时间点<br>- `endtime`：分析结束的时间点 | 采集指标列表：含`timestamp`采集时间点、`iface`网络接口名称、`rxpck_s`每秒接收的数据包数量、`txpck_s`每秒发送的数据包数量、`rxkB_s`每秒接收的数据量、`txkB_s`每秒发送的数据量、`rxcmp_s`​每秒接收的压缩数据包数、`txcmp_s`​每秒发送的压缩数据包数、`rxmcst_s`每秒接收的多播数据包数、`ifutil`网络接口带宽利用率 |

## 三、待开发需求
