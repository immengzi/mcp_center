# lsof File & Network Monitoring MCP (Management Control Program) Specification Document

## 1. Service Introduction
This service is a multi-dimensional monitoring Management Control Program (MCP) implemented based on the `lsof` (List Open Files) tool. Its core functions include **open file list query, network connection (socket) analysis, and file-associated process location** for local or remote servers. It supports filtering by user, port, and protocol, enabling quick troubleshooting of file occupation conflicts, abnormal network connections, and process resource occupation issues, providing comprehensive data support for system operation and maintenance and fault location.


## 2. Core Tool Information

| Tool Name | Tool Function | Core Input Parameters | Key Return Content |
| ---- | ---- | ---- | ---- |
| `list_open_files` | Query the list of open files on local/remote hosts (supports filtering by file path and user) | - `path`: File path (optional, only shows the opening status of this file when specified)<br>- `user`: Username (optional, filters files opened by the specified user)<br>- `host`: Remote hostname/IP (default localhost, omit for local operation)<br>- `port`: SSH port (default 22, used for remote operation, overrides config port) | - `success`: Whether the operation succeeded (boolean)<br>- `message`: Operation result description (e.g., "Successfully obtained local open files, total 28")<br>- `data`: Dictionary containing file information<br>&nbsp;&nbsp;- `host`: Hostname/IP of the operation<br>&nbsp;&nbsp;- `file_count`: Total number of open files<br>&nbsp;&nbsp;- `files`: File list (each entry includes command/pid/user/fd/type/file_path etc.)<br>&nbsp;&nbsp;- `filter`: Filter criteria (path/user) |
| `list_network_files` | Query network connection-related files (network sockets) on local/remote hosts (supports filtering by protocol and port) | - `proto`: Protocol type (tcp/udp/all, default all)<br>- `port`: Port number (optional, filters network connections of the specified port)<br>- `host`: Remote hostname/IP (default localhost, omit for local operation)<br>- `ssh_port`: SSH port (default 22, used for remote operation, overrides config port) | - `success`: Whether the operation succeeded (boolean)<br>- `message`: Operation result description (e.g., "Successfully obtained TCP network connections of 192.168.1.100, total 15")<br>- `data`: Dictionary containing network connection information<br>&nbsp;&nbsp;- `host`: Hostname/IP of the operation<br>&nbsp;&nbsp;- `connection_count`: Total number of network connections<br>&nbsp;&nbsp;- `connections`: Connection list (each entry includes command/pid/user/local_address/foreign_address/state etc.)<br>&nbsp;&nbsp;- `filter`: Filter criteria (proto/port) |
| `find_process_by_file` | Find processes that open a specified file on local/remote hosts (accurately locate file-occupying processes) | - `path`: File path (required, e.g., /tmp/test.log, /var/log/nginx/access.log)<br>- `host`: Remote hostname/IP (default localhost, omit for local operation)<br>- `port`: SSH port (default 22, used for remote operation, overrides config port) | - `success`: Whether the operation succeeded (boolean)<br>- `message`: Operation result description (e.g., "Found 2 processes opening /tmp/test.log locally")<br>- `data`: Dictionary containing process information<br>&nbsp;&nbsp;- `host`: Hostname/IP of the operation<br>&nbsp;&nbsp;- `file_path`: Target file path<br>&nbsp;&nbsp;- `process_count`: Total number of related processes<br>&nbsp;&nbsp;- `processes`: Process list (each entry includes command/pid/user/fd etc.) |


## 3. Tool Usage Instructions
1. **Prerequisites**:  
   The target host must have the `lsof` tool installed (via `yum install lsof` or `apt install lsof`). The running user must have execution permissions (local ordinary users can query files opened by themselves; `sudo` is required to query files of all users or system-level files; remote operation requires the SSH user to have corresponding permissions).

2. **Local Operation Process**:  
   ① To view all open files: Call `list_open_files` directly, and you can add `user=root` to filter files of the root user;  
   ② To troubleshoot network connections: Call `list_network_files`, and specify `proto=tcp` and `port=80` to filter TCP connections on port 80;  
   ③ To locate file-occupying processes: Call `find_process_by_file` and pass `path=/tmp/locked.txt` to find processes occupying the file.

3. **Remote Operation Process**:  
   ① Ensure the remote host is configured in `remote_hosts` of `LsofConfig` (including host, name, port, username, password attributes);  
   ② Call the target tool (e.g., `list_network_files`) and pass `host=192.168.1.100` and filtering parameters;  
   ③ If the remote SSH port is not the default 22, add the `port=2222` parameter (for `list_open_files`/`find_process_by_file`) or `ssh_port=2222` parameter (for `list_network_files`).


## 4. Notes
- **File Path Format**: The `path` parameter must be a full path (e.g., /var/log/syslog, not the relative path log/syslog). No manual escaping is needed for paths with spaces, as the tool handles it internally.
- **Port Parameter Limit**: `port` must be an integer between 1-65535. Non-numeric values or values outside this range will directly return a parameter error.
- **Permission Impact**: If some processes or files are missing from the return result, confirm the execution user's permissions (add `sudo` locally, or use the root user for SSH login remotely to get complete data).
- **Remote Configuration Dependence**: Remote operations require the target host's authentication information (username, password) to be configured in `LsofConfig`; otherwise, the prompt "Authentication config for remote host not found" will appear.
- **Performance Tip**: Executing `list_open_files` (without filtering criteria) on hosts with a large number of files/processes may take a long time. It is recommended to add `path` or `user` filtering criteria to reduce the query scope.