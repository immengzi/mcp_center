# Specification Document for Head Command MCP (Management Control Program)

## 1. Service Introduction
This service is an MCP (Management Control Program) based on the `head` command, designed to view the initial content of a file. Its core functionality is to display the first few lines of a specified file.

## 2. Core Tool Information
| Tool Name | Tool Function | Core Input Parameters | Key Return Content |
| ---- | ---- | ---- | ---- |
| `head_file_view_tool` | Quickly view the initial content of a file | - `host`: Remote hostname/IP (not required for local collection)<br>- `num`: Number of lines to view from the beginning of the file, default is 10 lines<br>- `file`: Path to the file to be viewed | File content string |

## 3. To-be-developed Requirements
