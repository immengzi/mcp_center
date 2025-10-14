# 文件传输MCP（管理控制程序）规范文档

## 一、服务介绍
本服务是一款整合`curl`、`wget`、`scp`、`sftp`工具的文件传输MCP（管理控制程序），支持HTTP/HTTPS/FTP资源下载、本地与远程服务器间的文件/目录传输，所有远程操作的认证信息统一从配置文件读取，为跨主机文件交互提供安全、便捷的标准化操作手段。


## 二、核心工具信息

| 工具名称 | 工具功能 | 核心输入参数 | 关键返回内容 |
| ---- | ---- | ---- | ---- |
| `http_download` | 通过`curl`或`wget`工具下载HTTP/HTTPS/FTP资源至本地 | - `url`：下载资源链接（字符串，必填，如`https://example.com/file.zip`）<br>- `output_path`：本地保存路径（字符串，必填，如`/tmp/file.zip`）<br>- `tool`：下载工具（字符串，可选，值为`curl`/`wget`，默认自动选择可用工具） | - `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（字符串，如“文件已通过curl下载至/tmp/file.zip”）<br>- `data`：包含操作详情的字典<br>&nbsp;&nbsp;- `url`：实际下载链接<br>&nbsp;&nbsp;- `output_path`：本地保存路径<br>&nbsp;&nbsp;- `file_size`：下载文件大小（整数，单位：字节）<br>&nbsp;&nbsp;- `transfer_time`：传输耗时（浮点数，单位：秒） |
| `scp_transfer` | 通过`scp`协议实现本地与远程间文件/目录传输 | - `src`：源路径（字符串，必填，本地路径如`/data/docs`，远程路径如`192.168.1.100:/remote/docs`）<br>- `dst`：目标路径（字符串，必填，格式同`src`）<br>- `host`：远程主机名/IP（字符串，必填，需与配置文件中主机信息匹配）<br>- `recursive`：是否递归传输目录（布尔值，可选，默认`false`，传输目录需设为`true`） | - `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（字符串，如“SCP传输成功：/data/docs -> 192.168.1.100:/remote/docs”）<br>- `data`：包含操作详情的字典<br>&nbsp;&nbsp;- `src`：源路径<br>&nbsp;&nbsp;- `dst`：目标路径<br>&nbsp;&nbsp;- `file_count`：传输的文件总数（整数）<br>&nbsp;&nbsp;- `transfer_time`：传输耗时（浮点数，单位：秒） |
| `sftp_transfer` | 通过`SFTP`协议实现本地与远程间高级文件传输（支持自动建目录） | - `operation`：操作类型（字符串，必填，值为`put`/`get`，`put`=本地到远程，`get`=远程到本地）<br>- `src`：源路径（字符串，必填，与`operation`匹配，如`put`时为本地路径）<br>- `dst`：目标路径（字符串，必填，与`operation`匹配，如`put`时为远程路径）<br>- `host`：远程主机名/IP（字符串，必填，需与配置文件中主机信息匹配）<br>- `create_dir`：是否自动创建目标目录（布尔值，可选，默认`true`） | - `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（字符串，如“SFTPput成功：/data/file.zip -> 192.168.1.100:/remote/file.zip”）<br>- `data`：包含操作详情的字典<br>&nbsp;&nbsp;- `operation`：操作类型（`put`/`get`）<br>&nbsp;&nbsp;- `src`：源路径<br>&nbsp;&nbsp;- `dst`：目标路径<br>&nbsp;&nbsp;- `file_size`：传输文件总大小（整数，单位：字节）<br>&nbsp;&nbsp;- `transfer_time`：传输耗时（浮点数，单位：秒） |


## 三、工具使用说明
1. **配置文件依赖规则**：  
   所有远程操作（`scp_transfer`/`sftp_transfer`）需先在配置文件中维护远程主机信息（`host`/`port`/`username`/`password`），调用工具时仅需传入`host`参数即可自动匹配认证信息，无需重复传入用户名/密码。
2. **本地操作场景**：  
   仅`http_download`支持纯本地操作（无需`host`参数）；`scp_transfer`/`sftp_transfer`若需本地传输（同一主机内路径拷贝），仍需传入`host="localhost"`（配置文件需维护本机信息）。
3. **工具选择逻辑**：  
   `http_download`的`tool`参数不指定时，服务会优先检查`curl`是否可用，若不可用则使用`wget`；若两者均未安装，会返回“未安装curl或wget工具”的错误提示。
4. **路径格式规范**：  
   - 本地路径：绝对路径（如`/tmp/downloads/`），目录路径需以`/`结尾；  
   - 远程路径：`host:路径`格式（如`192.168.1.100:/remote/data/`），仅`scp_transfer`支持`username@host:路径`格式（需与配置文件用户名一致）。


## 四、注意事项
- **权限要求**：  
  本地路径需具备读写权限（可通过`chmod 755 路径`调整）；远程路径需确保配置文件中SSH用户有操作权限（可通过远程执行`chown 用户名:组名 路径`授权）。
- **传输安全性**：  
  `scp`/`sftp`协议基于SSH加密传输，可保障数据安全；`http_download`若使用HTTP协议（非HTTPS），需注意资源来源的安全性，避免下载恶意文件。
- **大文件处理**：  
  传输单个大文件（如超过1GB）时，建议使用`sftp_transfer`（支持断点续传基础能力）；`scp_transfer`适合小文件批量传输，`http_download`需确保网络稳定（中断后需重新下载）。
- **错误排查建议**：  
  - 若远程连接失败，先通过`ping host`确认网络连通性，再检查配置文件中`port`/`username`/`password`是否正确；  
  - 若传输提示“文件不存在”，需验证源路径是否存在（本地路径用`ls 路径`，远程路径用`ssh host ls 路径`）；  
  - 若权限报错，优先检查路径所属用户与配置文件中SSH用户是否一致，不一致需调整路径权限或更换SSH用户。