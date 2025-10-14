# lsof 文件与网络监控 MCP（管理控制程序）规范文档

## 一、服务介绍
本服务是一款基于`lsof`（List Open Files）工具实现的多维度监控管理控制程序（MCP），核心功能为对本地或远程服务器的**打开文件列表查询、网络连接（套接字）分析、文件关联进程定位**，支持按用户、端口、协议筛选，可快速排查文件占用冲突、网络连接异常及进程资源占用问题，为系统运维与故障定位提供全面数据支撑。


## 二、核心工具信息

| 工具名称 | 工具功能 | 核心输入参数 | 关键返回内容 |
| ---- | ---- | ---- | ---- |
| `list_open_files` | 查询本地/远程主机的打开文件列表（支持按文件路径、用户筛选） | - `path`：文件路径（可选，指定后仅显示该文件的打开情况）<br>- `user`：用户名（可选，筛选指定用户打开的文件）<br>- `host`：远程主机名/IP（默认localhost，本地操作可不填）<br>- `port`：SSH端口（默认22，远程操作时使用，覆盖配置端口） | - `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（如"成功获取本地打开文件，共28个"）<br>- `data`：包含文件信息的字典<br>&nbsp;&nbsp;- `host`：操作的主机名/IP<br>&nbsp;&nbsp;- `file_count`：打开的文件总数<br>&nbsp;&nbsp;- `files`：文件列表（每条含command/pid/user/fd/type/file_path等字段）<br>&nbsp;&nbsp;- `filter`：筛选条件（path/user） |
| `list_network_files` | 查询本地/远程主机的网络连接相关文件（网络套接字，支持按协议、端口筛选） | - `proto`：协议类型（tcp/udp/all，默认all）<br>- `port`：端口号（可选，筛选指定端口的网络连接）<br>- `host`：远程主机名/IP（默认localhost，本地操作可不填）<br>- `ssh_port`：SSH端口（默认22，远程操作时使用，覆盖配置端口） | - `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（如"成功获取192.168.1.100的TCP网络连接，共15条"）<br>- `data`：包含网络连接信息的字典<br>&nbsp;&nbsp;- `host`：操作的主机名/IP<br>&nbsp;&nbsp;- `connection_count`：网络连接总数<br>&nbsp;&nbsp;- `connections`：连接列表（每条含command/pid/user/local_address/foreign_address/state等字段）<br>&nbsp;&nbsp;- `filter`：筛选条件（proto/port） |
| `find_process_by_file` | 查找本地/远程主机中打开指定文件的进程（精准定位文件占用进程） | - `path`：文件路径（必填，如/tmp/test.log、/var/log/nginx/access.log）<br>- `host`：远程主机名/IP（默认localhost，本地操作可不填）<br>- `port`：SSH端口（默认22，远程操作时使用，覆盖配置端口） | - `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（如"找到2个在本地打开/tmp/test.log的进程"）<br>- `data`：包含进程信息的字典<br>&nbsp;&nbsp;- `host`：操作的主机名/IP<br>&nbsp;&nbsp;- `file_path`：目标文件路径<br>&nbsp;&nbsp;- `process_count`：相关进程总数<br>&nbsp;&nbsp;- `processes`：进程列表（每条含command/pid/user/fd等字段） |


## 三、工具使用说明
1. **前置依赖**：  
   目标主机需安装`lsof`工具（可通过`yum install lsof`或`apt install lsof`安装），且运行用户具备执行权限（本地普通用户可查询自身打开的文件，查询所有用户或系统级文件需`sudo`；远程需SSH用户有对应权限）。

2. **本地操作流程**：  
   ① 若需查看所有打开文件：直接调用`list_open_files`，可补充`user=root`筛选root用户的文件；  
   ② 若需排查网络连接：调用`list_network_files`，指定`proto=tcp`和`port=80`筛选80端口的TCP连接；  
   ③ 若需定位文件占用进程：调用`find_process_by_file`，传入`path=/tmp/locked.txt`即可找到占用该文件的进程。

3. **远程操作流程**：  
   ① 确保远程主机已配置在`LsofConfig`的`remote_hosts`中（包含host、name、port、username、password属性）；  
   ② 调用目标工具（如`list_network_files`），传入`host=192.168.1.100`及筛选参数；  
   ③ 若远程SSH端口非默认22，需补充`port=2222`（`list_open_files`/`find_process_by_file`）或`ssh_port=2222`（`list_network_files`）参数。


## 四、注意事项
- **文件路径格式**：`path`参数需传入完整路径（如/var/log/syslog，而非相对路径log/syslog），路径含空格时无需手动转义，工具内部已处理。
- **端口参数限制**：`port`需为1-65535的整数，非数字或超出范围会直接返回参数错误。
- **权限影响**：若返回结果缺失部分进程或文件，需确认执行用户权限（本地加`sudo`、远程使用root用户SSH登录可获取完整数据）。
- **远程配置依赖**：远程操作需确保`LsofConfig`中已配置目标主机的认证信息（username、password不可缺失），否则会提示"未找到远程主机认证配置"。
- **性能提示**：在文件/进程数量极多的主机上执行`list_open_files`（无筛选条件）可能耗时较长，建议补充`path`或`user`筛选条件减少查询范围。