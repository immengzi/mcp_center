# ethtool Network Interface Configuration & Monitoring MCP (Management Control Program) Specification Document

## 1. Service Introduction
This service is a network interface advanced management control program (MCP) implemented based on the `ethtool` tool. Its core functions include **querying network interface hardware information, detecting feature support, and configuring speed/duplex mode** for local or remote servers. It can obtain low-level data such as network card driver version, firmware information, and link status, and supports modifying network interface speed and duplex mode, providing professional-level data support for network performance tuning and hardware fault diagnosis.


## 2. Core Tool Information

| Tool Name | Tool Function | Core Input Parameters | Key Return Content |
| ---- | ---- | ---- | ---- |
| `get_interface_details` | Query basic hardware information (driver, firmware, speed, etc.) of specified interface | - `iface`: Interface name (required, e.g., eth0, ens33)<br>- `host`: Remote hostname/IP (default localhost, omit for local operation)<br>- `port`: SSH port (default 22, used for remote operation, overrides config port) | - `success`: Whether the operation succeeded (boolean)<br>- `message`: Operation result description (e.g., "Successfully obtained detailed information of local interface eth0")<br>- `data`: Dictionary containing interface information<br>&nbsp;&nbsp;- `host`: Hostname/IP of the operation<br>&nbsp;&nbsp;- `interface`: Interface name<br>&nbsp;&nbsp;- `basic_info`: Basic information (driver/version/firmware_version/speed/duplex/link_detected etc.) |
| `get_interface_features` | Query feature support (network protocol features, speed modes, etc.) of specified interface | - `iface`: Interface name (required, e.g., eth0, ens33)<br>- `host`: Remote hostname/IP (default localhost, omit for local operation)<br>- `port`: SSH port (default 22, used for remote operation, overrides config port) | - `success`: Whether the operation succeeded (boolean)<br>- `message`: Operation result description (e.g., "Successfully obtained feature information of local interface eth0")<br>- `data`: Dictionary containing feature information<br>&nbsp;&nbsp;- `host`: Hostname/IP of the operation<br>&nbsp;&nbsp;- `interface`: Interface name<br>&nbsp;&nbsp;- `features`: Feature lists (supported/advertised/speed_duplex) |
| `set_interface_speed` | Set speed and duplex mode of specified interface (requires admin privileges) | - `iface`: Interface name (required, e.g., eth0, ens33)<br>- `speed`: Speed (Mbps, required, e.g., 10/100/1000)<br>- `duplex`: Duplex mode (required, full/half)<br>- `host`: Remote hostname/IP (default localhost, omit for local operation)<br>- `port`: SSH port (default 22, used for remote operation, overrides config port) | - `success`: Whether the operation succeeded (boolean)<br>- `message`: Operation result description (e.g., "Successfully set eth0 to 1000Mbps full duplex")<br>- `data`: Dictionary containing configuration result<br>&nbsp;&nbsp;- `host`: Hostname/IP of the operation<br>&nbsp;&nbsp;- `interface`: Interface name<br>&nbsp;&nbsp;- `configured`: Configuration information (speed/duplex) |


## 3. Tool Usage Instructions
1. **Prerequisites**:  
   The target host must have the `ethtool` tool installed (via `yum install ethtool` or `apt install ethtool`). Among them:  
   - Query operations (`get_interface_details`/`get_interface_features`) can be executed by ordinary users;  
   - Configuration operations (`set_interface_speed`) require administrator privileges (local operation needs `sudo`, remote SSH user needs sudo privileges).

2. **Local Operation Process**:  
   ① View basic interface information: Call `get_interface_details(iface="eth0")` to get driver, speed and other information;  
   ② Check supported features of the interface: Call `get_interface_features(iface="eth0")` to view supported speed modes and protocol features;  
   ③ Adjust interface speed and duplex: Call `set_interface_speed(iface="eth0", speed=1000, duplex="full")` (requires administrator privileges).

3. **Remote Operation Process**:  
   ① Ensure the remote host is configured in `remote_hosts` of `EthtoolConfig` (including host, name, port, username, password attributes);  
   ② Call the target tool (e.g., `get_interface_details`) and pass `host=192.168.1.100` and `iface` parameter;  
   ③ If the remote SSH port is not the default 22, add the `port=2222` parameter; when performing configuration operations, ensure the remote user has sudo privileges.


## 4. Notes
- **Permission Restriction**: `set_interface_speed` must be executed with administrator privileges; otherwise, a "permission denied" error will be returned (add `sudo` before the command locally, and configure NOPASSWD sudo privileges for the remote SSH user).
- **Speed Compatibility**: The `speed` parameter must be a speed supported by the network card (check via the `speed_duplex` field of `get_interface_features`). Setting an unsupported speed will cause configuration failure.
- **Link Status Dependence**: If `link_detected` is `False` (link not connected), speed and duplex mode settings may not take effect. It is recommended to check the physical connection first.
- **Persistent Configuration**: `ethtool` configurations will be lost after a reboot. To make them permanent, write them to the system network configuration file (e.g., `/etc/sysconfig/network-scripts/ifcfg-eth0`).
- **Remote Configuration Dependence**: Remote operations require the target host's authentication information (username, password) to be configured in `EthtoolConfig`; otherwise, the prompt "Authentication config for remote host not found" will appear.