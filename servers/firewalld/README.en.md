# firewalld Firewall Management MCP (Management Control Program) Specification Document

## 1. Service Introduction
This service is a firewall management control program (MCP) implemented based on the `firewalld` tool. Its core functions include **IP access control, port permission configuration, port forwarding setup, and firewall rule query** for local or remote servers. It supports switching between temporary and permanent rules and enables refined access control through rich rules, providing standardized operation interfaces for server security protection and network access management.


## 2. Core Tool Information

| Tool Name | Tool Function | Core Input Parameters | Key Return Content |
| ---- | ---- | ---- | ---- |
| `manage_ip_access` | Allow/deny access from specific IP/CIDR ranges (based on rich rules) | - `ip`: Target IP/CIDR (required, e.g., 192.168.1.100/24)<br>- `action`: Operation type (required, allow/deny)<br>- `zone`: Firewall zone (default: public)<br>- `protocol`: Protocol (tcp/udp/all, default: all)<br>- `permanent`: Whether to take permanent effect (default: True)<br>- `host`: Remote host name/IP (default: localhost)<br>- `port`: SSH port (default: 22) | - `success`: Whether the operation is successful (boolean)<br>- `message`: Operation result description (e.g., "Successfully allowed IP 192.168.1.100 to access the public zone")<br>- `data`: Dictionary containing configuration information<br>&nbsp;&nbsp;- `host`: Host name/IP of the operation<br>&nbsp;&nbsp;- `zone`: Applied zone<br>&nbsp;&nbsp;- `rule`: Rule details (ip/action/protocol) |
| `manage_port_access` | Add/remove access permissions for specific ports | - `port`: Port/port range (required, e.g., 80, 80-90)<br>- `protocol`: Protocol (tcp/udp, default: tcp)<br>- `action`: Operation type (required, add/remove)<br>- `zone`: Firewall zone (default: public)<br>- `permanent`: Whether to take permanent effect (default: True)<br>- `host`: Remote host name/IP (default: localhost)<br>- `ssh_port`: SSH port (default: 22) | - `success`: Whether the operation is successful (boolean)<br>- `message`: Operation result description (e.g., "Successfully added port 80/tcp access to the public zone")<br>- `data`: Dictionary containing configuration information<br>&nbsp;&nbsp;- `host`: Host name/IP of the operation<br>&nbsp;&nbsp;- `zone`: Applied zone<br>&nbsp;&nbsp;- `rule`: Rule details (port/protocol/action) |
| `configure_port_forward` | Configure port forwarding (source port → target IP:port) | - `source_port`: Source port (required, e.g., 80)<br>- `dest_ip`: Target IP (required, e.g., 192.168.2.100)<br>- `dest_port`: Target port (required, e.g., 8080)<br>- `protocol`: Protocol (tcp/udp, default: tcp)<br>- `action`: Operation type (add/remove, default: add)<br>- `zone`: Firewall zone (default: public)<br>- `permanent`: Whether to take permanent effect (default: True)<br>- `host`: Remote host name/IP (default: localhost)<br>- `port`: SSH port (default: 22) | - `success`: Whether the operation is successful (boolean)<br>- `message`: Operation result description (e.g., "Successfully configured port forwarding: 80/tcp → 192.168.2.100:8080")<br>- `data`: Dictionary containing forwarding rule information<br>&nbsp;&nbsp;- `host`: Host name/IP of the operation<br>&nbsp;&nbsp;- `zone`: Applied zone<br>&nbsp;&nbsp;- `forward_rule`: Forwarding details (source_port/dest_ip, etc.) |
| `list_firewall_rules` | Display firewall rules for a specific zone/all zones | - `zone`: Target zone (optional, query all zones if not filled)<br>- `host`: Remote host name/IP (default: localhost)<br>- `port`: SSH port (default: 22) | - `success`: Whether the operation is successful (boolean)<br>- `message`: Operation result description (e.g., "Successfully obtained rules for all zones, total 12 rules")<br>- `data`: Dictionary containing rule information<br>&nbsp;&nbsp;- `host`: Host name/IP of the operation<br>&nbsp;&nbsp;- `zone`: Queried zone<br>&nbsp;&nbsp;- `rule_count`: Total number of rules<br>&nbsp;&nbsp;- `rules`: List of rules (grouped by zone) |
| `list_firewall_zones` | Display information of all firewall zones (including default zone and associated interfaces) | - `host`: Remote host name/IP (default: localhost)<br>- `port`: SSH port (default: 22) | - `success`: Whether the operation is successful (boolean)<br>- `message`: Operation result description (e.g., "Successfully obtained information for 5 zones, default zone: public")<br>- `data`: Dictionary containing zone information<br>&nbsp;&nbsp;- `host`: Host name/IP of the operation<br>&nbsp;&nbsp;- `zone_count`: Total number of zones<br>&nbsp;&nbsp;- `default_zone`: Default zone<br>&nbsp;&nbsp;- `zones`: List of zones (including name, associated interfaces, etc.) |


## 3. Tool Usage Instructions
1. **Prerequisites**:  
   The target host must have the `firewalld` service installed (via `yum install firewalld` or `apt install firewalld`), and meet the following requirements:  
   - Local operation: The running user must have `root` or `sudo` privileges (all firewall operations require administrator privileges);  
   - Remote operation: The SSH user must be configured with `sudo` privileges (NOPASSWD is recommended to avoid interaction failures), and the `firewalld` service must be running (`systemctl start firewalld`).

2. **Local Operation Process**:  
   ① Allow access from a specific IP: Call `manage_ip_access(ip="192.168.1.200", action="allow")`;  
   ② Open Web ports: Call `manage_port_access(port="80-443", protocol="tcp", action="add")`;  
   ③ Configure port forwarding: Call `configure_port_forward(source_port=80, dest_ip="10.0.0.5", dest_port=8080)`;  
   ④ View all rules: Call `list_firewall_rules()`.

3. **Remote Operation Process**:  
   ① Ensure the remote host is configured in `remote_hosts` of `FirewalldConfig` (including host, name, port, username, and password attributes);  
   ② Call the target tool (e.g., `list_firewall_zones`) and pass the `host=192.168.1.100` parameter;  
   ③ If the remote SSH port is not the default 22, add the `port=2222` parameter; when performing configuration operations, ensure the remote user has `sudo` privileges.


## 4. Notes
- **Rule Activation Mechanism**: Temporary rules (`permanent=False`) take effect immediately but become invalid after the host restarts; permanent rules (`permanent=True`) require firewall reloading (the tool automatically executes `firewall-cmd --reload`) to take effect and are retained after restart.  
- **Port Forwarding Dependency**: Configuring port forwarding requires enabling masquerading. The tool automatically adds this rule to the target zone, no manual operation is needed.  
- **Permission Restrictions**: If "Permission denied" is prompted, switch to the `root` user or configure `sudo` for local operations; for remote operations, check the SSH user's `sudo` privileges and whether the authentication information is correct.  
- **Zone Selection**: The `zone` parameter uses the `public` zone by default. In production environments, it is recommended to divide dedicated zones (e.g., `dmz`, `internal`) based on network scenarios and associate them with corresponding network interfaces.  
- **Configuration Conflicts**: Avoid using `firewalld` and `iptables` tools simultaneously to manage the firewall, as this may cause rule conflicts; if switching is necessary, stop the `firewalld` service first (`systemctl stop firewalld`).