# ifconfig Network Interface Information Monitoring MCP (Management Control Program) Specification Document

## 1. Service Introduction
This service is a network interface information monitoring Management Control Program (MCP) implemented based on the `ifconfig` tool. Its core functions include **querying detailed information of network interfaces and extracting IP addresses of specified interfaces** on local or remote servers. It supports obtaining key information such as interface status, MAC address, IPv4/IPv6 address, subnet mask, MTU value, and transmit/receive traffic statistics, providing basic data support for network configuration verification and interface troubleshooting.


## 2. Core Tool Information

| Tool Name | Tool Function | Core Input Parameters | Key Return Content |
| ---- | ---- | ---- | ---- |
| `get_network_interfaces` | Query detailed information of network interfaces on local/remote hosts (supports specifying a single interface or returning all interfaces) | - `iface`: Interface name (optional, e.g., eth0, returns all interfaces if not specified)<br>- `host`: Remote hostname/IP (default localhost, omit for local operation)<br>- `port`: SSH port (default 22, used for remote operation, overrides config port) | - `success`: Whether the operation succeeded (boolean)<br>- `message`: Operation result description (e.g., "Successfully obtained information of all local interfaces, total 3")<br>- `data`: Dictionary containing interface information<br>&nbsp;&nbsp;- `host`: Hostname/IP of the operation<br>&nbsp;&nbsp;- `interface_count`: Total number of interfaces<br>&nbsp;&nbsp;- `interfaces`: Interface list (each entry includes name/status/mac_address/ipv4/ipv6/mtu/statistics etc.)<br>&nbsp;&nbsp;- `filter`: Filter criteria (iface) |
| `get_interface_ip` | Query IP address information of specified interface on local/remote hosts (focus on extracting IPv4/IPv6 addresses) | - `iface`: Interface name (required, e.g., eth0, ens33)<br>- `host`: Remote hostname/IP (default localhost, omit for local operation)<br>- `port`: SSH port (default 22, used for remote operation, overrides config port) | - `success`: Whether the operation succeeded (boolean)<br>- `message`: Operation result description (e.g., "Successfully obtained IP address information of eth0")<br>- `data`: Dictionary containing IP information<br>&nbsp;&nbsp;- `host`: Hostname/IP of the operation<br>&nbsp;&nbsp;- `interface`: Interface name<br>&nbsp;&nbsp;- `ipv4`: IPv4 address information (address/subnet_mask/broadcast)<br>&nbsp;&nbsp;- `ipv6`: IPv6 address information (address) |


## 3. Tool Usage Instructions
1. **Prerequisites**:  
   The target host must have the `ifconfig` tool installed (usually pre-installed with the `net-tools` package; if missing, install via `yum install net-tools` or `apt install net-tools`). The running user must have execution permissions (local ordinary users can query, remote operation requires the SSH user to have relevant permissions).

2. **Local Operation Process**:  
   ① To view detailed information of all interfaces: Call `get_network_interfaces()` directly;  
   ② To view information of a specific interface (e.g., eth0): Call `get_network_interfaces(iface="eth0")`;  
   ③ To only obtain the IP address of an interface: Call `get_interface_ip(iface="eth0")`, which focuses on returning IPv4/IPv6 related information.

3. **Remote Operation Process**:  
   ① Ensure the remote host is configured in `remote_hosts` of `IfconfigConfig` (including host, name, port, username, password attributes);  
   ② Call the target tool (e.g., `get_network_interfaces`) and pass `host=192.168.1.100` and optional parameters;  
   ③ If the remote SSH port is not the default 22, add the `port=2222` parameter.


## 4. Notes
- **Accuracy of Interface Name**: The `iface` parameter must match the actual interface name of the target host (all interface names can be obtained by calling `get_network_interfaces` without parameters); otherwise, "No information found for interface" will be returned.
- **Command Compatibility**: Some new systems (e.g., CentOS 8+/Ubuntu 20+) use the `ip` command instead of `ifconfig` by default. In this case, install the `net-tools` package first; otherwise, "command not found" will be prompted.
- **Permission Impact**: Ordinary users may not be able to view some advanced statistical information, but basic information such as IP addresses and status can still be obtained normally.
- **IPv6 Support**: If the host is not configured with IPv6, the `ipv6.address` field will return an empty value, which is normal.
- **Remote Configuration Dependence**: Remote operations require the target host's authentication information (username, password) to be configured in `IfconfigConfig`; otherwise, the prompt "Authentication config for remote host not found" will appear.