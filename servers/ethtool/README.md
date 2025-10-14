# ethtool 网络接口配置与监控 MCP（管理控制程序）规范文档

## 一、服务介绍
本服务是一款基于`ethtool`工具实现的网络接口深度管理控制程序（MCP），核心功能为对本地或远程服务器的**网络接口硬件信息查询、特性支持检测及速率/双工模式配置**，可获取网卡驱动版本、固件信息、链路状态等底层数据，支持修改网络接口的速率和双工模式，为网络性能调优、硬件故障诊断提供专业级数据支撑。


## 二、核心工具信息

| 工具名称 | 工具功能 | 核心输入参数 | 关键返回内容 |
| ---- | ---- | ---- | ---- |
| `get_interface_details` | 查询指定网卡的基础硬件信息（驱动、固件、速率等） | - `iface`：网卡名称（必填，如eth0、ens33）<br>- `host`：远程主机名/IP（默认localhost，本地操作可不填）<br>- `port`：SSH端口（默认22，远程操作时使用，覆盖配置端口） | - `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（如"成功获取本地网卡eth0的详细信息"）<br>- `data`：包含网卡信息的字典<br>&nbsp;&nbsp;- `host`：操作的主机名/IP<br>&nbsp;&nbsp;- `interface`：网卡名称<br>&nbsp;&nbsp;- `basic_info`：基础信息（driver/version/firmware_version/speed/duplex/link_detected等） |
| `get_interface_features` | 查询指定网卡的特性支持情况（网络协议特性、速率模式等） | - `iface`：网卡名称（必填，如eth0、ens33）<br>- `host`：远程主机名/IP（默认localhost，本地操作可不填）<br>- `port`：SSH端口（默认22，远程操作时使用，覆盖配置端口） | - `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（如"成功获取本地网卡eth0的特性信息"）<br>- `data`：包含特性信息的字典<br>&nbsp;&nbsp;- `host`：操作的主机名/IP<br>&nbsp;&nbsp;- `interface`：网卡名称<br>&nbsp;&nbsp;- `features`：特性列表（supported/advertised/speed_duplex） |
| `set_interface_speed` | 设置指定网卡的速率和双工模式（需要管理员权限） | - `iface`：网卡名称（必填，如eth0、ens33）<br>- `speed`：速率（Mbps，必填，如10/100/1000）<br>- `duplex`：双工模式（必填，full/half）<br>- `host`：远程主机名/IP（默认localhost，本地操作可不填）<br>- `port`：SSH端口（默认22，远程操作时使用，覆盖配置端口） | - `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（如"成功将eth0设置为1000Mbps全双工"）<br>- `data`：包含配置结果的字典<br>&nbsp;&nbsp;- `host`：操作的主机名/IP<br>&nbsp;&nbsp;- `interface`：网卡名称<br>&nbsp;&nbsp;- `configured`：配置信息（speed/duplex） |


## 三、工具使用说明
1. **前置依赖**：  
   目标主机需安装`ethtool`工具（可通过`yum install ethtool`或`apt install ethtool`安装）。其中：  
   - 查询类操作（`get_interface_details`/`get_interface_features`）普通用户即可执行；  
   - 配置类操作（`set_interface_speed`）需要管理员权限（本地需`sudo`，远程SSH用户需具备sudo权限）。

2. **本地操作流程**：  
   ① 查看网卡基础信息：调用`get_interface_details(iface="eth0")`获取驱动、速率等信息；  
   ② 检查网卡支持的特性：调用`get_interface_features(iface="eth0")`查看支持的速率模式和协议特性；  
   ③ 调整网卡速率和双工：调用`set_interface_speed(iface="eth0", speed=1000, duplex="full")`（需管理员权限）。

3. **远程操作流程**：  
   ① 确保远程主机已配置在`EthtoolConfig`的`remote_hosts`中（包含host、name、port、username、password属性）；  
   ② 调用目标工具（如`get_interface_details`），传入`host=192.168.1.100`及`iface`参数；  
   ③ 若远程SSH端口非默认22，补充`port=2222`参数；执行配置操作时，确保远程用户有sudo权限。


## 四、注意事项
- **权限限制**：`set_interface_speed`必须以管理员权限执行，否则会返回"权限被拒绝"错误（本地需在命令前加`sudo`，远程SSH用户需配置NOPASSWD sudo权限）。
- **速率兼容性**：`speed`参数需为网卡支持的速率（可通过`get_interface_features`的`speed_duplex`字段查询），设置不支持的速率会导致配置失败。
- **链路状态依赖**：若`link_detected`为`False`（链路未连接），速率和双工模式设置可能不生效，建议先检查物理连接。
- **持久化配置**：`ethtool`的配置在重启后会失效，如需永久生效，需写入系统网络配置文件（如`/etc/sysconfig/network-scripts/ifcfg-eth0`）。
- **远程配置依赖**：远程操作需确保`EthtoolConfig`中已配置目标主机的认证信息（username、password不可缺失），否则会提示"未找到远程主机认证配置"。