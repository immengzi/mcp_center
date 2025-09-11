# Specification Document for Swap Space Information Collection MCP (Management Control Program)

## 1. Service Introduction
This service is an MCP (Management Control Program) based on the `swapon` command for process information collection. Its core function is to activate and manage swap space, including enabling swap devices/files and viewing the current swap status.

## 2. Core Tool Information
| Tool Name | Tool Function | Core Input Parameters | Key Return Content |
| ---- | ---- | ---- | ---- |
| `swapon_collect_tool` | Retrieve the current swap device status from the target device (local/remote) | - `host`: Remote hostname/IP (not required for local collection) | List of swap devices (including `name` - the device or file path corresponding to the swap space, `type` - the type of swap space, `size` - the total size of the swap space, `used` - the amount of swap space currently used, `prio` - the priority of the swap space) |

## 3. To-be-developed Requirements
