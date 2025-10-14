# File Transfer MCP (Management Control Program) Specification Document

## 1. Service Introduction
This service is a file transfer MCP (Management Control Program) integrated with `curl`, `wget`, `scp`, and `sftp` tools. It supports downloading HTTP/HTTPS/FTP resources and transferring files/directories between local and remote servers. All authentication information for remote operations is uniformly read from the configuration file, providing a secure and convenient standardized operation method for cross-host file interaction.


## 2. Core Tool Information

| Tool Name | Tool Function | Core Input Parameters | Key Return Content |
| ---- | ---- | ---- | ---- |
| `http_download` | Download HTTP/HTTPS/FTP resources to local using `curl` or `wget` | - `url`: Download resource link (string, required, e.g., `https://example.com/file.zip`)<br>- `output_path`: Local save path (string, required, e.g., `/tmp/file.zip`)<br>- `tool`: Download tool (string, optional, values: `curl`/`wget`, automatically selects available tool by default) | - `success`: Whether the operation is successful (boolean)<br>- `message`: Operation result description (string, e.g., "File downloaded to /tmp/file.zip via curl")<br>- `data`: Dictionary containing operation details<br>&nbsp;&nbsp;- `url`: Actual download link<br>&nbsp;&nbsp;- `output_path`: Local save path<br>&nbsp;&nbsp;- `file_size`: Downloaded file size (integer, unit: bytes)<br>&nbsp;&nbsp;- `transfer_time`: Transfer duration (float, unit: seconds) |
| `scp_transfer` | Transfer files/directories between local and remote via `scp` protocol | - `src`: Source path (string, required, local path e.g., `/data/docs`, remote path e.g., `192.168.1.100:/remote/docs`)<br>- `dst`: Destination path (string, required, same format as `src`)<br>- `host`: Remote hostname/IP (string, required, must match host info in configuration file)<br>- `recursive`: Whether to transfer directories recursively (boolean, optional, default `false`, set to `true` for directory transfer) | - `success`: Whether the operation is successful (boolean)<br>- `message`: Operation result description (string, e.g., "SCP transfer successful: /data/docs -> 192.168.1.100:/remote/docs")<br>- `data`: Dictionary containing operation details<br>&nbsp;&nbsp;- `src`: Source path<br>&nbsp;&nbsp;- `dst`: Destination path<br>&nbsp;&nbsp;- `file_count`: Total number of transferred files (integer)<br>&nbsp;&nbsp;- `transfer_time`: Transfer duration (float, unit: seconds) |
| `sftp_transfer` | Advanced file transfer between local and remote via `SFTP` protocol (supports auto-directory creation) | - `operation`: Operation type (string, required, values: `put`/`get`, `put`=local to remote, `get`=remote to local)<br>- `src`: Source path (string, required, matches `operation`, e.g., local path for `put`)<br>- `dst`: Destination path (string, required, matches `operation`, e.g., remote path for `put`)<br>- `host`: Remote hostname/IP (string, required, must match host info in configuration file)<br>- `create_dir`: Whether to auto-create destination directory (boolean, optional, default `true`) | - `success`: Whether the operation is successful (boolean)<br>- `message`: Operation result description (string, e.g., "SFTP put successful: /data/file.zip -> 192.168.1.100:/remote/file.zip")<br>- `data`: Dictionary containing operation details<br>&nbsp;&nbsp;- `operation`: Operation type (`put`/`get`)<br>&nbsp;&nbsp;- `src`: Source path<br>&nbsp;&nbsp;- `dst`: Destination path<br>&nbsp;&nbsp;- `file_size`: Total size of transferred files (integer, unit: bytes)<br>&nbsp;&nbsp;- `transfer_time`: Transfer duration (float, unit: seconds) |


## 3. Tool Usage Instructions
1. **Configuration File Dependence Rule**:  
   All remote operations (`scp_transfer`/`sftp_transfer`) need to maintain remote host information (`host`/`port`/`username`/`password`) in the configuration file first. When calling the tool, only the `host` parameter needs to be passed to automatically match the authentication information, without repeatedly passing the username/password.
2. **Local Operation Scenario**:  
   Only `http_download` supports pure local operations (no `host` parameter required); if `scp_transfer`/`sftp_transfer` need local transfer (path copy within the same host), `host="localhost"` still needs to be passed (the configuration file needs to maintain local host information).
3. **Tool Selection Logic**:  
   When the `tool` parameter of `http_download` is not specified, the service will first check if `curl` is available; if not, it will use `wget`; if neither is installed, it will return an error message "curl or wget is not installed".
4. **Path Format Specification**:  
   - Local path: Absolute path (e.g., `/tmp/downloads/`), directory path must end with `/`;  
   - Remote path: `host:path` format (e.g., `192.168.1.100:/remote/data/`), only `scp_transfer` supports `username@host:path` format (must be consistent with the username in the configuration file).


## 4. Notes
- **Permission Requirements**:  
  The local path must have read and write permissions (adjustable via `chmod 755 path`); the remote path must ensure that the SSH user in the configuration file has operation permissions (authorize via remote execution of `chown username:groupname path`).
- **Transfer Security**:  
  The `scp`/`sftp` protocol is based on SSH encrypted transmission, which can ensure data security; if `http_download` uses the HTTP protocol (non-HTTPS), attention should be paid to the security of the resource source to avoid downloading malicious files.
- **Large File Handling**:  
  When transferring a single large file (e.g., over 1GB), it is recommended to use `sftp_transfer` (supports basic resume capability); `scp_transfer` is suitable for batch transfer of small files, and `http_download` needs to ensure network stability (re-download is required after interruption).
- **Error Troubleshooting Suggestions**:  
  - If remote connection fails, first confirm network connectivity via `ping host`, then check if `port`/`username`/`password` in the configuration file are correct;  
  - If the transfer prompts "file does not exist", verify whether the source path exists (use `ls path` for local path, `ssh host ls path` for remote path);  
  - If a permission error occurs, first check whether the user of the path is consistent with the SSH user in the configuration file; if not, adjust the path permissions or replace the SSH user.