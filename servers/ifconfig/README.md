# ifconfig 网络接口信息监控 MCP（管理控制程序）规范文档

## 一、服务介绍
本服务是一款基于`ifconfig`工具实现的网络接口信息监控管理控制程序（MCP），核心功能为对本地或远程服务器的**网络接口详细信息查询、指定网卡IP地址提取**，支持获取网卡状态、MAC地址、IPv4/IPv6地址、子网掩码、MTU值及收发流量统计等关键信息，为网络配置验证、接口故障排查提供基础数据支持。


## 二、核心工具信息

| 工具名称 | 工具功能 | 核心输入参数 | 关键返回内容 |
| ---- | ---- | ---- | ---- |
| `get_network_interfaces` | 查询本地/远程主机的网络接口详细信息（支持指定单网卡或返回所有网卡） | - `iface`：网卡名称（可选，如eth0，不填则返回所有网卡）<br>- `host`：远程主机名/IP（默认localhost，本地操作可不填）<br>- `port`：SSH端口（默认22，远程操作时使用，覆盖配置端口） | - `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（如"成功获取本地所有网卡信息，共3个"）<br>- `data`：包含网卡信息的字典<br>&nbsp;&nbsp;- `host`：操作的主机名/IP<br>&nbsp;&nbsp;- `interface_count`：网卡总数<br>&nbsp;&nbsp;- `interfaces`：网卡列表（每条含name/status/mac_address/ipv4/ipv6/mtu/statistics等字段）<br>&nbsp;&nbsp;- `filter`：筛选条件（iface） |
| `get_interface_ip` | 查询本地/远程主机指定网卡的IP地址信息（专注于IPv4/IPv6地址提取） | - `iface`：网卡名称（必填，如eth0、ens33）<br>- `host`：远程主机名/IP（默认localhost，本地操作可不填）<br>- `port`：SSH端口（默认22，远程操作时使用，覆盖配置端口） | - `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（如"成功获取eth0的IP地址信息"）<br>- `data`：包含IP信息的字典<br>&nbsp;&nbsp;- `host`：操作的主机名/IP<br>&nbsp;&nbsp;- `interface`：网卡名称<br>&nbsp;&nbsp;- `ipv4`：IPv4地址信息（address/subnet_mask/broadcast）<br>&nbsp;&nbsp;- `ipv6`：IPv6地址信息（address） |


## 三、工具使用说明
1. **前置依赖**：  
   目标主机需安装`ifconfig`工具（通常随`net-tools`包预装，缺失时可通过`yum install net-tools`或`apt install net-tools`安装），且运行用户具备执行权限（本地普通用户即可查询，远程需SSH用户有相关权限）。

2. **本地操作流程**：  
   ① 若需查看所有网卡详细信息：直接调用`get_network_interfaces()`；  
   ② 若需查看特定网卡（如eth0）信息：调用`get_network_interfaces(iface="eth0")`；  
   ③ 若仅需获取网卡IP地址：调用`get_interface_ip(iface="eth0")`，专注返回IPv4/IPv6相关信息。

3. **远程操作流程**：  
   ① 确保远程主机已配置在`IfconfigConfig`的`remote_hosts`中（包含host、name、port、username、password属性）；  
   ② 调用目标工具（如`get_network_interfaces`），传入`host=192.168.1.100`及可选参数；  
   ③ 若远程SSH端口非默认22，需补充`port=2222`参数。


## 四、注意事项
- **网卡名称准确性**：`iface`参数需与目标主机实际网卡名称一致（可通过`get_network_interfaces`无参调用获取所有网卡名称），否则会返回"未找到网卡信息"。
- **命令兼容性**：部分新系统（如CentOS 8+/Ubuntu 20+）默认使用`ip`命令替代`ifconfig`，此时需先安装`net-tools`包，否则会提示"command not found"。
- **权限影响**：普通用户可能无法查看部分高级统计信息，但基础的IP地址、状态等信息仍可正常获取。
- **IPv6支持**：若主机未配置IPv6，`ipv6.address`字段会返回空值，属于正常情况。
- **远程配置依赖**：远程操作需确保`IfconfigConfig`中已配置目标主机的认证信息（username、password不可缺失），否则会提示"未找到远程主机认证配置"。