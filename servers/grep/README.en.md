# File Content Search MCP (Management Control Program) Specification Document

## 1. Service Introduction
This service is an MCP (Management Control Program) based on the `grep` command for searching file contents. The core function is to search for lines containing specific patterns in specified files. It supports file searching on both local and remote hosts, and advanced searching with various grep options (such as case-insensitive search, displaying line numbers, etc.).

## 2. Core Tool Information
| Tool Name | Tool Function | Core Input Parameters | Key Return Content |
| ---- | ---- | ---- | ---- |
| `grep_search_tool` | Search for specified patterns in files | - `host`: Remote hostname/IP (not required for local search)<br>- `options`: grep options (optional), such as "-i" for case insensitive, "-n" for line numbers, etc.<br>- `pattern`: The pattern to search for (supports regular expressions)<br>- `file`: The file path to search | A string containing matching lines, or a corresponding prompt message if no matches are found |

## 3. To-be-developed Requirements