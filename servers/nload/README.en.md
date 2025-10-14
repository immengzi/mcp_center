# Nload Bandwidth Monitoring MCP (Management Control Program) Specification Document

## 1. Service Introduction
This service is a bandwidth monitoring management control program (MCP) implemented based on the `nload` tool. Its core functions include **real-time bandwidth collection and traffic analysis** for specified network interfaces on local or remote servers. It supports viewing current rate, average rate, maximum rate, and total traffic of inbound/outbound traffic, providing intuitive data support for bandwidth load evaluation and network resource optimization.


## 2. Core Tool Information

| Tool Name | Tool Function | Core Input Parameters | Key Return Content |
| ---- | ---- | ---- | ---- |
| `monitor_bandwidth` | Get real-time bandwidth data of specified interface via `nload` (including inbound/outbound traffic details) | - `iface`: Network interface name (e.g., eth0, required)<br>- `duration`: Monitoring duration (seconds, default 10s, range 5-60)<br>- `host`: Remote hostname/IP (default localhost, omit for local operation)<br>- `port`: SSH port (default 22, used for remote operation) | - `success`: Whether the operation succeeded (boolean)<br>- `message`: Operation result description (e.g., "Successfully obtained interface bandwidth data")<br>- `data`: Dictionary containing bandwidth information<br>&nbsp;&nbsp;- `host`: Hostname/IP of the operation<br>&nbsp;&nbsp;- `monitor_duration`: Actual monitoring duration (seconds)<br>&nbsp;&nbsp;- `bandwidth`: Bandwidth monitoring data<br>&nbsp;&nbsp;&nbsp;&nbsp;- `interface`: Interface name<br>&nbsp;&nbsp;&nbsp;&nbsp;- `incoming`: Inbound traffic (current/average/maximum/total/unit)<br>&nbsp;&nbsp;&nbsp;&nbsp;- `outgoing`: Outbound traffic (same structure as incoming) |
| `list_network_interfaces` | Get all network interface names of local or remote host (for selecting monitoring targets) | - `host`: Remote hostname/IP (default localhost, omit for local operation)<br>- `port`: SSH port (default 22, used for remote operation) | - `success`: Whether the operation succeeded (boolean)<br>- `message`: Operation result description (e.g., "Successfully obtained 3 interface names")<br>- `data`: Dictionary containing interface list<br>&nbsp;&nbsp;- `host`: Hostname/IP of the operation<br>&nbsp;&nbsp;- `interfaces`: List of interface names (e.g., ["eth0", "lo"]) |


## 3. Tool Usage Instructions
1. **Prerequisites**：  
   The target host must have the `nload` tool installed (via `yum install -y nload` or `apt install -y nload`), and the running user must have execution permissions (local operation may require `sudo`, remote operation requires relevant permissions for SSH user).

2. **Local Operation Process**：  
   ① Call `list_network_interfaces` to get all local interface names (e.g., eth0, ens33);  
   ② Call `monitor_bandwidth` with `iface` parameter (interface name from step ①) and monitoring duration to get real-time bandwidth data of the interface.

3. **Remote Operation Process**：  
   ① Ensure the remote host is configured in `NloadConfig`'s `remote_hosts` (including host, name, port, username, password attributes);  
   ② Call `list_network_interfaces` with `host` parameter to get remote interface list;  
   ③ Call `monitor_bandwidth` with `host`, `iface` and monitoring duration to get remote interface bandwidth data.


## 4. Notes
- **Monitoring Duration Limit**：`duration` must be set to 5-60 seconds (too short may lead to inaccurate data, too long will increase waiting time).
- **Interface Name Validation**：The `iface` parameter must be an actual interface name on the target host (query via `list_network_interfaces` for confirmation), otherwise an error will be returned.
- **Configuration Dependence**：Remote operation requires the target host's authentication info (username, password) to be correctly configured in `NloadConfig`, otherwise "incomplete authentication config" will be prompted.
- **Unit Compatibility**：The rate unit in the return result is uniformly Mbps (Kbps is converted automatically), and the total traffic unit follows `nload` output (e.g., MB, GB).
- **Version Adaptation**：The output format of `nload` may vary slightly by version. If parsing exceptions occur, it is recommended to upgrade to the latest stable version (`yum update nload` or `apt upgrade nload`).