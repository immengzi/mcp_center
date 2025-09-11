# strace Process Tracking Toolset MCP (Management Control Program) Specification Document

## 1. Service Introduction
This service is a set of process tracking tools based on the `strace` command, providing comprehensive process behavior analysis capabilities that support monitoring of processes on local and remote servers. By tracing system calls, it can accurately capture file operations, permission issues, network interactions, and freeze causes of processes, providing underlying data support for development debugging, performance optimization, and troubleshooting.

## 2. Core Tool Information

| Tool Name | Function | Core Input Parameters | Key Return Content |
|---------|---------|---------------------|------------------|
| `strace_track_file_process` | Tracks file operations and running status of processes (e.g., opening, reading, writing files) | - `pid`: Target process PID (required)<br>- `host`: Remote host IP/hostname (optional for local tracking)<br>- `port`: SSH port (default 22)<br>- `username`/`password`: Required for remote tracking<br>- `output_file`: Log path (optional)<br>- `follow_children`: Track child processes (default False)<br>- `duration`: Tracking time (seconds, optional) | - `success`: Tracking start status<br>- `message`: Result description<br>- `strace_pid`: Tracker process ID<br>- `output_file`: Log path<br>- `target_pid`/`host`: Target process and host info |
| `strace_check_permission_file` | Troubleshoots "permission denied" and "file not found" errors | - `pid`: Target process PID (required)<br>- Remote parameters (`host`/`port`/`username`/`password`)<br>- `output_file`: Log path (optional)<br>- `duration`: Tracking time (default 30s) | - Basic status info (`success`/`message`, etc.)<br>- `errors`: Error statistics dictionary including:<br>&nbsp;&nbsp;- Permission denied details<br>&nbsp;&nbsp;- File not found details |
| `strace_check_network` | Diagnoses process network issues (connection failures, timeouts, DNS problems) | - `pid`: Target process PID (required)<br>- Remote parameters (same as above)<br>- `output_file`: Log path (optional)<br>- `duration`: Tracking time (default 30s)<br>- `trace_dns`: Track DNS calls (default True) | - Basic status info<br>- `errors`: Network error statistics including:<br>&nbsp;&nbsp;- Connection refused, timeout errors<br>&nbsp;&nbsp;- DNS resolution failure details (if enabled) |
| `strace_locate_freeze` | Identifies process freeze causes (IO blocking, lock waiting, etc.) | - `pid`: Target process PID (required)<br>- Remote parameters (same as above)<br>- `output_file`: Log path (optional)<br>- `duration`: Tracking time (default 30s)<br>- `slow_threshold`: Slow operation threshold (default 0.5s) | - Basic status info<br>- `analysis`: Freeze analysis dictionary including:<br>&nbsp;&nbsp;- Slow operation details<br>&nbsp;&nbsp;- Blocking type statistics<br>&nbsp;&nbsp;- Longest duration system calls |

## 3. Tool Usage Instructions
1. **Local/Remote Switching**:
   - Local tracking: Do not fill in `host`, `username`, `password` parameters
   - Remote tracking: Must provide complete remote connection info (`host`, `username`, `password`)

2. **Tracking Control**:
   - Duration control: Specify tracking seconds via `duration`; continuous tracking if not set
   - Log output: `output_file` is optional, default generates log file with PID and timestamp
   - Child process tracking: Only `strace_track_file_process` supports `follow_children`

3. **Scenario-specific Usage**:
   - File operation auditing: Use `strace_track_file_process`
   - Permission/file errors: Use `strace_check_permission_file`
   - Network issue diagnosis: Use `strace_check_network`
   - Performance freeze analysis: Use `strace_locate_freeze`

## 4. Notes
1. **Permission Requirements**:
   - Requires permission to trace target process (usually root privileges)
   - Remote host must have `strace` installed and SSH access enabled

2. **System Impact**:
   - `strace` increases target process CPU usage (approximately 5-10%); short tracking recommended in production
   - Processes with high-frequency system calls may generate large logs; monitor disk space

3. **Security Restrictions**:
   - Some security-hardened processes (e.g., `Dumpable: 0`) cannot be traced
   - Kernel parameter `kernel.yama.ptrace_scope` may restrict non-root tracking

4. **Result Interpretation**:
   - Error statistics based on system call return codes (e.g., EACCES for permission issues)
   - Slow operations determined by whether system call duration exceeds `slow_threshold`