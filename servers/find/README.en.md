# Specification Document for Process Information Collection MCP (Management Control Program)

## 1. Service Introduction
This service is an MCP (Management Control Program) based on the `find` command for file searching. Its core functionality is to recursively search for files or directories, supporting precise targeting based on multiple conditions. It can search by file name, filter by size, and sort by time.

## 2. Core Tool Information
| Tool Name | Tool Function | Core Input Parameters | Key Return Content |
| ---- | ---- | ---- | ---- |
| `find_with_name_tool` | Search for files by name in a specified directory | - `host`: Remote hostname/IP (not required for local collection)<br>- `path`: Directory to search<br>- `name`: File name to search for | List of found files (including `file` with specific file paths that meet the search criteria) |
| `find_with_date_tool` | Search for files by modification time in a specified directory | - `host`: Remote hostname/IP (not required for local collection)<br>- `path`: Directory to search<br>- `name`: File name to search for | List of found files (including `file` with specific file paths that meet the search criteria) |
| `find_with_size_tool` | Search for files by size in a specified directory | - `host`: Remote hostname/IP (not required for local collection)<br>- `path`: Directory to search<br>- `name`: File name to search for | List of found files (including `file` with specific file paths that meet the search criteria) |

## 3. To-be-developed Requirements
