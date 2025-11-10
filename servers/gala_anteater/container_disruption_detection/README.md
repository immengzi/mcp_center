# Container Disruption Detection MCP

本项目提供容器级性能异常检测与根因分析（RCA）能力，基于 **Anteater 时序引擎** 与 **MCP 工具集成框架**。

## 功能概述

- 自动检测容器运行时性能异常（支持多指标）
- 异常根因分析，基于时序相关性计算
- 自动生成诊断报告（Markdown 格式）

## 核心组件

| 模块 | 说明 |
|------|------|
| `mcp_server.py` | MCP 服务器主程序，注册检测、RCA 与报告生成工具 |
| `mcp_data.py` | 数据模型与 MetricLoader 构建逻辑 |

## 启动方式

```bash
python servers/gala-anteater/container_disruption_detection/mcp/mcp_server.py
