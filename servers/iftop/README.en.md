# iftop Network Traffic Monitoring MCP (Management Control Program) Specification Document

## 1. Service Introduction
This service is a network traffic monitoring management control program (MCP) implemented based on the `iftop` tool. Its core functions include **real-time traffic collection and connection analysis** for specified network interfaces on local or remote servers. It supports viewing total traffic statistics and top connection information, providing intuitive data support for network troubleshooting and bandwidth usage analysis.


## 2. Core Tool Information

| Tool Name | Tool Function | Core Input Parameters | Key Return Content |
| ---- | ---- | ---- | ---- |
| `get_interface_traffic` | Get real-time traffic data (including total traffic and top connections) of specified network interface via `iftop` | - `iface`: Network interface name (e.g., eth0, required)<br>- `sample_seconds`: Sampling duration (seconds, default 5s, range 3-30)<br>- `host`: Remote hostname/IP (default localhost, omit for local operation)<br>- `port`: SSH port (default 22, used for remote operation)<br>- `username`: SSH username (default root, required for remote operation)<br>- `password`: SSH password (required for remote operation) | - `success`: Whether the operation succeeded (boolean)<br>- `message`: Operation result description (e.g., "Successfully obtained interface traffic data")<br>- `data`: Dictionary containing traffic information<br>&nbsp;&nbsp;- `host`: Hostname/IP of the operation<br>&nbsp;&nbsp;- `total_stats`: Total traffic statistics<br>&nbsp;&nbsp;&nbsp;&nbsp;- `interface`: Interface name<br>&nbsp;&nbsp;&nbsp;&nbsp;- `tx_total`/`rx_total`: Total transmit/receive traffic (MB)<br>&nbsp;&nbsp;&nbsp;&nbsp;- `tx_rate_avg`/`rx_rate_avg`: Average transmit/receive rate (Mbps)<br>&nbsp;&nbsp;- `top_connections`: Top 10 connections list (sorted by receive rate) |
| `list_network_interfaces` | Get all network interface names of local or remote host (for selecting monitoring targets) | - `host`: Remote hostname/IP (default localhost, omit for local operation)<br>- `port`/`username`/`password`: Same as `get_interface_traffic` | - `success`: Whether the operation succeeded (boolean)<br>- `message`: Operation result description (e.g., "Successfully obtained 3 interface names")<br>- `data`: Dictionary containing interface list<br>&nbsp;&nbsp;- `host`: Hostname/IP of the operation<br>&nbsp;&nbsp;- `interfaces`: List of interface names (e.g., ["eth0", "lo"]) |


## 3. Tool Usage Instructions
1. **Prerequisites**：  
   The target host must have the `iftop` tool installed (install via `yum install iftop` or `apt install iftop`), and the running user must have execution permissions (local operation may require `sudo`, remote operation requires relevant permissions for SSH user).

2. **Local Operation Process**：  
   ① Call `list_network_interfaces` to get all local interface names (e.g., eth0, ens33);  
   ② Call `get_interface_traffic` with `iface` parameter (interface name from step ①) and sampling duration to get real-time traffic data of the interface.

3. **Remote Operation Process**：  
   ① Ensure the remote host is configured in `IftopConfig`'s `remote_hosts` (including host, name, port and other attributes);  
   ② Call `list_network_interfaces` with `host`, `username`, `password` to get remote interface list;  
   ③ Call `get_interface_traffic` with remote host information and target interface name to get traffic data.


## 4. Notes
- **Sampling Duration Limit**：`sample_seconds` must be set to 3-30 seconds (too short may lead to inaccurate data, too long will increase waiting time).
- **Interface Name Validation**：The `iface` parameter must be an actual interface name on the target host (query via `list_network_interfaces` for confirmation), otherwise an error will be returned.
- **Permission Issues**：If "permission denied" is prompted, ensure the executing user has `iftop` execution permission (add `sudo` for local operation, use SSH user with permissions for remote operation).
- **Output Parsing Compatibility**：The output format of `iftop` may vary slightly by version. If parsing exceptions occur, it is recommended to upgrade `iftop` to the latest stable version.
- **Network Environment Impact**：Sampling results of remote operations may be affected by network latency. It is recommended to use in a stable network environment.