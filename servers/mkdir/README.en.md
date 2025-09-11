# Specification Document for Folder Creation MCP (Management Control Program)

## 1. Service Introduction
This service is an MCP (Management Control Program) for folder creation based on the `mkdir` command, with the core functionality being the creation of folders.

## 2. Core Tool Information
| Tool Name | Tool Function | Core Input Parameters | Key Return Content |
| ---- | ---- | ---- | ---- |
| `mkdir_collect_tool` | Performs directory creation, supports batch creation, setting permissions, and recursive creation of multi-level directories | - `host`: Remote hostname/IP (not required for local collection)<br>- `dir`: Directory name to be created | Boolean value indicating whether the mkdir operation was successful |

## 3. To-be-developed Requirements
