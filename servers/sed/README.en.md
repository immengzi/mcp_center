# Sed Text Processing MCP (Management Control Program) Specification Document

## 1. Service Introduction
This service is an MCP (Management Control Program) based on the `sed` command for text processing. The core functions include text replacement and line deletion operations in specified files. It supports file operations on both local and remote hosts, and advanced text processing with various sed options (such as direct file modification).

## 2. Core Tool Information
| Tool Name | Tool Function | Core Input Parameters | Key Return Content |
| ---- | ---- | ---- | ---- |
| `sed_text_replace_tool` | Replace text matching a specified pattern in a file | - `host`: Remote hostname/IP (not required for local operations)<br>- `options`: sed options (optional), such as "-i" to modify the file directly<br>- `pattern`: The pattern to replace (supports regular expressions)<br>- `replacement`: The text to replace with<br>- `file`: The file path to operate on | A boolean indicating whether the operation was successful |
| `sed_text_delete_tool` | Delete lines matching a pattern from a file | - `host`: Remote hostname/IP (not required for local operations)<br>- `options`: sed options (optional), such as "-i" to modify the file directly<br>- `pattern`: The pattern of lines to delete (supports regular expressions)<br>- `file`: The file path to operate on | A boolean indicating whether the operation was successful |

## 3. To-be-developed Requirements
It is planned to add support for more sed command functions, such as text insertion and line number processing, to further enhance text processing capabilities.