# Specification Document for File Deletion MCP (Management Control Program)

## 1. Service Introduction
This service is an MCP (Management Control Program) for file deletion based on the `rm` command, with the core functionality of deleting specified files or folders.

## 2. Core Tool Information
| Tool Name | Tool Function | Core Input Parameters | Key Return Content |
| ---- | ---- | ---- | ---- |
| `rm_collect_tool` | Deletes files or folders | - `host`: Remote hostname/IP (not required for local collection)<br>- `path`: Path of the file or folder to be deleted | Boolean value indicating whether the rm operation was successful |

## 3. To-be-developed Requirements
