# Specification Document for Swap Space Disabling MCP (Management Control Program)

## 1. Service Introduction
This service is an MCP (Management Control Program) based on the `swapoff` command for disabling swap space. Its core function is to disable swap space, release enabled swap partitions or swap files, and remove them from the system's memory management.

## 2. Core Tool Information
| Tool Name | Tool Function | Core Input Parameters | Key Return Content |
| ---- | ---- | ---- | ---- |
| `swapoff_disabling_swap_tool` | Disable swap space, release enabled swap partitions or swap files, and remove them from the system's memory management | - `host`: Remote hostname/IP (optional for local collection)<br>- `name`: Path of the swap space to be disabled | Boolean value indicating whether the specified swap space was successfully disabled |

## 3. To-be-developed Requirements
