# Specification Document for System Memory Overall Status Information Collection MCP (Management Control Program)

## 1. Service Introduction
This service is an MCP (Management Control Program) based on the `free` command for collecting overall system memory status information. Its core function is to accurately gather physical memory information of the target device, including total system memory, used system memory, free physical memory, and the amount of memory the system can allocate to new applications.

## 2. Core Tool Information
| Tool Name | Tool Function | Core Input Parameters | Key Return Content |
| ---- | ---- | ---- | ---- |
| `free_collect_tool` | Retrieve overall memory status information from the target device (local/remote) | - `host`: Remote hostname/IP (not required for local collection) | Memory information list (including `total` total system memory (MB), `used` used system memory (MB), `free` free physical memory (MB), `available` available system memory (MB)) |

## 3. To-be-developed Requirements
It is planned to develop a malicious process identification function based on the `top` command. By analyzing dimensions such as process memory usage characteristics, CPU usage, running duration, and process name legitimacy, it will assist in locating potential malicious processes and improve the security monitoring capability of device processes.