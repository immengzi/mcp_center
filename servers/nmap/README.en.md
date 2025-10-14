# Nmap Network Scan Management and Control Program (MCP) Specification Document

## 1. Service Introduction
This service is a network scan management and control program (MCP) implemented based on the encapsulation of the `nmap` tool. Its core functions include **host discovery, port detection, and service identification** for IPs/network segments on local or remote servers. It supports multi-mode scanning and custom configurations, automatically parses scan results, and outputs structured data. It provides standardized tool support for network device inventory management, port security detection, and network topology sorting, adapting to automated scanning needs in small and medium-sized enterprise networks or test environments.

## 2. Core Tool Information

| Tool Name       | Tool Function                                                                 | Core Input Parameters                                                                                                                                                                                                 | Key Return Content                                                                                                                                                                                                 |
|-----------------|-------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `scan_network`  | IP/network segment scanning for local/remote hosts (supports host discovery, port detection, service identification)                                                                 | - `target`: Scanning target (required, supports single IP, CIDR network segment, IP range, e.g., 192.168.1.1, 192.168.1.0/24, 192.168.1.1-100)<br>- `scan_type`: Scanning type (optional, basic/full/quick, default: basic; basic=100 common ports, full=all ports 1-65535, quick=10 core ports)<br>- `port_range`: Custom port range (optional, e.g., 22,80-443, takes precedence over scan_type)<br>- `host_discovery`: Whether to perform only host discovery (no port scanning, True/False, default: False)<br>- `host`: Remote host name/IP (default: localhost, not required for local operations)<br>- `ssh_port`: SSH port (default: 22, used for remote operations)<br>- `ssh_user`: SSH username (required for remote operations)<br>- `ssh_pwd`: SSH password (optional for remote operations, alternative to ssh_key)<br>- `ssh_key`: SSH private key path (optional for remote operations, takes precedence over password) | - `success`: Whether the operation is successful (boolean)<br>- `message`: Operation result description (e.g., "Successfully scanned 192.168.1.0/24, found 8 active hosts")<br>- `data`: Dictionary containing scan results<br>  - `host`: Host name/IP performing the scan<br>  - `target`: Scanning target<br>  - `scan_type`: Scanning type (including custom for custom ports)<br>  - `host_count`: Total number of discovered hosts<br>  - `up_host_count`: Number of active hosts<br>  - `results`: List of hosts, each host includes:<br>    - `ip`: Host IP<br>    - `status`: Status (up/down/unknown)<br>    - `status_details`: Status details (e.g., latency time)<br>    - `open_ports`: List of open ports (including port number, status, service name, details) |

## 3. Tool User Guide

1. **Local Operation Rules**: Do not fill in the `host`, `ssh_user`, `ssh_pwd`, and `ssh_key` parameters; scanning will be initiated from the local machine (`localhost`) by default. Only the core `target` parameter needs to be provided, and `scan_type`/`port_range`/`host_discovery` can be optionally configured according to requirements (e.g., set `host_discovery=True` for host discovery only).

2. **Remote Operation Rules**: Must provide `host` (remote host IP/hostname), `ssh_user` (SSH username), and either `ssh_pwd` or `ssh_key` (one of the two); `ssh_port` is optional (default: 22). Ensure the remote host has the `nmap` tool installed, and the SSH user has `nmap` execution permissions (root user is recommended to avoid restrictions on privileged port scanning).

3. **Permission Requirements**:  

    - Local operations: Scanning privileged ports (1-1024) requires root or sudo privileges; ordinary users can only scan ports above 1024. It is recommended to run as root or configure password-free `sudo nmap`.  

    - Remote operations: The SSH user must have access permissions to the `nmap` tool and the target network segment. If scanning a remote network segment, ensure network connectivity between the remote host and the target segment.

## 4. Notes

- **Validity of Target Format**: `target` must conform to IP (e.g., 192.168.1.1), CIDR (e.g., 192.168.1.0/24), or IP range (e.g., 192.168.1.1-100) formats. The tool will automatically verify, and invalid formats will return clear error prompts.

- **Priority of Scanning Modes**: `port_range` (custom ports) takes precedence over `scan_type` (preset modes). If both are configured, scanning will only be performed according to `port_range`.

- **Scanning Efficiency and Time Consumption**: A full port scan (`scan_type="full"`) takes approximately 1-5 minutes per IP. Large-scale network segments (e.g., /16) may take over an hour. It is recommended to first filter active hosts using `host_discovery` before performing targeted scans.

- **Network Security Compliance**: Scanning public IPs or unauthorized networks may violate the "Network Security Law" or enterprise security policies. Ensure scanning targets are self-owned or authorized devices/network segments.

- **Tool Dependencies**: All operations depend on the target host having `nmap` installed (version 7.80+). If not installed, an error "nmap: command not found" will be returned. For Linux, install via `apt/yum install nmap`; for Windows, install manually and configure environment variables.

- **Firewall Interception Risk**: Some device firewalls may block `nmap` scan packets (e.g., ICMP ping disabled, port filtering), which may result in "host down" or "port status unknown". It is necessary to open protocols required for scanning (TCP/UDP/ICMP) in advance.