# NVIDIA GPU 监控工具集 MCP 规范文档

## 一、服务介绍
本工具集是基于 `nvidia-smi` 构建的 GPU 监控 MCP（管理控制程序），提供两种核心工具满足不同场景需求：
- 结构化数据查询：输出机器可解析的 GPU 指标（如利用率、显存等）
- 原生表格查询：输出与终端 `nvidia-smi` 完全一致的原始表格，保留人类可读格式

支持本地及远程服务器查询，为 GPU 资源管理、性能调优和故障排查提供灵活的监控能力。

## 二、核心工具信息

| 工具名称              | 工具功能                                  | 核心输入参数                                                                 | 关键返回内容                                                                                     |
|-----------------------|-------------------------------------------|------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------|
| `nvidia_smi_status`   | 输出结构化 GPU 状态数据（JSON 友好）      | - `host`：远程主机 IP/hostname（本地可不填）<br>- `port`：SSH 端口（默认 22）<br>- `username`/`password`：远程查询必填<br>- `gpu_index`：指定 GPU 索引（可选）<br>- `include_processes`：是否包含进程信息（默认 False） | - `success`：查询成功与否<br>- `message`：结果描述<br>- `data`：结构化数据，包含：<br>&nbsp;&nbsp;- `host`：主机地址<br>&nbsp;&nbsp;- `gpus`：GPU 列表（含索引、型号、利用率、显存等） |
| `nvidia_smi_raw_table`| 输出 `nvidia-smi` 原生表格（保留原始格式） | - `host`：远程主机 IP/hostname（本地可不填）<br>- `port`：SSH 端口（默认 22）<br>- `username`/`password`：远程查询必填 | - `success`：查询成功与否<br>- `message`：结果描述<br>- `data`：原始表格数据，包含：<br>&nbsp;&nbsp;- `host`：主机地址<br>&nbsp;&nbsp;- `raw_table`：`nvidia-smi` 原生表格字符串（含换行和格式） |

## 三、工具使用说明
### 1. 本地/远程切换
- **本地查询**：不填写 `host`、`username`、`password` 参数，直接调用工具。
- **远程查询**：必须提供 `host`、`username`、`password`，`port` 可选（默认 22）。

### 2. 工具选择指南
| 场景需求                     | 推荐工具                | 示例调用                                                                 |
|------------------------------|-------------------------|--------------------------------------------------------------------------|
| 程序解析 GPU 指标（如监控系统） | `nvidia_smi_status`     | `nvidia_smi_status(gpu_index=0, include_processes=True)`                 |
| 直观查看 GPU 状态（类终端体验） | `nvidia_smi_raw_table`  | `nvidia_smi_raw_table(host="192.168.1.10", username="admin", password="xxx")` |

### 3. 关键参数说明
- `gpu_index`（仅 `nvidia_smi_status`）：指定单个 GPU 索引（0-based），不填则返回所有 GPU。
- `include_processes`（仅 `nvidia_smi_status`）：设为 `True` 时返回占用 GPU 的进程详情（PID、名称、占用显存）。
- `raw_table`（仅 `nvidia_smi_raw_table`）：包含与终端 `nvidia-smi` 完全一致的输出，保留表格边框、换行和原始格式。

## 四、注意事项
1. **环境依赖**：
   - 本地/远程主机必须安装 NVIDIA 显卡驱动及 `nvidia-smi` 工具（通常随驱动自动安装）。
   - 远程查询需确保目标主机开放 SSH 端口，且用户有执行 `nvidia-smi` 的权限。

2. **权限要求**：
   - 查看进程信息可能需要 root 权限（非 root 用户仅能看到自身进程）。
   - 部分 GPU 指标（如功耗）可能因显卡型号或驱动版本不同而无法获取。

3. **输出差异**：
   - `nvidia_smi_status` 的结构化数据中，显存单位为 MB，温度单位为摄氏度，利用率为百分比。
   - `nvidia_smi_raw_table` 的输出格式完全依赖 `nvidia-smi` 版本，不同版本可能存在细微差异（如字段顺序、单位显示）。