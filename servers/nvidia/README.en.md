# NVIDIA GPU Monitoring Toolset MCP Specification Document

## 1. Service Introduction
This toolset is a GPU monitoring MCP (Management Control Program) built on `nvidia-smi`, providing two core tools for different scenarios:
- Structured data query: Outputs machine-parsable GPU metrics (e.g., utilization, memory)
- Raw table query: Outputs the exact same raw table as the terminal `nvidia-smi`, preserving human-readable format

Supports local and remote server queries, offering flexible monitoring capabilities for GPU resource management, performance tuning, and troubleshooting.

## 2. Core Tool Information

| Tool Name             | Function                                      | Core Input Parameters                                                              | Key Return Content                                                                                |
|-----------------------|-----------------------------------------------|-----------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------|
| `nvidia_smi_status`   | Outputs structured GPU status data (JSON-friendly) | - `host`: Remote host IP/hostname (optional for local)<br>- `port`: SSH port (default 22)<br>- `username`/`password`: Required for remote<br>- `gpu_index`: Specific GPU index (optional)<br>- `include_processes`: Include process info (default False) | - `success`: Query success status<br>- `message`: Result description<br>- `data`: Structured data including:<br>&nbsp;&nbsp;- `host`: Host address<br>&nbsp;&nbsp;- `gpus`: List of GPUs (with index, model, utilization, memory, etc.) |
| `nvidia_smi_raw_table`| Outputs `nvidia-smi` raw table (original format) | - `host`: Remote host IP/hostname (optional for local)<br>- `port`: SSH port (default 22)<br>- `username`/`password`: Required for remote | - `success`: Query success status<br>- `message`: Result description<br>- `data`: Raw table data including:<br>&nbsp;&nbsp;- `host`: Host address<br>&nbsp;&nbsp;- `raw_table`: `nvidia-smi` raw table string (with line breaks and format) |

## 3. Tool Usage Instructions
### 1. Local/Remote Switching
- **Local query**: Call the tool directly without filling `host`, `username`, `password`.
- **Remote query**: Must provide `host`, `username`, `password`; `port` is optional (default 22).

### 2. Tool Selection Guide
| Scenario Requirement                          | Recommended Tool         | Example Call                                                                   |
|------------------------------------------------|--------------------------|--------------------------------------------------------------------------------|
| Program parsing of GPU metrics (e.g., monitoring systems) | `nvidia_smi_status`      | `nvidia_smi_status(gpu_index=0, include_processes=True)`                      |
| Intuitive GPU status check (terminal-like experience)    | `nvidia_smi_raw_table`   | `nvidia_smi_raw_table(host="192.168.1.10", username="admin", password="xxx")`  |

### 3. Key Parameter Explanations
- `gpu_index` (only `nvidia_smi_status`): Specifies a single GPU index (0-based); returns all GPUs if not set.
- `include_processes` (only `nvidia_smi_status`): Set to `True` to return details of GPU-occupying processes (PID, name, memory used).
- `raw_table` (only `nvidia_smi_raw_table`): Contains the exact same output as terminal `nvidia-smi`, preserving table borders, line breaks, and original format.

## 4. Notes
1. **Environment Dependencies**:
   - Local/remote hosts must have NVIDIA GPU drivers and `nvidia-smi` installed (usually included with drivers).
   - Remote queries require the target host to open the SSH port, and the user must have permission to execute `nvidia-smi`.

2. **Permission Requirements**:
   - Viewing process information may require root privileges (non-root users can only see their own processes).
   - Some GPU metrics (e.g., power consumption) may not be available depending on GPU model or driver version.

3. **Output Differences**:
   - In `nvidia_smi_status` structured data, memory units are MB, temperature is in Celsius, and utilization is a percentage.
   - The output format of `nvidia_smi_raw_table` depends entirely on the `nvidia-smi` version; minor differences (e.g., field order, unit display) may exist between versions.