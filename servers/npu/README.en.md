# NPU-SMI Management Control Program (MCP) Specification Document

## 1. Service Introduction
This service is an NPU (Neural Processing Unit) management control program (MCP) implemented based on the `npu-smi` tool. Its core functions include **status monitoring, power control, and device reset** for NPU devices on local or remote servers. It provides professional tool support for hardware resource management, performance tuning, and troubleshooting in AI training/inference tasks.


## 2. Core Tool Information

| Tool Name | Tool Function | Core Input Parameters | Key Return Content |
| ---- | ---- | ---- | ---- |
| `get_npu_status` | Get NPU device status information via `npu-smi` (supports single/all devices) | - `npu_id`: Specific NPU device ID (optional, queries all devices by default)<br>- `host`: Remote hostname/IP (default `localhost`, omit for local operation)<br>- `port`: SSH port (default 22, used for remote operation)<br>- `username`: SSH username (default `root`, required for remote operation)<br>- `password`: SSH password (required for remote operation) | - `success`: Whether the operation succeeded (boolean)<br>- `message`: Operation result description (e.g., "Successfully obtained information for 2 NPU devices")<br>- `data`: Dictionary containing NPU status<br>&nbsp;&nbsp;- `host`: Hostname/IP of the operation<br>&nbsp;&nbsp;- `npus`: List of NPU devices, each containing:<br>&nbsp;&nbsp;&nbsp;&nbsp;- `Id`: Device ID (integer)<br>&nbsp;&nbsp;&nbsp;&nbsp;- `Name`: Device name<br>&nbsp;&nbsp;&nbsp;&nbsp;- `Memory-Usage`: Memory usage (including used/total)<br>&nbsp;&nbsp;&nbsp;&nbsp;- `Utilization`: Device utilization (%)<br>&nbsp;&nbsp;&nbsp;&nbsp;- `Temperature`: Temperature (°C) |
| `set_npu_power_limit` | Set power limit for NPU device via `npu-smi` (unit: watts) | - `npu_id`: NPU device ID (non-negative integer, required)<br>- `power_limit`: Power limit value (positive integer, required)<br>- `host`/`port`/`username`/`password`: Same as `get_npu_status` | - `success`: Whether the operation succeeded (boolean)<br>- `message`: Operation result description (e.g., "Power limit set to 150 watts")<br>- `data`: Dictionary containing operation details<br>&nbsp;&nbsp;- `host`: Hostname/IP of the operation<br>&nbsp;&nbsp;- `npu_id`: Target device ID<br>&nbsp;&nbsp;- `power_limit`: Set power value (watts) |
| `reset_npu_device` | Reset NPU device via `npu-smi` (for fault recovery) | - `npu_id`: NPU device ID (non-negative integer, required)<br>- `host`/`port`/`username`/`password`: Same as `get_npu_status` | - `success`: Whether the operation succeeded (boolean)<br>- `message`: Operation result description (e.g., "NPU device 3 has been successfully reset")<br>- `data`: Dictionary containing operation details<br>&nbsp;&nbsp;- `host`: Hostname/IP of the operation<br>&nbsp;&nbsp;- `npu_id`: ID of the reset device |


## 3. Tool Usage Instructions
1. **Local Operation Rules**:  
   Omit the `host`, `username`, and `password` parameters. Operations are performed on NPU devices of the local machine (`localhost` by default). Only core business parameters like `npu_id` need to be provided (`npu_id` can be omitted in `get_npu_status` to query all devices).

2. **Remote Operation Rules**:  
   The `host` (remote host IP/hostname), `username` (SSH username), and `password` (SSH password) must be provided. The `port` is optional (default 22). Ensure the remote host has the `npu-smi` tool installed and the SSH user has NPU management permissions (usually `root`).

3. **Permission Requirements**:  
   - Local operation: Must run under a user with NPU management permissions (may require `sudo`).  
   - Remote operation: The SSH user must have permission to modify NPU configurations (recommended to use `root` user).


## 4. Notes
- **Device ID Validity**: `npu_id` must be an actual NPU device ID existing on the target host (all valid IDs can be queried via `get_npu_status`). Invalid IDs will cause operation failure.
- **Power Limit Range**: The `power_limit` value must be within the power range supported by the device (different NPU models have different power limits). Values outside the range will return device error messages.
- **Reset Risk**: `reset_npu_device` will interrupt all running tasks on the NPU. Use it only when confirming tasks have stopped or can be interrupted.
- **Tool Dependency**: All operations depend on the `npu-smi` tool being installed on the target host (usually provided by the NPU driver package). Missing installation will return a "command not found" error.
- **Version Compatibility**: The command parameters of `npu-smi` may vary slightly by driver version. It is recommended to confirm the specific parameters supported by the target host via `npu-smi --help`.