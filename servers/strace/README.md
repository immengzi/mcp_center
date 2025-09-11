# strace 进程跟踪工具集 MCP（管理控制程序）规范文档

## 一、服务介绍
本服务是一套基于 `strace` 命令的进程跟踪工具集，提供全方位的进程行为分析能力，支持本地及远程服务器的进程监控。通过跟踪系统调用，可精准捕获进程的文件操作、权限问题、网络交互及卡顿原因，为开发调试、性能优化和故障排查提供底层数据支持。

## 二、核心工具信息

| 工具名称 | 工具功能 | 核心输入参数 | 关键返回内容 |
|---------|---------|------------|------------|
| `strace_track_file_process` | 跟踪进程的文件操作和运行状态（如打开、读取、写入文件等） | - `pid`：目标进程PID（必填）<br>- `host`：远程主机IP/hostname（本地跟踪可不填）<br>- `port`：SSH端口（默认22）<br>- `username`/`password`：远程跟踪时必填<br>- `output_file`：日志路径（可选）<br>- `follow_children`：是否跟踪子进程（默认False）<br>- `duration`：跟踪时长（秒，可选） | - `success`：跟踪启动状态<br>- `message`：结果描述<br>- `strace_pid`：跟踪进程ID<br>- `output_file`：日志路径<br>- `target_pid`/`host`：目标进程及主机信息 |
| `strace_check_permission_file` | 排查进程的"权限不足"和"文件找不到"错误 | - `pid`：目标进程PID（必填）<br>- 远程参数（`host`/`port`/`username`/`password`）<br>- `output_file`：日志路径（可选）<br>- `duration`：跟踪时长（默认30秒） | - 基础状态信息（`success`/`message`等）<br>- `errors`：错误统计字典，包含：<br>&nbsp;&nbsp;- 权限不足错误详情<br>&nbsp;&nbsp;- 文件找不到错误详情 |
| `strace_check_network` | 诊断进程网络问题（连接失败、超时、DNS解析等） | - `pid`：目标进程PID（必填）<br>- 远程参数（同上）<br>- `output_file`：日志路径（可选）<br>- `duration`：跟踪时长（默认30秒）<br>- `trace_dns`：是否跟踪DNS调用（默认True） | - 基础状态信息<br>- `errors`：网络错误统计，包含：<br>&nbsp;&nbsp;- 连接被拒绝、超时等错误<br>&nbsp;&nbsp;- DNS解析失败详情（若启用） |
| `strace_locate_freeze` | 定位进程卡顿原因（IO阻塞、锁等待等慢操作） | - `pid`：目标进程PID（必填）<br>- 远程参数（同上）<br>- `output_file`：日志路径（可选）<br>- `duration`：跟踪时长（默认30秒）<br>- `slow_threshold`：慢操作阈值（默认0.5秒） | - 基础状态信息<br>- `analysis`：卡顿分析字典，包含：<br>&nbsp;&nbsp;- 慢操作调用详情<br>&nbsp;&nbsp;- 阻塞类型分类统计<br>&nbsp;&nbsp;- 耗时最长的系统调用 |

## 三、工具使用说明
1. **本地/远程切换**：
   - 本地跟踪：不填写 `host`、`username`、`password` 参数
   - 远程跟踪：必须提供完整的远程连接信息（`host`、`username`、`password`）

2. **跟踪控制**：
   - 时长控制：通过 `duration` 指定跟踪秒数，不填则持续跟踪直至手动终止
   - 日志输出：`output_file` 可选，默认生成包含PID和时间戳的日志文件
   - 子进程跟踪：仅 `strace_track_file_process` 支持 `follow_children` 参数

3. **专项场景**：
   - 文件操作审计：使用 `strace_track_file_process`
   - 权限/文件错误：使用 `strace_check_permission_file`
   - 网络问题诊断：使用 `strace_check_network`
   - 性能卡顿分析：使用 `strace_locate_freeze`

## 四、注意事项
1. **权限要求**：
   - 需具备目标进程的跟踪权限（通常需要root权限）
   - 远程主机需安装 `strace` 工具并开放SSH访问

2. **系统影响**：
   - `strace` 会增加目标进程的CPU开销（约5-10%），生产环境建议短时间跟踪
   - 高频率系统调用的进程可能生成大量日志，需注意磁盘空间

3. **安全限制**：
   - 部分安全加固的进程（如 `Dumpable: 0`）无法被跟踪
   - 内核参数 `kernel.yama.ptrace_scope` 可能限制非root用户的跟踪能力

4. **结果解读**：
   - 错误统计基于系统调用返回码（如EACCES对应权限不足）
   - 慢操作判断依据系统调用耗时是否超过 `slow_threshold`