# Specification Document for Process Information Collection MCP (Management Control Program)

## 1. Service Introduction
This service is an MCP (Management Control Program) for process information collection based on the `top` command. Its core function is to accurately collect process running data of target devices, providing basic data support for subsequent process analysis and resource monitoring.

## 2. Core Tool Information
| Category | Details |
| -------- | ------- |
| Tool Name | top_collect_tool |
| Tool Function | Using the `top` command to obtain information about the **top k processes with the highest memory usage** in the specified target (remote machine or local machine). (k is a configurable parameter, supporting setting specific values according to actual needs) |

## 3. To-be-developed Requirements
It is planned to develop a malicious process identification function based on the `top` command. By analyzing dimensions such as process memory usage characteristics, CPU usage, running duration, and process name legitimacy, it will assist in locating potential malicious processes and improve the security monitoring capability of device processes.