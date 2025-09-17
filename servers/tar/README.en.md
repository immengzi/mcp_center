# Specification Document for Tar Command MCP (Management Control Program)

## 1. Service Introduction
This service is an MCP (Management Control Program) based on the `tar` command, designed for archiving and extracting files or directories. Its core functions include packaging, compressing, unpacking, and restoring specified files or directories to meet requirements for data backup, migration, and distribution.

## 2. Core Tool Information
| Tool Name | Tool Function | Core Input Parameters | Key Return Content |
| ---- | ---- | ---- | ---- |
| `tar_extract_file_tool` | Extract files or directories using the tar command | - `host`: Remote hostname or IP address (optional for local operations)<br>- `options`: tar command options (e.g., `-xzvf`)<br>- `file`: Path to the archive file<br>- `extract_path`: Directory to extract files to | Boolean value indicating whether the extraction was successful |
| `tar_compress_file_tool` | Compress files or directories using the tar command | - `host`: Remote hostname or IP address (optional for local operations)<br>- `options`: tar command options (e.g., `-czvf`, `-xzvf`)<br>- `source_path`: Path to the file or directory to compress<br>- `archive_path`: Output path for the archive file | Boolean value indicating whether the compression was successful |

## 3. To-be-developed Requirements
