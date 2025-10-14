# iptables 防火墙管理 MCP（管理控制程序）规范文档

## 一、服务介绍
本服务是一款基于`iptables`（Linux内核级防火墙工具）实现的底层网络安全管理控制程序（MCP），核心功能为对本地或远程服务器的**IP访问控制规则管理、端口转发配置、IP转发功能开关及防火墙规则查询**。作为直接操作netfilter内核模块的工具，`iptables`支持精细的数据包过滤逻辑与复杂NAT（网络地址转换）配置，适用于需要自定义链、高级路由规则的场景，为服务器安全防护、流量管控及故障定位提供底层技术支撑。


## 二、核心工具信息

| 工具名称 | 工具功能 | 核心输入参数 | 关键返回内容 |
| ---- | ---- | ---- | ---- |
| `manage_ip_rule` | 添加/删除IP访问控制规则（允许/拒绝特定IP的TCP/UDP/全协议流量） | - `ip`：目标IP/CIDR（必填，如192.168.1.100/24）<br>- `action`：动作（必填，ACCEPT/DROP/REJECT）<br>- `chain`：规则链（INPUT/OUTPUT/FORWARD，默认INPUT）<br>- `protocol`：协议（tcp/udp/all，默认all）<br>- `port`：端口号（可选，如80，仅tcp/udp协议有效）<br>- `action_type`：操作类型（add/delete，默认add）<br>- `save`：是否保存规则（True/False，默认False，保存后重启不丢失）<br>- `host`：远程主机名/IP（默认localhost，本地操作可不填）<br>- `port`：SSH端口（默认22，远程操作时使用，覆盖配置端口） | - `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（如"成功添加规则：ACCEPT来自192.168.1.0/24的tcp流量（端口80），已保存"）<br>- `data`：包含规则信息的字典<br>&nbsp;&nbsp;- `host`：操作的主机名/IP<br>&nbsp;&nbsp;- `rule`：规则详情（ip/action/chain/protocol/port）<br>&nbsp;&nbsp;- `save_status`：规则保存状态（saved/unsaved） |
| `configure_port_forward` | 配置基于DNAT的端口转发规则（将源端口流量转发到目标IP:端口） | - `src_port`：源端口（必填，如80，1-65535整数）<br>- `dst_ip`：目标IP（必填，如10.0.0.5，仅支持IPv4）<br>- `dst_port`：目标端口（必填，如8080，1-65535整数）<br>- `protocol`：协议（tcp/udp，默认tcp）<br>- `action`：操作类型（add/remove，默认add）<br>- `save`：是否保存规则（True/False，默认False）<br>- `host`：远程主机名/IP（默认localhost，本地操作可不填）<br>- `ssh_port`：SSH端口（默认22，远程操作时使用，覆盖配置端口） | - `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（如"成功添加端口转发：80/tcp → 10.0.0.5:8080"）<br>- `data`：包含转发规则的字典<br>&nbsp;&nbsp;- `host`：操作的主机名/IP<br>&nbsp;&nbsp;- `forward_rule`：转发详情（src_port/dst_ip/dst_port/protocol）<br>&nbsp;&nbsp;- `ip_forward_status`：IP转发功能状态（enabled/disabled） |
| `list_iptables_rules` | 查询指定表/链的所有防火墙规则（支持filter/nat/mangle/raw表） | - `table`：目标表（filter/nat/mangle/raw，默认filter）<br>- `chain`：目标链（可选，如INPUT，不填则查询所有链）<br>- `host`：远程主机名/IP（默认localhost，本地操作可不填）<br>- `ssh_port`：SSH端口（默认22，远程操作时使用，覆盖配置端口） | - `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（如"成功获取192.168.1.100的nat表规则，共8条"）<br>- `data`：包含规则信息的字典<br>&nbsp;&nbsp;- `host`：操作的主机名/IP<br>&nbsp;&nbsp;- `table`：查询的表名<br>&nbsp;&nbsp;- `rule_count`：规则总数<br>&nbsp;&nbsp;- `rules`：规则列表（每条含chain/target/protocol/source/destination/details） |
| `enable_ip_forward` | 启用/禁用系统IP转发功能（端口转发的前置依赖） | - `enable`：是否启用（True/False，必填）<br>- `persistent`：是否持久化（True/False，默认True，重启后仍生效）<br>- `host`：远程主机名/IP（默认localhost，本地操作可不填）<br>- `ssh_port`：SSH端口（默认22，远程操作时使用，覆盖配置端口） | - `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（如"成功禁用192.168.1.100的IP转发功能（非持久化）"）<br>- `data`：包含配置状态的字典<br>&nbsp;&nbsp;- `host`：操作的主机名/IP<br>&nbsp;&nbsp;- `enabled`：IP转发启用状态（True/False）<br>&nbsp;&nbsp;- `persistent`：持久化状态（True/False） |


## 三、工具使用说明
1. **前置依赖**：  
   目标主机需满足以下条件：  
   - 内核支持netfilter框架（Linux 2.4+系统默认支持），且已安装`iptables`工具（CentOS/RHEL：`yum install iptables`；Ubuntu/Debian：`apt install iptables`）。  
   - 权限要求：本地操作需`root`或`sudo`权限（`iptables`直接操作内核模块，普通用户无权限）；远程操作需SSH用户配置`sudo`免密权限（避免密码交互导致命令执行失败）。  
   - 配置依赖：远程主机需提前在`IptablesConfig`的`remote_hosts`中配置（含host、name、port、username、password属性）。

2. **本地操作流程**：  
   ① 禁止特定IP访问SSH端口（22端口）并保存规则：  
      ```python
      manage_ip_rule(
          ip="192.168.1.50",
          action="DROP",
          chain="INPUT",
          protocol="tcp",
          port=22,
          action_type="add",
          save=True
      )
      ```  
   ② 配置80端口TCP流量转发到内部服务器10.0.0.5:8080：  
      ```python
      configure_port_forward(
          src_port=80,
          dst_ip="10.0.0.5",
          dst_port=8080,
          protocol="tcp",
          action="add",
          save=True
      )
      ```  
   ③ 查看filter表所有链的规则：  
      ```python
      list_iptables_rules(table="filter")
      ```  
   ④ 启用IP转发并持久化配置：  
      ```python
      enable_ip_forward(enable=True, persistent=True)
      ```

3. **远程操作流程**：  
   ① 示例：查询远程主机192.168.1.100的nat表规则（SSH端口2222）：  
      ```python
      list_iptables_rules(
          table="nat",
          host="192.168.1.100",
          ssh_port=2222
      )
      ```  
   ② 示例：删除远程主机192.168.1.100的80端口转发规则：  
      ```python
      configure_port_forward(
          src_port=80,
          dst_ip="10.0.0.5",
          dst_port=8080,
          protocol="tcp",
          action="remove",
          host="192.168.1.100",
          ssh_port=22
      )
      ```


## 四、注意事项
- **规则持久化机制**：`iptables`规则默认临时生效（主机重启后丢失），需通过`save=True`参数保存到配置文件（CentOS/RHEL：`/etc/sysconfig/iptables`；Ubuntu/Debian：`/etc/iptables/rules.v4`），工具会自动执行`iptables-save`命令完成保存。  
- **链与表的对应关系**：不同功能的规则需在指定表中配置——过滤流量用`filter`表、地址转换用`nat`表、数据包修改用`mangle`表，错放表会导致规则不生效（如NAT规则放filter表无效）。  
- **IP转发的依赖性**：配置端口转发前必须启用IP转发（`enable_ip_forward(enable=True)`），否则转发规则仅存在于配置中但不实际生效；工具配置转发时会自动临时启用IP转发，建议通过`persistent=True`持久化避免重启失效。  
- **与firewalld的冲突**：`iptables`和`firewalld`不能同时运行（二者均操作netfilter模块），若系统已安装firewalld，需先停止并禁用（`systemctl stop firewalld && systemctl disable firewalld`），否则规则会被firewalld覆盖或清除。  
- **规则顺序影响**：`iptables`按规则添加顺序匹配数据包，靠前的规则优先生效（如先配置的“DROP 192.168.1.50”会阻止后续“ACCEPT 192.168.1.0/24”对该IP的放行），添加规则时需按“精确规则优先、拒绝规则靠前”的原则排序。  
- **端口参数限制**：`port`需为1-65535的整数，传入非数字或超出范围的值会直接返回参数错误；如需配置端口范围（如80-90），需多次调用工具或手动拼接规则（工具暂不支持直接输入端口范围）。