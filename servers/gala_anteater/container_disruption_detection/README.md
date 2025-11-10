# README

````markdown
# Container Disruption Detection MCP

基于 **Anteater** 时序引擎与 **MCP**，提供容器级异常检测与根因分析（RCA），并输出 Markdown 诊断报告。

## 功能概述
- 多指标容器异常检测（SPOT + TS-DBSCAN 过滤）
- 根因分析（基于相关性）
- 自动生成诊断报告（Markdown）

## 目录结构
| 模块 | 说明 |
|---|---|
| `mcp_server.py` | MCP 服务器：注册检测、RCA、报告工具 |
| `mcp_data.py`   | 数据模型与 `MetricLoader` 构建 |

## 启动
```bash
python servers/gala-anteater/container_disruption_detection/mcp/mcp_server.py
````

默认监听 `0.0.0.0:12345`。

## 数据约定

* `MetricLoader` 为 Anteater 组件，需可访问你的时序数据源（如 Prometheus）。
* 机器 ID 在标签 `machine_id` 中。
* 容器名在标签 `container_name` 中。

## 工具接口

### 1) 容器异常检测

**name:** `container_disruption_detection_tool`

```python
container_disruption_detection_tool(
    kpis: List[KPIParam],
    window: WindowParam = WindowParam(),          # look_back(分钟), obs_size(观测窗口点数)
    extra: Optional[ExtraConfig] = None,          # extra_metrics: "cpu,memory,..."
    anteater_conf: Optional[dict] = None,         # AnteaterConf JSON
    metric_info: Optional[dict] = None,           # MetricInfo JSON
    machine_id: Optional[str] = None              # 可省略：不传则自动发现
) -> List[AnomalyModel]
```

* 不传 `machine_id` 时，系统会基于 `kpis[*].metric` 自动发现近 `window.look_back` 分钟内活跃的机器并逐一检测。
* `KPIParam.params` 中常用字段：

  * `outlier_ratio_th`：异常比例阈值，默认 `0.1`

### 2) 根因分析

**name:** `rca_tool`

```python
rca_tool(
    metric: str,
    victim_container_name: str,
    window: WindowParam = WindowParam(),
    anteater_conf: Optional[dict] = None,
    metric_info: Optional[dict] = None,
    machine_id: str                               # 必填
) -> List[RootCauseModel]
```

* 在指定 `machine_id` 与 `metric` 下，定位 `victim_container_name` 的时序，并在同机器的同指标下计算与其他容器的相关性，返回前 3 个可能原因。

### 3) 报告生成

**name:** `report_tool`

```python
report_tool(
    anomalies: List[AnomalyModel],
    report_type: ReportType = ReportType.anomaly   # 或 ReportType.normal
) -> Dict[str, str]  # {"markdown": "..."}
```

## 参数说明

* `WindowParam.look_back`：回溯时间（分钟），默认 `20`
* `WindowParam.obs_size`：观测窗口长度（最近 N 个点），默认 `6`
* `ExtraConfig.extra_metrics`：逗号分隔的额外指标，用于在异常信息中输出趋势（相对变动）

## 返回模型（节选）

* `AnomalyModel`：`machine_id`, `metric`, `labels`, `score`, `details`
* `RootCauseModel`：`metric`, `labels`, `score`

## 依赖

* Python ≥ 3.8
* `anteater`（gala_anteater）
* `numpy`, `pandas`, `pydantic`
* MCP 框架（`mcp.server.FastMCP`）