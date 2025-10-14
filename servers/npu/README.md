# NPU-SMI 管理控制程序（MCP）规范文档

## 一、服务介绍
本服务是一款基于`npu-smi`工具实现的NPU（神经网络处理器）管理控制程序（MCP），核心功能为对本地或远程服务器的NPU设备进行**状态监控、功率控制、设备重置**等操作，为AI训练/推理任务中的硬件资源管理、性能调优和故障排查提供专业工具支持。


## 二、核心工具信息

| 工具名称 | 工具功能 | 核心输入参数 | 关键返回内容 |
| ---- | ---- | ---- | ---- |
| `get_npu_status` | 通过`npu-smi`获取NPU设备状态信息（支持查询单个/所有设备） | - `npu_id`：特定NPU设备ID（可选，默认查询所有设备）<br>- `host`：远程主机名/IP（默认`localhost`，本地操作可不填）<br>- `port`：SSH端口（默认22，远程操作时使用）<br>- `username`：SSH用户名（默认`root`，远程操作时需指定）<br>- `password`：SSH密码（远程操作时必填） | - `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（如"成功获取2个NPU设备信息"）<br>- `data`：包含NPU状态的字典<br>&nbsp;&nbsp;- `host`：操作的主机名/IP<br>&nbsp;&nbsp;- `npus`：NPU设备列表，每个设备包含：<br>&nbsp;&nbsp;&nbsp;&nbsp;- `Id`：设备ID（整数）<br>&nbsp;&nbsp;&nbsp;&nbsp;- `Name`：设备名称<br>&nbsp;&nbsp;&nbsp;&nbsp;- `Memory-Usage`：内存使用（含used/total）<br>&nbsp;&nbsp;&nbsp;&nbsp;- `Utilization`：设备利用率（%）<br>&nbsp;&nbsp;&nbsp;&nbsp;- `Temperature`：温度（°C） |
| `set_npu_power_limit` | 通过`npu-smi`设置NPU设备的功率限制（单位：瓦特） | - `npu_id`：NPU设备ID（非负整数，必填）<br>- `power_limit`：功率限制值（正整数，必填）<br>- `host`/`port`/`username`/`password`：同`get_npu_status` | - `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（如"功率限制已设置为150瓦特"）<br>- `data`：包含操作详情的字典<br>&nbsp;&nbsp;- `host`：操作的主机名/IP<br>&nbsp;&nbsp;- `npu_id`：目标设备ID<br>&nbsp;&nbsp;- `power_limit`：设置的功率值（瓦特） |
| `reset_npu_device` | 通过`npu-smi`重置NPU设备（用于故障恢复） | - `npu_id`：NPU设备ID（非负整数，必填）<br>- `host`/`port`/`username`/`password`：同`get_npu_status` | - `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（如"NPU设备3已成功重置"）<br>- `data`：包含操作详情的字典<br>&nbsp;&nbsp;- `host`：操作的主机名/IP<br>&nbsp;&nbsp;- `npu_id`：被重置的设备ID |


## 三、工具使用说明
1. **本地操作规则**：  
   不填写`host`、`username`、`password`参数，默认对本机（`localhost`）的NPU设备进行操作，仅需提供`npu_id`等核心业务参数（`get_npu_status`可省略`npu_id`以查询所有设备）。

2. **远程操作规则**：  
   必须提供`host`（远程主机IP/hostname）、`username`（SSH用户名）、`password`（SSH密码），`port`可选（默认22）；需确保远程主机已安装`npu-smi`工具且SSH用户具备NPU管理权限（通常为`root`）。

3. **权限要求**：  
   - 本地操作：需运行在具有NPU管理权限的用户下（可能需要`sudo`）。  
   - 远程操作：SSH用户需对NPU设备有配置修改权限（建议使用`root`用户）。


## 四、注意事项
- **设备ID有效性**：`npu_id`需为目标主机上实际存在的NPU设备ID（可通过`get_npu_status`查询所有有效ID），无效ID会导致操作失败。
- **功率限制范围**：`power_limit`值需在设备支持的功率范围内（不同型号NPU的功率上限不同），超出范围会返回设备报错信息。
- **重置风险**：`reset_npu_device`会中断该NPU上正在运行的所有任务，请在确认任务已停止或可中断的情况下使用。
- **工具依赖性**：所有操作依赖目标主机已安装`npu-smi`工具（通常由NPU驱动包提供），未安装会返回"command not found"错误。
- **版本兼容性**：`npu-smi`的命令参数可能因驱动版本略有差异，建议通过`npu-smi --help`确认目标主机支持的具体参数。