# Specification Document for File Move and Rename MCP (Management Control Program)

## 1. Service Introduction
This service is an MCP (Management Control Program) based on the `mv` command for moving or renaming files or folders. Its core functionality is to move or rename specified files or folders.

## 2. Core Tool Information
| Tool Name | Tool Function | Core Input Parameters | Key Return Content |
| ---- | ---- | ---- | ---- |
| `mv_collect_tool` | Move or rename files/directories | - `host`: Remote hostname/IP (not required for local collection)<br>- `source`: Source file or directory <br>- `target`: Target file or directory | Boolean value indicating whether the mv operation was successful |

## 3. To-be-developed Requirements
