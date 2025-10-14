# netstat Network Connection Monitoring MCP (Management Control Program) Specification Document

## 1. Service Introduction
This service is a network connection monitoring Management Control Program (MCP) implemented based on the `netstat` tool. Its core functions include **network connection status query and specified port occupation detection** for local or remote servers. It supports TCP/UDP protocol filtering, connection status filtering, and process association analysis, providing accurate data support for network troubleshooting, port conflict location, and process occupation tracing.


## 2. Core Tool Information

| Tool Name | Tool Function | Core Input Parameters | Key Return Content |
| ---- | ---- | ---- | ---- |
| `query_network_connections` | Query the network connection list of local/remote hosts via `netstat` (supports TCP/UDP filtering and TCP status filtering) | - `proto`: Protocol type (tcp/udp/all, default all)<br>- `state`: Connection state (TCP-only, e.g., ESTABLISHED/LISTENING, default no filter)<br>- `host`: Remote hostname/IP (default localhost, omit for local operation)<br>- `port`: SSH port (default 22, used for remote operation, overrides config port) | - `success`: Whether the operation succeeded (boolean)<br>- `message`: Operation result description (e.g., "Successfully obtained local TCP connections, total 12")<br>- `data`: Dictionary containing connection data<br>&nbsp;&nbsp;- `host`: Hostname/IP of the operation<br>&nbsp;&nbsp;- `connection_count`: Total number of connections matching the criteria<br>&nbsp;&nbsp;- `connections`: Connection list (each entry includes protocol/recv_queue/local_ip/local_port/foreign_ip/foreign_port/state/pid/program fields)<br>&nbsp;&nbsp;- `filter`: Filter criteria (proto/state) |
| `check_port_occupation` | Detect the occupation of a specified port on local/remote hosts via `netstat` (including process association information) | - `port`: Port number (required, must be an integer between 1-65535, e.g., 80, 443)<br>- `proto`: Protocol type (tcp/udp, default tcp)<br>- `host`: Remote hostname/IP (default localhost, omit for local operation)<br>- `ssh_port`: SSH port (default 22, used for remote operation, overrides config port) | - `success`: Whether the operation succeeded (boolean)<br>- `message`: Operation result description (e.g., "Port 80/TCP on remote host 192.168.1.100 is occupied by: nginx")<br>- `data`: Dictionary containing port occupation data<br>&nbsp;&nbsp;- `host`: Hostname/IP of the operation<br>&nbsp;&nbsp;- `check_port`: Checked port number<br>&nbsp;&nbsp;- `proto`: Checked protocol<br>&nbsp;&nbsp;- `is_occupied`: Whether the port is occupied (boolean)<br>&nbsp;&nbsp;- `occupations`: Occupation list (each entry includes protocol/local_ip/pid/program/state fields) |


## 3. Tool Usage Instructions
1. **Prerequisites**:  
   The target host must have the `netstat` tool installed (usually pre-installed with the `net-tools` package; if missing, install via `yum install net-tools` or `apt install net-tools`). The running user must have execution permissions (local operation may require `sudo`, remote operation requires relevant permissions for the SSH user).

2. **Local Operation Process**:  
   ① Call `query_network_connections`, and you can specify `proto` (e.g., tcp) and `state` (e.g., LISTENING) to filter target connections;  
   ② If you need to detect a specific port, call `check_port_occupation` and pass `port` (e.g., 80) and `proto` (e.g., tcp) to get occupation information.

3. **Remote Operation Process**:  
   ① Ensure the remote host is configured in `remote_hosts` of `NetstatConfig` (including host, name, port, username, password attributes);  
   ② Call `query_network_connections` and pass `host` (e.g., 192.168.1.100) and filtering parameters to get the remote connection list;  
   ③ Call `check_port_occupation` and pass `host` and `port` (e.g., 443) to detect the remote port occupation;  
   ④ If the remote SSH port is not the default 22, supplement the `port` parameter (for `query_network_connections`) or `ssh_port` parameter (for `check_port_occupation`).


## 4. Notes
- **Protocol and State Matching**: The `state` parameter is only valid for `proto=tcp`. UDP has no connection state, so avoid invalid combinations during filtering.
- **Port Parameter Validation**: `port` must be an integer between 1-65535. Non-numeric values or values outside this range will directly return a parameter error.
- **Configuration Dependence**: Remote operations require the target host's authentication information (username, password) to be correctly configured in `NetstatConfig`; otherwise, the prompt "Authentication config for remote host not found" will appear.
- **Permission Impact**: If "permission denied" is returned or the process information is "-", ensure the executing user has permission to run `netstat -p` (add `sudo` for local operation, use an SSH user with root or sudo permissions for remote operation).
- **Command Compatibility**: Some systems (e.g., Alpine) may require the `ss` command instead of `netstat`. In this case, install the `net-tools` package first; otherwise, command execution will fail.