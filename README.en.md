# mcp_center

## 1. Introduction
mcp_center is used to build the oe intelligent assistant, and its directory structure is as follows:
```
├── client - Test client
├── config - Public and private configuration files
├── mcp_config - Configuration files for mcp registration to the framework
├── README.en.md - English version description
├── README.md - Chinese version description
├── requiremenets.txt - Overall dependencies
├── run.sh - Script to start the mcp service
├── servers - Directory containing mcp server source code
└── service - Directory containing .service files for mcp
```

### Running Instructions
1. Before running the mcp server, execute the following command in the mcp_center directory:
   ```
   export PYTHONPATH=$(pwd)
   ```
2. Start the mcp server through Python for testing
3. You can test each mcp tool through client.py in the client directory. The specific URL, tool name, and input parameters can be adjusted as needed.


## 2. Rules for Adding New mcp
1. **Create Service Source Code Directory**  
   Create a new folder under the `mcp_center/servers` directory. Example (taking top mcp as an example):
   ```
   servers/top/
   ├── README.en.md       English version of mcp service details
   ├── README.md          Chinese version of mcp service details
   ├── requirements.txt   Contains only private installation dependencies (to avoid conflicts with public dependencies)
   └── src                Source code directory (including server main entry)
       └── server.py
   ```

2. **Configuration File Settings**  
   Create a new configuration file under the `mcp_center/config/private` directory. Example (taking top mcp as an example):
   ```
   config/private/top
   ├── config_loader.py   Configuration loader (including public configuration and private custom configuration)
   └── config.toml        Private custom configuration
   ```

3. **Document Updates**  
   For each new mcp added, you need to synchronously add the basic information of the mcp to the existing mcp section in the main directory's README (ensure that ports do not conflict, starting from 12100).
   For each new mcp added, you need to add a .service file in the service directory of the main directory to make the mcp a service.
   For each new mcp added, you need to create a corresponding directory in mcp_config of the main directory and create a config.json under it (for registering the mcp to the framework).
   For each new mcp added, you need to add a command in run.sh of the main directory to start the mcp service.

4. **General Parameter Requirements**  
   Each mcp tool requires a host as an input parameter for communication with the remote server.

5. **Remote Command Execution**  
   Remote command execution can be implemented through `paramiko`.


## 3. Existing MCP Services

| Category | Details                     |
|----------|-----------------------------|
| Name     | servers/remote_info         |
| Directory| mcp_center/servers/servers/remote_info |
| Port Used| 12100                       |
| Introduction | Obtain endpoint information |

| Category | Details                     |
|----------|-----------------------------|
| Name     | servers/shell_generator     |
| Directory| mcp_center/servers/servers/shell_generator |
| Port Used| 12101                       |
| Introduction | Generate & execute shell commands |

| Category | Details |
|----------|--------------------------|
| Name | servers/ |
| Directory | mcp_center/servers/servers/lscpu |
| Port Occupied | 12202 |
| Description | Collects static information such as CPU architecture |

| Category | Details |
|----------|--------------------------|
| Name | servers/numa_topo |
| Directory | mcp_center/servers/servers/numa_topo |
| Port Occupied | 12203 |
| Description | Queries NUMA hardware topology and system configuration |

| Category | Details |
|----------|--------------------------|
| Name | servers/numa_bind_proc |
| Directory | mcp_center/servers/servers/numa_bind_proc |
| Port Occupied | 12204 |
| Description | Binds processes to specified NUMA nodes at startup |

| Category | Details |
|----------|--------------------------|
| Name | servers/numa_rebind_proc |
| Directory | mcp_center/servers/servers/numa_rebind_proc |
| Port Occupied | 12205 |
| Description | Modifies NUMA bindings of already started processes |

| Category | Details |
|----------|--------------------------|
| Name | servers/numa_bind_docker |
| Directory | mcp_center/servers/servers/numa_bind_docker |
| Port Occupied | 12206 |
| Description | Configure NUMA binding for Docker containers |

| Category | Details |
|----------|--------------------------|
| Name | servers/numa_perf_compare |
| Directory | mcp_center/servers/servers/numa_perf_compare |
| Port Occupied | 12208 |
| Description | Control test variables with NUMA binding |

| Category | Details |
|----------|--------------------------|
| Name | servers/numa_diagnose |
| Directory | mcp_center/servers/servers/numa_diagnose |
| Port Occupied | 12209 |
| Description | Locate hardware issues with NUMA binding |

| Category | Details |
|----------|--------------------------|
| Name | servers/numastat |
| Directory | mcp_center/servers/servers/numastat |
| Port Occupied | 12210 |
| Description | View the overall NUMA memory access status of the system |

| Category | Details |
|----------|--------------------------|
| Name | servers/numa_cross_node |
| Directory | mcp_center/servers/servers/numa_cross_node |
| Port Occupied | 12211 |
| Description | Identify processes with excessive cross-node memory access |

| Category | Details |
|----------|--------------------------|
| Name | servers/numa_container |
| Directory | mcp_center/servers/servers/numa_container |
| Port Occupied | 12214 |
| Description | Monitor NUMA memory access in Docker containers |

| Category | Details |
|----------|--------------------------|
| Name | servers/hotspot_trace |
| Directory | mcp_center/servers/servers/hotspot_trace |
| Port Occupied | 12216 |
| Description | Quickly locate CPU performance bottlenecks in systems/processes |

| Category | Details |
|----------|--------------------------|
| Name | servers/cache_miss_audit |
| Directory | mcp_center/servers/servers/cache_miss_audit |
| Port Occupied | 12217 |
| Description | Identify performance losses due to CPU cache misses |

| Category | Details |
|----------|--------------------------|
| Name | servers/func_timing_trace |
| Directory | mcp_center/servers/servers/func_timing_trace |
| Port Occupied | 12218 |
| Description | Accurately measure function execution time (including call stack) |

| Category | Details |
|----------|--------------------------|
| Name | servers/strace_syscall |
| Directory | mcp_center/servers/servers/strace_syscall |
| Port Occupied | 12219 |
| Description | Investigate unreasonable system calls (high frequency / time-consuming) |

| Category | Details |
|----------|--------------------------|
| Name | servers/perf_interrupt |
| Directory | mcp_center/servers/servers/perf_interrupt |
| Port Occupied | 12220 |
| Description | Locate CPU usage caused by high-frequency interrupts |

| Category | Details |
|----------|--------------------------|
| Name | servers/flame_graph |
| Directory | mcp_center/servers/servers/flame_graph |
| Port Occupied | 12222 |
| Description | Flame graph generation: Visualize performance bottlenecks |