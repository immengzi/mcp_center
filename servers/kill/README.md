# 进程控制MCP（管理控制程序）规范文档

## 一、服务介绍
本服务是一款基于`kill`命令实现进程控制的MCP（管理控制程序），核心功能为通过发送信号量对本地或远程进程进行精细化控制（暂停、恢复、信号查询等），为进程管理、故障排查提供灵活的操作手段。

## 二、核心工具信息

| 工具名称 | 工具功能 | 核心输入参数 | 关键返回内容 |
| ---- | ---- | ---- | ---- |
| `pause_process` | 通过`kill`指令发送`SIGSTOP`信号暂停进程（支持本地/远程） | - `pid`：需暂停的进程PID（正整数，必填）<br>- `host`：远程主机名/IP（默认`localhost`，本地操作可不填）<br>- `port`：SSH端口（默认22，远程操作时使用）<br>- `username`：SSH用户名（默认`root`，远程操作时需指定）<br>- `password`：SSH密码（远程操作时必填） | - `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（字符串）<br>- `data`：包含操作详情的字典<br>&nbsp;&nbsp;- `host`：操作的主机名/IP<br>&nbsp;&nbsp;- `pid`：被暂停的进程PID |
| `resume_process` | 通过`kill`指令发送`SIGCONT`信号恢复进程（支持本地/远程） | - `pid`：需恢复的进程PID（正整数，必填）<br>- `host`：远程主机名/IP（默认`localhost`，本地操作可不填）<br>- `port`：SSH端口（默认22，远程操作时使用）<br>- `username`：SSH用户名（默认`root`，远程操作时需指定）<br>- `password`：SSH密码（远程操作时必填） | - `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（字符串）<br>- `data`：包含操作详情的字典<br>&nbsp;&nbsp;- `host`：操作的主机名/IP<br>&nbsp;&nbsp;- `pid`：被恢复的进程PID |
| `get_kill_signals` | 查看本地或远程服务器的`kill`信号量含义及功能说明 | - `host`：远程主机名/IP（本地查询可不填）<br>- `port`：SSH端口（默认22，远程查询时使用）<br>- `username`：SSH用户名（远程查询时必填）<br>- `password`：SSH密码（远程查询时必填） | - `success`：查询是否成功（布尔值）<br>- `message`：查询结果描述（字符串）<br>- `data`：包含信号量信息的字典<br>&nbsp;&nbsp;- `host`：查询的主机名/IP（本地为`localhost`）<br>&nbsp;&nbsp;- `signals`：信号量列表，每个元素包含：<br>&nbsp;&nbsp;&nbsp;&nbsp;- `number`：信号编号（整数）<br>&nbsp;&nbsp;&nbsp;&nbsp;- `name`：信号名称（如`SIGTERM`）<br>&nbsp;&nbsp;&nbsp;&nbsp;- `description`：信号功能说明 |

## 三、工具使用说明
1. **本地操作**：不填写`host`、`username`、`password`参数，默认对本机进程进行操作。
2. **远程操作**：必须提供`host`、`username`、`password`参数，`port`可选（默认22）。
3. 信号量说明：`pause_process`和`resume_process`分别依赖`SIGSTOP`（暂停）和`SIGCONT`（恢复）信号，可通过`get_kill_signals`查询所有支持的信号量及其功能。

## 四、注意事项
- 操作进程需具备相应权限（本地操作可能需要`sudo`，远程操作需SSH用户有进程控制权限）。
- 暂停进程（`SIGSTOP`）会冻结进程执行，恢复后从暂停点继续运行，不会丢失数据。
- 信号量功能可能因操作系统版本存在差异，`get_kill_signals`返回结果以目标系统实际支持为准。