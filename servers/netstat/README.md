# netstat 网络连接监控 MCP（管理控制程序）规范文档

## 一、服务介绍
本服务是一款基于`netstat`工具实现的网络连接监控管理控制程序（MCP），核心功能为对本地或远程服务器的**网络连接状态查询、指定端口占用检测**，支持TCP/UDP协议筛选、连接状态过滤及进程关联分析，为网络故障排查、端口冲突定位、进程占用溯源提供精准数据支持。


## 二、核心工具信息

| 工具名称 | 工具功能 | 核心输入参数 | 关键返回内容 |
| ---- | ---- | ---- | ---- |
| `query_network_connections` | 通过`netstat`查询本地/远程主机的网络连接列表（支持TCP/UDP筛选、TCP状态过滤） | - `proto`：协议类型（tcp/udp/all，默认all）<br>- `state`：连接状态（仅TCP有效，如ESTABLISHED/LISTENING，默认不筛选）<br>- `host`：远程主机名/IP（默认localhost，本地操作可不填）<br>- `port`：SSH端口（默认22，远程操作时使用，覆盖配置端口） | - `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（如"成功获取本地TCP连接，共12条"）<br>- `data`：包含连接数据的字典<br>&nbsp;&nbsp;- `host`：操作的主机名/IP<br>&nbsp;&nbsp;- `connection_count`：符合条件的连接总数<br>&nbsp;&nbsp;- `connections`：连接列表（每条含protocol/recv_queue/local_ip/local_port/foreign_ip/foreign_port/state/pid/program字段）<br>&nbsp;&nbsp;- `filter`：筛选条件（proto/state） |
| `check_port_occupation` | 通过`netstat`检测本地/远程主机指定端口的占用情况（含进程关联信息） | - `port`：端口号（必填，需为1-65535的整数，如80、443）<br>- `proto`：协议类型（tcp/udp，默认tcp）<br>- `host`：远程主机名/IP（默认localhost，本地操作可不填）<br>- `ssh_port`：SSH端口（默认22，远程操作时使用，覆盖配置端口） | - `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（如"远程主机192.168.1.100的端口80/TCP被占用：nginx"）<br>- `data`：包含端口占用数据的字典<br>&nbsp;&nbsp;- `host`：操作的主机名/IP<br>&nbsp;&nbsp;- `check_port`：检测的端口号<br>&nbsp;&nbsp;- `proto`：检测的协议<br>&nbsp;&nbsp;- `is_occupied`：端口是否被占用（布尔值）<br>&nbsp;&nbsp;- `occupations`：占用列表（每条含protocol/local_ip/pid/program/state字段） |


## 三、工具使用说明
1. **前置依赖**：  
   目标主机需安装`netstat`工具（通常随`net-tools`包预装，缺失时可通过`yum install net-tools`或`apt install net-tools`安装），且运行用户具备执行权限（本地可能需要`sudo`，远程需SSH用户有相关权限）。

2. **本地操作流程**：  
   ① 调用`query_network_connections`，可指定`proto`（如tcp）和`state`（如LISTENING）筛选目标连接；  
   ② 若需检测特定端口，调用`check_port_occupation`，传入`port`（如80）和`proto`（如tcp）即可获取占用信息。

3. **远程操作流程**：  
   ① 确保远程主机已配置在`NetstatConfig`的`remote_hosts`中（包含host、name、port、username、password属性）；  
   ② 调用`query_network_connections`，传入`host`（如192.168.1.100）及筛选参数，获取远程连接列表；  
   ③ 调用`check_port_occupation`，传入`host`、`port`（如443），检测远程端口占用情况；  
   ④ 若远程SSH端口非默认22，需补充`port`（`query_network_connections`）或`ssh_port`（`check_port_occupation`）参数。


## 四、注意事项
- **协议与状态匹配**：`state`参数仅对`proto=tcp`有效，UDP协议无连接状态，筛选时需避免无效组合。
- **端口参数校验**：`port`需为1-65535的整数，非数字或超出范围会直接返回参数错误。
- **配置依赖**：远程操作需确保`NetstatConfig`中已正确配置目标主机的认证信息（username、password不可缺失），否则会提示"未找到远程主机认证配置"。
- **权限影响**：若返回"permission denied"或进程信息为"-"，需确保执行用户有`netstat -p`（查看进程）的权限（本地可加`sudo`，远程需使用root或具备sudo权限的SSH用户）。
- **命令兼容性**：部分系统（如Alpine）可能需用`ss`命令替代`netstat`，此时需先安装`net-tools`包，否则会导致命令执行失败。