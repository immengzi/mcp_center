# Nload 带宽监控 MCP（管理控制程序）规范文档

## 一、服务介绍
本服务是一款基于`nload`工具实现的带宽监控管理控制程序（MCP），核心功能为对本地或远程服务器的指定网络网卡进行**实时带宽采集、流量分析**等操作，支持查看入站/出站流量的当前速率、平均速率、最大速率及总流量，为带宽负载评估、网络资源优化提供直观的数据支持。


## 二、核心工具信息

| 工具名称 | 工具功能 | 核心输入参数 | 关键返回内容 |
| ---- | ---- | ---- | ---- |
| `monitor_bandwidth` | 通过`nload`获取指定网卡的实时带宽数据（含入站/出站流量详情） | - `iface`：网络网卡名称（如eth0，必填）<br>- `duration`：监控时长（秒，默认10秒，5-60范围）<br>- `host`：远程主机名/IP（默认localhost，本地操作可不填）<br>- `port`：SSH端口（默认22，远程操作时使用） | - `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（如"成功获取网卡带宽数据"）<br>- `data`：包含带宽信息的字典<br>&nbsp;&nbsp;- `host`：操作的主机名/IP<br>&nbsp;&nbsp;- `monitor_duration`：实际监控时长（秒）<br>&nbsp;&nbsp;- `bandwidth`：带宽监控数据<br>&nbsp;&nbsp;&nbsp;&nbsp;- `interface`：网卡名称<br>&nbsp;&nbsp;&nbsp;&nbsp;- `incoming`：入站流量（current/average/maximum/total/unit）<br>&nbsp;&nbsp;&nbsp;&nbsp;- `outgoing`：出站流量（结构同incoming） |
| `list_network_interfaces` | 获取本地或远程主机的所有网络网卡名称（用于选择监控目标） | - `host`：远程主机名/IP（默认localhost，本地操作可不填）<br>- `port`：SSH端口（默认22，远程操作时使用） | - `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（如"成功获取3个网卡名称"）<br>- `data`：包含网卡列表的字典<br>&nbsp;&nbsp;- `host`：操作的主机名/IP<br>&nbsp;&nbsp;- `interfaces`：网卡名称列表（如["eth0", "lo"]） |


## 三、工具使用说明
1. **前置依赖**：  
   目标主机需安装`nload`工具（可通过`yum install -y nload`或`apt install -y nload`安装），且运行用户具备执行权限（本地可能需要`sudo`，远程需SSH用户有相关权限）。

2. **本地操作流程**：  
   ① 调用`list_network_interfaces`获取本机所有网卡名称（如eth0、ens33）；  
   ② 调用`monitor_bandwidth`，指定`iface`参数（步骤①获取的网卡名）和监控时长，即可获取该网卡的实时带宽数据。

3. **远程操作流程**：  
   ① 确保远程主机已配置在`NloadConfig`的`remote_hosts`中（包含host、name、port、username、password属性）；  
   ② 调用`list_network_interfaces`，传入`host`参数获取远程网卡列表；  
   ③ 调用`monitor_bandwidth`，传入`host`、`iface`及监控时长，获取远程网卡带宽数据。


## 四、注意事项
- **监控时长限制**：`duration`需设置为5-60秒（过短可能导致数据不准确，过长会增加等待时间）。
- **网卡名称校验**：`iface`参数必须是目标主机上实际存在的网卡名称（可通过`list_network_interfaces`查询确认），否则会返回错误。
- **配置依赖**：远程操作需确保`NloadConfig`中已正确配置目标主机的认证信息（username、password不可缺失），否则会提示"认证配置不完整"。
- **单位兼容性**：返回结果中速率单位统一为Mbps（Kbps自动转换），总流量单位随`nload`输出（如MB、GB）。
- **版本适配**：`nload`输出格式可能因版本略有差异，若解析异常，建议升级到最新稳定版本（`yum update nload`或`apt upgrade nload`）。