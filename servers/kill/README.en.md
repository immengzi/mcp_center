# Process Control MCP (Management Control Program) Specification Document

## 1. Service Introduction
This service is an MCP (Management Control Program) for process control based on the `kill` command. Its core function is to perform refined control (pause, resume, signal query, etc.) on local or remote processes by sending signals, providing flexible operation means for process management and troubleshooting.

## 2. Core Tool Information

| Tool Name | Tool Function | Core Input Parameters | Key Return Content |
| ---- | ---- | ---- | ---- |
| `pause_process` | Pauses processes by sending `SIGSTOP` signal via `kill` command (supports local/remote) | - `pid`: PID of the process to pause (positive integer, required)<br>- `host`: Remote host name/IP (default `localhost`, optional for local operations)<br>- `port`: SSH port (default 22, used for remote operations)<br>- `username`: SSH username (default `root`, required for remote operations)<br>- `password`: SSH password (mandatory for remote operations) | - `success`: Whether the operation succeeded (boolean)<br>- `message`: Description of operation result (string)<br>- `data`: Dictionary containing operation details<br>&nbsp;&nbsp;- `host`: Hostname/IP of the operation<br>&nbsp;&nbsp;- `pid`: PID of the paused process |
| `resume_process` | Resumes processes by sending `SIGCONT` signal via `kill` command (supports local/remote) | - `pid`: PID of the process to resume (positive integer, required)<br>- `host`: Remote host name/IP (default `localhost`, optional for local operations)<br>- `port`: SSH port (default 22, used for remote operations)<br>- `username`: SSH username (default `root`, required for remote operations)<br>- `password`: SSH password (mandatory for remote operations) | - `success`: Whether the operation succeeded (boolean)<br>- `message`: Description of operation result (string)<br>- `data`: Dictionary containing operation details<br>&nbsp;&nbsp;- `host`: Hostname/IP of the operation<br>&nbsp;&nbsp;- `pid`: PID of the resumed process |
| `get_kill_signals` | Views the meanings and functional descriptions of `kill` signals on local or remote servers | - `host`: Remote host name/IP (optional for local queries)<br>- `port`: SSH port (default 22, used for remote queries)<br>- `username`: SSH username (required for remote queries)<br>- `password`: SSH password (mandatory for remote queries) | - `success`: Whether the query succeeded (boolean)<br>- `message`: Description of query result (string)<br>- `data`: Dictionary containing signal information<br>&nbsp;&nbsp;- `host`: Hostname/IP of the query (`localhost` for local)<br>&nbsp;&nbsp;- `signals`: List of signals, each containing:<br>&nbsp;&nbsp;&nbsp;&nbsp;- `number`: Signal number (integer)<br>&nbsp;&nbsp;&nbsp;&nbsp;- `name`: Signal name (e.g., `SIGTERM`)<br>&nbsp;&nbsp;&nbsp;&nbsp;- `description`: Signal function explanation |

## 3. Tool Usage Instructions
1. **Local Operations**: Do not fill in `host`, `username`, and `password` parameters; operations will be performed on local processes by default.
2. **Remote Operations**: Must provide `host`, `username`, and `password` parameters; `port` is optional (default 22).
3. Signal Description: `pause_process` and `resume_process` rely on `SIGSTOP` (pause) and `SIGCONT` (resume) signals respectively. All supported signals and their functions can be queried via `get_kill_signals`.

## 4. Notes
- Corresponding permissions are required to operate processes (local operations may require `sudo`, remote operations require SSH users to have process control permissions).
- Pausing a process (`SIGSTOP`) will freeze process execution; after resumption, it will continue running from the pause point without data loss.
- Signal functions may vary by operating system version; the results returned by `get_kill_signals` are subject to the actual support of the target system.