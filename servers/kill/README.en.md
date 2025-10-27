# Process Control MCP (Management Control Program) Specification Document

## 1. Service Introduction
This service is a process control MCP (Management Control Program) implemented based on the `kill` command. Its core function is to perform refined control (termination, pause, resume, signal query, etc.) on local or remote processes by sending signals. All authentication information for remote operations is uniformly read from the configuration file, providing a secure and flexible standardized operation method for process management and troubleshooting.


## 2. Core Tool Information

| Tool Name | Tool Function | Core Input Parameters | Key Return Content |
| ---- | ---- | ---- | ---- |
| `kill_process` | Terminate processes by sending signals via the `kill` command (supports local/remote, default: SIGTERM(15)) | - `pid`: PID of the process to terminate (positive integer, required)<br>- `signal`: Signal number (integer, optional; common values: 9(SIGKILL), 15(SIGTERM))<br>- `host`: Remote hostname/IP (string, optional for local operations; must match the configuration file) | - `success`: Whether the operation is successful (boolean)<br>- `message`: Operation result description (string)<br>- `data`: Dictionary containing operation details<br>&nbsp;&nbsp;- `host`: Hostname/IP of the operation (local: `localhost`)<br>&nbsp;&nbsp;- `pid`: PID of the operated process<br>&nbsp;&nbsp;- `signal`: Number of the sent signal |
| `pause_process` | Pause processes by sending the `SIGSTOP` signal via the `kill` command (supports local/remote) | - `pid`: PID of the process to pause (positive integer, required)<br>- `host`: Remote hostname/IP (string, optional for local operations; must match the configuration file) | - `success`: Whether the operation is successful (boolean)<br>- `message`: Operation result description (string)<br>- `data`: Dictionary containing operation details<br>&nbsp;&nbsp;- `host`: Hostname/IP of the operation (local: `localhost`)<br>&nbsp;&nbsp;- `pid`: PID of the paused process |
| `resume_process` | Resume processes by sending the `SIGCONT` signal via the `kill` command (supports local/remote) | - `pid`: PID of the process to resume (positive integer, required)<br>- `host`: Remote hostname/IP (string, optional for local operations; must match the configuration file) | - `success`: Whether the operation is successful (boolean)<br>- `message`: Operation result description (string)<br>- `data`: Dictionary containing operation details<br>&nbsp;&nbsp;- `host`: Hostname/IP of the operation (local: `localhost`)<br>&nbsp;&nbsp;- `pid`: PID of the resumed process |
| `check_process_status` | Check if a local or remote process exists and its name information | - `pid`: PID of the process to check (positive integer, required)<br>- `host`: Remote hostname/IP (string, optional for local operations; must match the configuration file) | - `success`: Whether the query is successful (boolean)<br>- `message`: Query result description (string)<br>- `data`: Dictionary containing process status<br>&nbsp;&nbsp;- `host`: Hostname/IP of the query (local: `localhost`)<br>&nbsp;&nbsp;- `pid`: PID of the queried process<br>&nbsp;&nbsp;- `exists`: Whether the process exists (boolean)<br>&nbsp;&nbsp;- `name`: Process name (string, empty if the process does not exist) |
| `get_kill_signals` | View the meaning and function description of `kill` signals on local or remote servers | - `host`: Remote hostname/IP (string, optional for local queries; must match the configuration file) | - `success`: Whether the query is successful (boolean)<br>- `message`: Query result description (string)<br>- `data`: Dictionary containing signal information<br>&nbsp;&nbsp;- `host`: Hostname/IP of the query (local: `localhost`)<br>&nbsp;&nbsp;- `signals`: List of signals, each element includes:<br>&nbsp;&nbsp;&nbsp;&nbsp;- `number`: Signal number (integer)<br>&nbsp;&nbsp;&nbsp;&nbsp;- `name`: Signal name (e.g., `SIGTERM`)<br>&nbsp;&nbsp;&nbsp;&nbsp;- `description`: Signal function description |


## 3. Tool Usage Instructions
1. **Configuration File Dependence Rule**:  
   For all remote operations, remote host information (`host`/`port`/`username`/`password`) must be maintained in the configuration file first. When calling the tool, only the `host` parameter needs to be passed to automatically match the authentication information, without repeatedly passing the username/password.
2. **Distinction Between Local and Remote Operations**:  
   - Local operations: Do not fill in the `host` parameter; the tool will operate on local processes by default;  
   - Remote operations: Must fill in the `host` parameter (must be consistent with the host information in the configuration file), and there is no need to manually pass `port`/`username`/`password`.
3. **Signal Usage Specifications**:  
   - Process termination: By default, `SIGTERM(15)` is used (graceful termination, processes can capture and clean up resources); `SIGKILL(9)` is used for forced termination (uncatchable, terminates processes directly);  
   - Pause/resume: Only `SIGSTOP(19)` (pause) and `SIGCONT(18)` (resume) are supported; `SIGSTOP` cannot be ignored by processes, and `SIGCONT` is required to resume after pausing;  
   - Signal details: The `get_kill_signals` tool can be used to query all signals supported by the target system and their function descriptions.
4. **Suggestions for Process Status Verification**:  
   Before executing `kill_process`/`pause_process`/`resume_process`, it is recommended to call `check_process_status` first to confirm whether the process exists, avoiding errors caused by operating on invalid PIDs.


## 4. Notes
- **Permission Requirements**:  
  For local operations, if the process belongs to another user, the current user must have `sudo` permissions; for remote operations, the SSH user in the configuration file must have permissions to execute the `kill` and `ps` commands on the target process (process ownership can be confirmed via `ps -u username`).
- **Risks of Signal Usage**:  
  - Forced termination using `SIGKILL(9)` may cause loss of process memory data (e.g., unsaved files, database transactions); it is recommended to use `SIGTERM(15)` first;  
  - `SIGSTOP` only pauses process execution and does not release memory/port resources occupied by the process; the system resource usage should be evaluated for long-term pauses.
- **System Compatibility**:  
  Signal numbers and functions may vary by operating system (e.g., Linux, Unix); the result returned by `get_kill_signals` is subject to the actual support of the target system; Windows systems are not supported (no `kill` command or POSIX signal mechanism).
- **Suggestions for Error Troubleshooting**:  
  - Remote connection failure: First confirm network connectivity via `ping host`, then check whether `host`/`port`/`username`/`password` in the configuration file are correct;  
  - Process operation failure: If "Operation not permitted" is prompted, check user permissions; if "No such process" is prompted, confirm whether the PID is valid via `check_process_status`;  
  - Signal query failure: Ensure that the target system supports the `kill -l` command (supported by mainstream Linux/Unix systems).