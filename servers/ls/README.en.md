# Specification Document for Ls Command MCP (Management Control Program)

## 1. Service Introduction
This service is an MCP (Management Control Program) based on the `ls` command for displaying directory structures. Its core function is to list the file structure of a specified directory.

## 2. Core Tool Information
| Tool Name | Tool Function | Core Input Parameters | Key Return Content |
| ---- | ---- | ---- | ---- |
| `ls_collect_tool` | List directory contents | - `host`: Remote hostname/IP (not required for local collection)<br>- `file`: Target file/directory | List of contents of the target directory |

## 3. To-be-developed Requirements
It is planned to develop a malicious process identification function based on the `top` command. By analyzing dimensions such as process memory usage characteristics, CPU usage, running duration, and process name legitimacy, it will assist in locating potential malicious processes and improve the security monitoring capability of device processes.