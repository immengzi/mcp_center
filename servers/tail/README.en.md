# Specification Document for Tail Command MCP (Management Control Program)

## 1. Service Introduction
This service is an MCP (Management Control Program) based on the `tail` command, designed to view the content at the end of a file. Its core functionality is to display the last few lines of a specified file.

## 2. Core Tool Information
| Tool Name | Tool Function | Core Input Parameters | Key Return Content |
| ---- | ---- | ---- | ---- |
| `tail_file_view_tool` | Quickly view the content at the end of a file | - `host`: Remote hostname/IP (not required for local collection)<br>- `num`: Number of lines to view at the end of the file, default is 10 lines<br>- `file`: Path to the file to be viewed | File content string |

## 3. To-be-developed Requirements
