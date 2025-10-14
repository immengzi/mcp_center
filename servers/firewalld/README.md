# firewalld 防火墙管理 MCP（管理控制程序）规范文档

## 一、服务介绍
本服务是一款基于`firewalld`工具实现的防火墙管理控制程序（MCP），核心功能为对本地或远程服务器的**IP访问控制、端口权限配置、端口转发设置及防火墙规则查询**，支持临时/永久规则切换，可通过富规则实现精细化访问控制，为服务器安全防护、网络访问管控提供标准化操作接口。


## 二、核心工具信息

| 工具名称 | 工具功能 | 核心输入参数 | 关键返回内容 |
| ---- | ---- | ---- | ---- |
| `manage_ip_access` | 允许/拒绝特定IP/CIDR段访问（基于富规则） | - `ip`：目标IP/CIDR（必填，如192.168.1.100/24）<br>- `action`：操作类型（必填，allow/deny）<br>- `zone`：防火墙区域（默认public）<br>- `protocol`：协议（tcp/udp/all，默认all）<br>- `permanent`：是否永久生效（默认True）<br>- `host`：远程主机名/IP（默认localhost）<br>- `port`：SSH端口（默认22） | - `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（如"成功允许IP 192.168.1.100访问public区域"）<br>- `data`：包含配置信息的字典<br>&nbsp;&nbsp;- `host`：操作的主机名/IP<br>&nbsp;&nbsp;- `zone`：应用的区域<br>&nbsp;&nbsp;- `rule`：规则详情（ip/action/protocol） |
| `manage_port_access` | 添加/移除特定端口的访问权限 | - `port`：端口/端口范围（必填，如80、80-90）<br>- `protocol`：协议（tcp/udp，默认tcp）<br>- `action`：操作类型（必填，add/remove）<br>- `zone`：防火墙区域（默认public）<br>- `permanent`：是否永久生效（默认True）<br>- `host`：远程主机名/IP（默认localhost）<br>- `ssh_port`：SSH端口（默认22） | - `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（如"成功添加端口80/tcp访问public区域"）<br>- `data`：包含配置信息的字典<br>&nbsp;&nbsp;- `host`：操作的主机名/IP<br>&nbsp;&nbsp;- `zone`：应用的区域<br>&nbsp;&nbsp;- `rule`：规则详情（port/protocol/action） |
| `configure_port_forward` | 配置端口转发（源端口→目标IP:端口） | - `source_port`：源端口（必填，如80）<br>- `dest_ip`：目标IP（必填，如192.168.2.100）<br>- `dest_port`：目标端口（必填，如8080）<br>- `protocol`：协议（tcp/udp，默认tcp）<br>- `action`：操作类型（add/remove，默认add）<br>- `zone`：防火墙区域（默认public）<br>- `permanent`：是否永久生效（默认True）<br>- `host`：远程主机名/IP（默认localhost）<br>- `port`：SSH端口（默认22） | - `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（如"成功配置端口转发80/tcp→192.168.2.100:8080"）<br>- `data`：包含转发规则的字典<br>&nbsp;&nbsp;- `host`：操作的主机名/IP<br>&nbsp;&nbsp;- `zone`：应用的区域<br>&nbsp;&nbsp;- `forward_rule`：转发详情（source_port/dest_ip等） |
| `list_firewall_rules` | 展示指定区域/所有区域的防火墙规则 | - `zone`：目标区域（可选，不填则查所有）<br>- `host`：远程主机名/IP（默认localhost）<br>- `port`：SSH端口（默认22） | - `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（如"成功获取所有区域规则，共12条"）<br>- `data`：包含规则信息的字典<br>&nbsp;&nbsp;- `host`：操作的主机名/IP<br>&nbsp;&nbsp;- `zone`：查询的区域<br>&nbsp;&nbsp;- `rule_count`：规则总数<br>&nbsp;&nbsp;- `rules`：规则列表（按区域分组） |
| `list_firewall_zones` | 展示所有防火墙区域信息（含默认区域、关联接口） | - `host`：远程主机名/IP（默认localhost）<br>- `port`：SSH端口（默认22） | - `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（如"成功获取5个区域信息，默认区域public"）<br>- `data`：包含区域信息的字典<br>&nbsp;&nbsp;- `host`：操作的主机名/IP<br>&nbsp;&nbsp;- `zone_count`：区域总数<br>&nbsp;&nbsp;- `default_zone`：默认区域<br>&nbsp;&nbsp;- `zones`：区域列表（含名称、关联接口等） |


## 三、工具使用说明
1. **前置依赖**：  
   目标主机需安装`firewalld`服务（可通过`yum install firewalld`或`apt install firewalld`安装），且满足：  
   - 本地操作：运行用户需具备`root`或`sudo`权限（所有防火墙操作均需管理员权限）；  
   - 远程操作：SSH用户需配置`sudo`权限（建议配置NOPASSWD免密，避免交互失败），且`firewalld`服务处于运行状态（`systemctl start firewalld`）。

2. **本地操作流程**：  
   ① 允许特定IP访问：调用`manage_ip_access(ip="192.168.1.200", action="allow")`；  
   ② 开放Web端口：调用`manage_port_access(port="80-443", protocol="tcp", action="add")`；  
   ③ 配置端口转发：调用`configure_port_forward(source_port=80, dest_ip="10.0.0.5", dest_port=8080)`；  
   ④ 查看所有规则：调用`list_firewall_rules()`。

3. **远程操作流程**：  
   ① 确保远程主机已配置在`FirewalldConfig`的`remote_hosts`中（包含host、name、port、username、password属性）；  
   ② 调用目标工具（如`list_firewall_zones`），传入`host=192.168.1.100`参数；  
   ③ 若远程SSH端口非默认22，补充`port=2222`参数；执行配置操作时，确保远程用户有`sudo`权限。


## 四、注意事项
- **规则生效机制**：临时规则（`permanent=False`）即时生效，主机重启后失效；永久规则（`permanent=True`）需重载防火墙（工具自动执行`firewall-cmd --reload`）才生效，重启后保留。
- **端口转发依赖**：配置端口转发必须启用地址伪装（masquerade），工具会自动为目标区域添加该规则，无需手动操作。
- **权限限制**：若提示"Permission denied"，本地操作需切换`root`用户或配置`sudo`；远程操作需检查SSH用户`sudo`权限及认证信息是否正确。
- **区域选择**：`zone`参数默认使用`public`区域，生产环境建议根据网络场景划分专用区域（如`dmz`、`internal`），并关联对应的网卡接口。
- **配置冲突**：避免同时使用`firewalld`和`iptables`工具管理防火墙，可能导致规则冲突；若需切换，需先停止`firewalld`服务（`systemctl stop firewalld`）。