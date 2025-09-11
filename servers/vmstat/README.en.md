# Specification Document for System Resource Interaction Bottleneck Information Collection MCP (Management Control Program)

## 1. Service Introduction
This service is an MCP (Management Control Program) based on the `vmstat` command for collecting system resource interaction bottleneck information. Its core function is to monitor the overall status of system resources in real-time, allowing for a one-time view of key metrics such as CPU, memory, I/O, interrupts, and context switches. It quickly identifies performance bottlenecks (such as CPU overload, insufficient memory, disk I/O blocking, or process blocking).

## 2. Core Tool Information
| Tool Name | Tool Function | Core Input Parameters | Key Return Content |
| ---- | ---- | ---- | ---- |
| `vmstat_collect_tool` | Obtain the overall status of target device resources | - `host`: Remote hostname/IP (not required for local collection) | System resource status dictionary (including `r` running queue process count, `b` processes waiting for I/O, `si` data loaded from disk to memory per second (KB/s), `so` data swapped from memory to disk per second (KB/s), `bi` blocks read from disk, `bo` blocks written to disk, `in` interrupts per second, including clock interrupts, `cs` context switches per second, `us` CPU time consumed by user processes, `sy` CPU time consumed by kernel processes, `id` CPU idle time, `wa` percentage of CPU time waiting for I/O completion, `st` percentage of CPU time stolen by virtual machines) |
| `vmstat_slabinfo_collect_tool` | Obtain statistical information on kernel slab memory cache (slabinfo) | - `host`: Remote hostname/IP (not required for local queries) | Detailed dictionary of slab memory cache information (including `cache` name of the slab cache in the kernel, `num` number of currently active cache objects, `total` total number of objects in the cache, `size` size of each cache object, `pages` number of cache objects per slab) |

## 3. To-be-developed Requirements
It is planned to develop a malicious process identification function based on the `top` command. By analyzing dimensions such as process memory usage characteristics, CPU usage, running duration, and process name legitimacy, it will assist in locating potential malicious processes and improve the security monitoring capability of device processes.