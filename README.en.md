# mcp_center

## 1. Introduction
mcp_center is used to build the oe intelligent assistant, with the following directory structure:
```
/mcp_center/
├── client
├── config
├── README.en.md
├── README.md
├── requiremenets.txt
└── servers
```

### Running Instructions
1. Before running the mcp server, execute the following command in the mcp_center directory:
   ```
   export PYTHONPATH=$(pwd)
   ```
2. Invoke the mcp server via Python for testing
3. You can test each mcp tool through client.py in the client directory. The specific URL, tool name, and input parameters can be adjusted as needed.


## 2. Adding New MCP Rules
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

3. **Documentation Update**  
   For each new mcp added, you need to synchronously add the basic information of the mcp in the existing mcp section of the main directory's README (ensure no port conflicts, ports start from 12100).

4. **General Parameter Requirements**  
   Each mcp tool requires a host as an input parameter for communicating with remote servers.

5. **Remote Command Execution**  
   Remote command execution can be implemented through `paramiko`.


## 3. Existing MCP Services

| Category | Details                  |
|----------|--------------------------|
| Name     | top                      |
| Directory| mcp_center/servers/top   |
| Port     | 12100                    |
| Introduction | Obtain process information through top |