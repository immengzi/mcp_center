# mcp_center

## 1. Introduction
mcp_center is used to build the oe intelligent assistant, and its directory structure is as follows:
```
├── client - Test client
├── config - Public and private configuration files
├── mcp_config - Configuration files for mcp registration to the framework
├── README.en.md - English version Introduction
├── README.md - Chinese version Introduction
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

| Category | Details                     |
|----------|-----------------------------|
| Name     | servers/free                |
| Directory| mcp_center/servers/free     |
| Port Used| 13100                       |
| Introduction | Obtain the overall status of system memory |

| Category | Details                     |
|----------|-----------------------------|
| Name     | servers/vmstat              |
| Directory| mcp_center/servers/vmstat   |
| Port Used| 13101                       |
| Introduction | Collect information on system resource interaction bottlenecks |

| Category | Details                     |
|----------|-----------------------------|
| Name     | servers/sar                 |
| Directory| mcp_center/servers/sar      |
| Port Used| 13102                       |
| Introduction | System resource monitoring and fault diagnosis |

| Category | Details                     |
|----------|-----------------------------|
| Name     | servers/sync                |
| Directory| mcp_center/servers/sync     |
| Port Used| 13103                       |
| Introduction | Write memory buffer data to disk |

| Category | Details                     |
|----------|-----------------------------|
| Name     | servers/swapon              |
| Directory| mcp_center/servers/swapon   |
| Port Used| 13104                       |
| Introduction | Check the status of swap devices |

| Category | Details                     |
|----------|-----------------------------|
| Name     | servers/swapoff             |
| Directory| mcp_center/servers/swapoff  |
| Port Used| 13105                       |
| Introduction | Disable swap devices    |

| Category | Details                     |
|----------|-----------------------------|
| Name     | servers/fallocate           |
| Directory| mcp_center/servers/fallocate|
| Port Used| 13106                       |
| Introduction | Temporarily create and enable swap files |

| Category | Details                     |
|----------|-----------------------------|
| Name     | servers/find                |
| Directory| mcp_center/servers/find     |
| Port Used| 13107                       |
| Introduction | File Search             |

| Category | Details                     |
|----------|-----------------------------|
| Name     | servers/touch               |
| Directory| mcp_center/servers/touch    |
| Port Used| 13108                       |
| Introduction | File Creation and Time Calibration |

| Category | Details                     |
|----------|-----------------------------|
| Name     | servers/mkdir               |
| Directory| mcp_center/servers/mkdir    |
| Port Used| 13109                       |
| Introduction | Directory Creation      |

| Category | Details                     |
|----------|-----------------------------|
| Name     | servers/rm                  |
| Directory| mcp_center/servers/rm       |
| Port Used| 13110                       |
| Introduction | File Deletion           |

| Category | Details                     |
|----------|-----------------------------|
| Name     | servers/mv                  |
| Directory| mcp_center/servers/mv       |
| Port Used| 13111                       |
| Introduction | File move or rename     |

| Category | Details                     |
|----------|-----------------------------|
| Name     | servers/ls                  |
| Directory| mcp_center/servers/ls       |
| Port Used| 13112                       |
| Introduction | View directory contents |