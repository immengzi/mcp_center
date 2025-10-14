# tshark Network Packet Capture & Analysis MCP (Management Control Program) Specification Document

## 1. Service Introduction
This service is a network traffic management control program (MCP) implemented based on the `tshark` (Wireshark command-line version) tool. Its core functions include **real-time packet capture of specified interfaces, custom-filtered capture, and network protocol distribution statistics** for local or remote servers. It supports limiting capture scope by duration/packet count, and can extract key information such as source/destination IP, port, and protocol type of packets, providing low-level data support for network fault location, traffic anomaly analysis, and protocol compliance detection.


## 2. Core Tool Information

| Tool Name | Tool Function | Core Input Parameters | Key Return Content |
| ---- | ---- | ---- | ---- |
| `capture_packets` | Capture network packets of specified interface (supports limits by duration, packet count, and filter rules) | - `iface`: Interface name (required, e.g., eth0, ens33)<br>- `duration`: Capture duration (seconds, default 10, range 3-60)<br>- `count`: Maximum number of packets to capture (optional, e.g., 100, stops when reached)<br>- `filter`: Capture filter rule (optional, e.g., `tcp port 80`, follows pcap syntax)<br>- `host`: Remote hostname/IP (default localhost, omit for local operation)<br>- `port`: SSH port (default 22, used for remote operation, overrides config port) | - `success`: Whether the operation succeeded (boolean)<br>- `message`: Operation result description (e.g., "Successfully captured 58 packets on local interface eth0")<br>- `data`: Dictionary containing capture data<br>&nbsp;&nbsp;- `host`: Hostname/IP of the operation<br>&nbsp;&nbsp;- `interface`: Interface name<br>&nbsp;&nbsp;- `capture_params`: Capture parameters (duration/count/filter)<br>&nbsp;&nbsp;- `packet_count`: Actual number of captured packets<br>&nbsp;&nbsp;- `packets`: Packet list (each entry includes packet_id/timestamp/src_ip/dst_ip etc.) |
| `analyze_protocol_stats` | Analyze network protocol distribution of specified interface (counts proportion of packets per protocol) | - `iface`: Interface name (required, e.g., eth0, ens33)<br>- `duration`: Analysis duration (seconds, default 10, range 3-60)<br>- `filter`: Analysis filter rule (optional, e.g., `ip`, only statistics on qualified traffic)<br>- `host`: Remote hostname/IP (default localhost, omit for local operation)<br>- `port`: SSH port (default 22, used for remote operation, overrides config port) | - `success`: Whether the operation succeeded (boolean)<br>- `message`: Operation result description (e.g., "Successfully analyzed protocol distribution of local interface eth0, captured 120 packets")<br>- `data`: Dictionary containing statistical data<br>&nbsp;&nbsp;- `host`: Hostname/IP of the operation<br>&nbsp;&nbsp;- `interface`: Interface name<br>&nbsp;&nbsp;- `analysis_params`: Analysis parameters (duration/filter)<br>&nbsp;&nbsp;- `stats`: Protocol statistics (total_packets, protocols count per protocol) |


## 3. Tool Usage Instructions
1. **Prerequisites**:  
   The target host must have the `tshark` tool installed (via `yum install wireshark-cli` or `apt install tshark`), and the running user must have the following permissions:  
   - Local operation: Ordinary users can capture packets, but on some systems, the user needs to be added to the `wireshark` user group (execute `usermod -aG wireshark username`);  
   - Remote operation: The SSH user must have permission to execute `tshark`; if capturing all traffic is required, sudo privileges may be needed.

2. **Local Operation Process**:  
   ① Basic capture: Call `capture_packets(iface="eth0")`, which captures packets on the eth0 interface for 10 seconds by default;  
   ② Restricted capture: Call `capture_packets(iface="eth0", duration=20, count=200, filter="udp port 53")` to capture DNS packets on eth0 for 20 seconds or 200 packets (stops when either limit is reached);  
   ③ Protocol analysis: Call `analyze_protocol_stats(iface="eth0", duration=15)` to count all protocol distributions on the eth0 interface within 15 seconds.

3. **Remote Operation Process**:  
   ① Ensure the remote host is configured in `remote_hosts` of `TsharkConfig` (including host, name, port, username, password attributes);  
   ② Call the target tool (e.g., `capture_packets`) and pass `host=192.168.1.100` and parameters such as `iface`;  
   ③ If the remote SSH port is not the default 22, add the `port=2222` parameter; if remote capture requires sudo, configure a user with sudo privileges in `TsharkConfig`.


## 4. Notes
- **Capture Filter Rules**: The `filter` parameter must follow pcap filter syntax (e.g., `tcp` captures only TCP packets, `src host 192.168.1.5` captures only packets with source IP 192.168.1.5). Syntax errors will cause capture failure.
- **Permission Restrictions**: If local capture prompts "Permission denied", add the user to the `wireshark` group and log in again; if remote capture fails, check if the SSH user has permission to execute `tshark`.
- **Performance Impact**: Long-term or unfiltered capture may occupy high CPU/memory. It is recommended to set `duration` and `filter` appropriately in production environments to avoid affecting services.
- **Data Volume Control**: The `count` parameter should be set to a reasonable value (e.g., within 1000). Too many packets will result in excessively large return results, affecting transmission efficiency.
- **Remote Configuration Dependence**: Remote operations require complete authentication information (username, password) of the target host to be configured in `TsharkConfig`; otherwise, the prompt "Authentication config for remote host not found" will appear.