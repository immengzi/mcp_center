# iptables Firewall Management MCP (Management Control Program) Specification Document

## 1. Service Introduction
This service is an underlying network security management control program (MCP) implemented based on `iptables` (a Linux kernel-level firewall tool). Its core functions include **IP access control rule management, port forwarding configuration, IP forwarding function switch, and firewall rule query** for local or remote servers. As a tool that directly operates the netfilter kernel module, `iptables` supports refined packet filtering logic and complex NAT (Network Address Translation) configuration. It is suitable for scenarios requiring custom chains and advanced routing rules, providing underlying technical support for server security protection, traffic control, and fault location.


## 2. Core Tool Information

| Tool Name | Tool Function | Core Input Parameters | Key Return Content |
| ---- | ---- | ---- | ---- |
| `manage_ip_rule` | Add/remove IP access control rules (allow/deny TCP/UDP/all-protocol traffic from specific IPs) | - `ip`: Target IP/CIDR (required, e.g., 192.168.1.100/24)<br>- `action`: Action (required, ACCEPT/DROP/REJECT)<br>- `chain`: Rule chain (INPUT/OUTPUT/FORWARD, default INPUT)<br>- `protocol`: Protocol (tcp/udp/all, default all)<br>- `port`: Port number (optional, e.g., 80, only valid for tcp/udp protocols)<br>- `action_type`: Operation type (add/delete, default add)<br>- `save`: Whether to save rules (True/False, default False, persists after reboot if saved)<br>- `host`: Remote hostname/IP (default localhost, omit for local operation)<br>- `port`: SSH port (default 22, used for remote operation, overrides config port) | - `success`: Operation success status (boolean)<br>- `message`: Operation result description (e.g., "Successfully added rule: ACCEPT tcp traffic from 192.168.1.0/24 (port 80), saved")<br>- `data`: Dictionary containing rule information<br>&nbsp;&nbsp;- `host`: Hostname/IP of the operation<br>&nbsp;&nbsp;- `rule`: Rule details (ip/action/chain/protocol/port)<br>&nbsp;&nbsp;- `save_status`: Rule save status (saved/unsaved) |
| `configure_port_forward` | Configure DNAT-based port forwarding rules (forward source port traffic to target IP:port) | - `src_port`: Source port (required, e.g., 80, integer 1-65535)<br>- `dst_ip`: Target IP (required, e.g., 10.0.0.5, IPv4 only)<br>- `dst_port`: Target port (required, e.g., 8080, integer 1-65535)<br>- `protocol`: Protocol (tcp/udp, default tcp)<br>- `action`: Operation type (add/remove, default add)<br>- `save`: Whether to save rules (True/False, default False)<br>- `host`: Remote hostname/IP (default localhost, omit for local operation)<br>- `ssh_port`: SSH port (default 22, used for remote operation, overrides config port) | - `success`: Operation success status (boolean)<br>- `message`: Operation result description (e.g., "Successfully added port forwarding: 80/tcp → 10.0.0.5:8080")<br>- `data`: Dictionary containing forwarding rule<br>&nbsp;&nbsp;- `host`: Hostname/IP of the operation<br>&nbsp;&nbsp;- `forward_rule`: Forwarding details (src_port/dst_ip/dst_port/protocol)<br>&nbsp;&nbsp;- `ip_forward_status`: IP forwarding function status (enabled/disabled) |
| `list_iptables_rules` | Query all firewall rules for specified table/chain (supports filter/nat/mangle/raw tables) | - `table`: Target table (filter/nat/mangle/raw, default filter)<br>- `chain`: Target chain (optional, e.g., INPUT, query all chains if omitted)<br>- `host`: Remote hostname/IP (default localhost, omit for local operation)<br>- `ssh_port`: SSH port (default 22, used for remote operation, overrides config port) | - `success`: Operation success status (boolean)<br>- `message`: Operation result description (e.g., "Successfully obtained nat table rules of 192.168.1.100, total 8 rules")<br>- `data`: Dictionary containing rule information<br>&nbsp;&nbsp;- `host`: Hostname/IP of the operation<br>&nbsp;&nbsp;- `table`: Queried table name<br>&nbsp;&nbsp;- `rule_count`: Total number of rules<br>&nbsp;&nbsp;- `rules`: Rule list (each entry includes chain/target/protocol/source/destination/details) |
| `enable_ip_forward` | Enable/disable system IP forwarding function (prerequisite for port forwarding) | - `enable`: Whether to enable (True/False, required)<br>- `persistent`: Whether to persist (True/False, default True, remains effective after reboot)<br>- `host`: Remote hostname/IP (default localhost, omit for local operation)<br>- `ssh_port`: SSH port (default 22, used for remote operation, overrides config port) | - `success`: Operation success status (boolean)<br>- `message`: Operation result description (e.g., "Successfully disabled IP forwarding function of 192.168.1.100 (non-persistent)")<br>- `data`: Dictionary containing configuration status<br>&nbsp;&nbsp;- `host`: Hostname/IP of the operation<br>&nbsp;&nbsp;- `enabled`: IP forwarding enable status (True/False)<br>&nbsp;&nbsp;- `persistent`: Persistence status (True/False) |


## 3. Tool Usage Instructions
1. **Prerequisites**:  
   The target host must meet the following requirements:  
   - Kernel supports netfilter framework (Linux 2.4+ systems support it by default), and `iptables` tool is installed (CentOS/RHEL: `yum install iptables`; Ubuntu/Debian: `apt install iptables`).  
   - Permission requirements: Local operation requires `root` or `sudo` privileges (`iptables` directly operates kernel modules, regular users have no permission); remote operation requires SSH user to configure password-free `sudo` privileges (to avoid command execution failure due to password interaction).  
   - Configuration dependency: Remote hosts need to be configured in `remote_hosts` of `IptablesConfig` in advance (including host, name, port, username, password attributes).

2. **Local Operation Process**:  
   ① Block specific IP from accessing SSH port (port 22) and save the rule:  
      ```python
      manage_ip_rule(
          ip="192.168.1.50",
          action="DROP",
          chain="INPUT",
          protocol="tcp",
          port=22,
          action_type="add",
          save=True
      )