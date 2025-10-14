# iftop 网络流量监控 MCP（管理控制程序）规范文档

## 一、服务介绍
本服务是一款基于`iftop`工具实现的网络流量监控管理控制程序（MCP），核心功能为对本地或远程服务器的指定网络网卡进行**实时流量采集、连接分析**等操作，支持查看总流量统计和Top连接信息，为网络故障排查、带宽占用分析提供直观的数据支持。


## 二、核心工具信息

| 工具名称 | 工具功能 | 核心输入参数 | 关键返回内容 |
| ---- | ---- | ---- | ---- |
| `get_interface_traffic` | 通过`iftop`获取指定网卡的实时流量数据（含总流量和Top连接） | - `iface`：网络网卡名称（如eth0，必填）<br>- `sample_seconds`：采样时长（秒，默认5秒，3-30范围）<br>- `host`：远程主机名/IP（默认localhost，本地操作可不填）<br>- `port`：SSH端口（默认22，远程操作时使用）<br>- `username`：SSH用户名（默认root，远程操作时需指定）<br>- `password`：SSH密码（远程操作时必填） | - `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（如"成功获取网卡流量数据"）<br>- `data`：包含流量信息的字典<br>&nbsp;&nbsp;- `host`：操作的主机名/IP<br>&nbsp;&nbsp;- `total_stats`：总流量统计<br>&nbsp;&nbsp;&nbsp;&nbsp;- `interface`：网卡名称<br>&nbsp;&nbsp;&nbsp;&nbsp;- `tx_total`/`rx_total`：总发送/接收流量（MB）<br>&nbsp;&nbsp;&nbsp;&nbsp;- `tx_rate_avg`/`rx_rate_avg`：平均发送/接收速率（Mbps）<br>&nbsp;&nbsp;- `top_connections`：Top 10连接列表（按接收速率排序） |
| `list_network_interfaces` | 获取本地或远程主机的所有网络网卡名称（用于选择监控目标） | - `host`：远程主机名/IP（默认localhost，本地操作可不填）<br>- `port`/`username`/`password`：同`get_interface_traffic` | - `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（如"成功获取3个网卡名称"）<br>- `data`：包含网卡列表的字典<br>&nbsp;&nbsp;- `host`：操作的主机名/IP<br>&nbsp;&nbsp;- `interfaces`：网卡名称列表（如["eth0", "lo"]） |


## 三、工具使用说明
1. **前置依赖**：  
   目标主机需安装`iftop`工具（可通过`yum install iftop`或`apt install iftop`安装），且运行用户具备执行权限（本地可能需要`sudo`，远程需SSH用户有相关权限）。

2. **本地操作流程**：  
   ① 调用`list_network_interfaces`获取本机所有网卡名称（如eth0、ens33）；  
   ② 调用`get_interface_traffic`，指定`iface`参数（步骤①获取的网卡名）和采样时长，即可获取该网卡的实时流量数据。

3. **远程操作流程**：  
   ① 确保远程主机已配置在`IftopConfig`的`remote_hosts`中（包含host、name、port等属性）；  
   ② 调用`list_network_interfaces`，传入`host`、`username`、`password`获取远程网卡列表；  
   ③ 调用`get_interface_traffic`，传入远程主机信息和目标网卡名，获取流量数据。


## 四、注意事项
- **采样时长限制**：`sample_seconds`需设置为3-30秒（过短可能导致数据不准确，过长会增加等待时间）。
- **网卡名称校验**：`iface`参数必须是目标主机上实际存在的网卡名称（可通过`list_network_interfaces`查询确认），否则会返回错误。
- **权限问题**：若提示"permission denied"，需确保执行用户有`iftop`执行权限（本地可加`sudo`，远程需使用有权限的SSH用户）。
- **输出解析兼容**：`iftop`的输出格式可能因版本略有差异，若出现解析异常，建议升级`iftop`到最新稳定版本。
- **网络环境影响**：远程操作的采样结果可能受网络延迟影响，建议在稳定网络环境中使用。