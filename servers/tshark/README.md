# tshark 网络数据包捕获与分析 MCP（管理控制程序）规范文档

## 一、服务介绍
本服务是一款基于`tshark`（Wireshark命令行版）工具实现的网络流量管理控制程序（MCP），核心功能为对本地或远程服务器的**指定网卡数据包实时捕获、自定义过滤抓包及网络协议分布统计**，支持按时长/包数限制抓包范围，可提取数据包的源目IP、端口、协议类型等关键信息，为网络故障定位、流量异常分析、协议合规检测提供底层数据支撑。


## 二、核心工具信息

| 工具名称 | 工具功能 | 核心输入参数 | 关键返回内容 |
| ---- | ---- | ---- | ---- |
| `capture_packets` | 捕获指定网卡的网络数据包（支持时长、包数、过滤规则限制） | - `iface`：网卡名称（必填，如eth0、ens33）<br>- `duration`：捕获时长（秒，默认10，范围3-60）<br>- `count`：最大捕获包数（可选，如100，达到即停止）<br>- `filter`：抓包过滤规则（可选，如`tcp port 80`，遵循pcap语法）<br>- `host`：远程主机名/IP（默认localhost，本地操作可不填）<br>- `port`：SSH端口（默认22，远程操作时使用，覆盖配置端口） | - `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（如"在本地网卡eth0上成功捕获58个数据包"）<br>- `data`：包含抓包数据的字典<br>&nbsp;&nbsp;- `host`：操作的主机名/IP<br>&nbsp;&nbsp;- `interface`：网卡名称<br>&nbsp;&nbsp;- `capture_params`：抓包参数（duration/count/filter）<br>&nbsp;&nbsp;- `packet_count`：实际捕获包数<br>&nbsp;&nbsp;- `packets`：数据包列表（每条含packet_id/timestamp/src_ip/dst_ip等字段） |
| `analyze_protocol_stats` | 分析指定网卡的网络协议分布（统计各协议数据包占比） | - `iface`：网卡名称（必填，如eth0、ens33）<br>- `duration`：分析时长（秒，默认10，范围3-60）<br>- `filter`：分析过滤规则（可选，如`ip`，仅统计符合条件的流量）<br>- `host`：远程主机名/IP（默认localhost，本地操作可不填）<br>- `port`：SSH端口（默认22，远程操作时使用，覆盖配置端口） | - `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（如"成功分析本地网卡eth0的协议分布，共捕获120个数据包"）<br>- `data`：包含统计数据的字典<br>&nbsp;&nbsp;- `host`：操作的主机名/IP<br>&nbsp;&nbsp;- `interface`：网卡名称<br>&nbsp;&nbsp;- `analysis_params`：分析参数（duration/filter）<br>&nbsp;&nbsp;- `stats`：协议统计信息（total_packets总包数、protocols各协议计数） |


## 三、工具使用说明
1. **前置依赖**：  
   目标主机需安装`tshark`工具（可通过`yum install wireshark-cli`或`apt install tshark`安装），且运行用户具备以下权限：  
   - 本地操作：普通用户可抓包，但部分系统需将用户加入`wireshark`用户组（执行`usermod -aG wireshark 用户名`）；  
   - 远程操作：SSH用户需具备执行`tshark`的权限，若需抓所有流量，可能需要sudo权限。

2. **本地操作流程**：  
   ① 基础抓包：调用`capture_packets(iface="eth0")`，默认在eth0网卡抓包10秒；  
   ② 限定抓包：调用`capture_packets(iface="eth0", duration=20, count=200, filter="udp port 53")`，在eth0抓20秒或200个DNS数据包（先到即停）；  
   ③ 协议分析：调用`analyze_protocol_stats(iface="eth0", duration=15)`，统计15秒内eth0网卡的所有协议分布。

3. **远程操作流程**：  
   ① 确保远程主机已配置在`TsharkConfig`的`remote_hosts`中（包含host、name、port、username、password属性）；  
   ② 调用目标工具（如`capture_packets`），传入`host=192.168.1.100`及`iface`等参数；  
   ③ 若远程SSH端口非默认22，补充`port=2222`参数；若远程抓包需sudo，需在`TsharkConfig`中配置具备sudo权限的用户。


## 四、注意事项
- **抓包过滤规则**：`filter`参数需遵循pcap过滤语法（如`tcp`仅抓TCP包、`src host 192.168.1.5`仅抓源IP为192.168.1.5的包），语法错误会导致抓包失败。
- **权限限制**：若本地抓包提示"Permission denied"，需将用户加入`wireshark`组并重新登录；远程抓包失败时，检查SSH用户是否有`tshark`执行权限。
- **性能影响**：长时间或无过滤抓包可能占用较高CPU/内存，建议在生产环境使用时限定`duration`和`filter`，避免影响业务。
- **数据量控制**：`count`参数建议设置合理值（如1000以内），过多数据包会导致返回结果体积过大，影响传输效率。
- **远程配置依赖**：远程操作需确保`TsharkConfig`中已配置目标主机的完整认证信息（username、password不可缺失），否则会提示"未找到远程主机认证配置"。