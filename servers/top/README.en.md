# Specification Document for Process Information Collection MCP (Management Control Program)

## 1. Service Introduction
This service is an MCP (Management Control Program) for process information collection based on the `top` command. Its core function is to accurately collect process running data of target devices, providing basic data support for subsequent process analysis and resource monitoring.

## 2. Core Tool Information
| Tool Name | Tool Function | Core Input Parameters | Key Return Content |
| ---- | ---- | ---- | ---- |
| `top_collect_tool` | Obtain information of the **top k processes by memory usage** in the target device (local/remote), where k supports custom configuration | - `host`: Remote hostname/IP (not required for local collection)<br>- `k`: Number of processes to obtain (default 5) | Process list (including `pid` (process ID), `name` (process name), `memory` (memory usage in MB)) |
| `top_servers_tool` | Obtain server load information of the specified target (local or remote server) through the `top` command, which can get statuses such as CPU, memory, disk, network, and processes, providing data support for system operation and maintenance, performance analysis, and troubleshooting. | - `host`: Remote hostname/IP (not required for local collection)<br>- `dimensions`: cpu, memory, disk, network<br>- `include_processes`: bool<br>- `top_n`: int | - `server_info` (basic server information)<br>- `metrics` (requested dimension results, such as memory)<br>- `processes` (when `include_processes`=True)<br>- `error` |

## 3. To-be-Developed Requirements
It is planned to develop a malicious process identification function based on the `top` command. By analyzing dimensions such as process memory usage characteristics, CPU utilization, running duration, and process name legitimacy, it will assist in locating potential malicious processes and improve the security monitoring capability of device processes.