# 进程控制MCP（管理控制程序）规范文档

## 一、服务介绍
本服务是一款基于`kill`命令实现进程控制的MCP（管理控制程序），核心功能为通过发送信号量对本地或远程进程进行精细化控制（终止、暂停、恢复、信号查询等），所有远程操作的认证信息统一从配置文件读取，为进程管理、故障排查提供安全、灵活的标准化操作手段。


## 二、核心工具信息

| 工具名称 | 工具功能 | 核心输入参数 | 关键返回内容 |
| ---- | ---- | ---- | ---- |
| `kill_process` | 通过`kill`指令发送信号终止进程（支持本地/远程，默认SIGTERM(15)） | - `pid`：需终止的进程PID（正整数，必填）<br>- `signal`：信号量（整数，可选，常用值：9(SIGKILL)、15(SIGTERM)）<br>- `host`：远程主机名/IP（字符串，本地操作可不填，需与配置文件匹配） | - `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（字符串）<br>- `data`：包含操作详情的字典<br>&nbsp;&nbsp;- `host`：操作的主机名/IP（本地为`localhost`）<br>&nbsp;&nbsp;- `pid`：被操作的进程PID<br>&nbsp;&nbsp;- `signal`：发送的信号量编号 |
| `pause_process` | 通过`kill`指令发送`SIGSTOP`信号暂停进程（支持本地/远程） | - `pid`：需暂停的进程PID（正整数，必填）<br>- `host`：远程主机名/IP（字符串，本地操作可不填，需与配置文件匹配） | - `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（字符串）<br>- `data`：包含操作详情的字典<br>&nbsp;&nbsp;- `host`：操作的主机名/IP（本地为`localhost`）<br>&nbsp;&nbsp;- `pid`：被暂停的进程PID |
| `resume_process` | 通过`kill`指令发送`SIGCONT`信号恢复进程（支持本地/远程） | - `pid`：需恢复的进程PID（正整数，必填）<br>- `host`：远程主机名/IP（字符串，本地操作可不填，需与配置文件匹配） | - `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（字符串）<br>- `data`：包含操作详情的字典<br>&nbsp;&nbsp;- `host`：操作的主机名/IP（本地为`localhost`）<br>&nbsp;&nbsp;- `pid`：被恢复的进程PID |
| `check_process_status` | 检查本地或远程进程是否存在及名称信息 | - `pid`：需检查的进程PID（正整数，必填）<br>- `host`：远程主机名/IP（字符串，本地操作可不填，需与配置文件匹配） | - `success`：查询是否成功（布尔值）<br>- `message`：查询结果描述（字符串）<br>- `data`：包含进程状态的字典<br>&nbsp;&nbsp;- `host`：查询的主机名/IP（本地为`localhost`）<br>&nbsp;&nbsp;- `pid`：查询的进程PID<br>&nbsp;&nbsp;- `exists`：进程是否存在（布尔值）<br>&nbsp;&nbsp;- `name`：进程名称（字符串，进程不存在时为空） |
| `get_kill_signals` | 查看本地或远程服务器的`kill`信号量含义及功能说明 | - `host`：远程主机名/IP（字符串，本地查询可不填，需与配置文件匹配） | - `success`：查询是否成功（布尔值）<br>- `message`：查询结果描述（字符串）<br>- `data`：包含信号量信息的字典<br>&nbsp;&nbsp;- `host`：查询的主机名/IP（本地为`localhost`）<br>&nbsp;&nbsp;- `signals`：信号量列表，每个元素包含：<br>&nbsp;&nbsp;&nbsp;&nbsp;- `number`：信号编号（整数）<br>&nbsp;&nbsp;&nbsp;&nbsp;- `name`：信号名称（如`SIGTERM`）<br>&nbsp;&nbsp;&nbsp;&nbsp;- `description`：信号功能说明 |


## 三、工具使用说明
1. **配置文件依赖规则**：  
   所有远程操作需先在配置文件中维护远程主机信息（`host`/`port`/`username`/`password`），调用工具时仅需传入`host`参数即可自动匹配认证信息，无需重复传入用户名/密码。
2. **本地与远程操作区分**：  
   - 本地操作：不填写`host`参数，默认对本机进程执行操作；  
   - 远程操作：必须填写`host`参数（需与配置文件中主机信息一致），无需手动传入`port`/`username`/`password`。
3. **信号量使用规范**：  
   - 终止进程：默认使用`SIGTERM(15)`（优雅终止，进程可捕获并清理资源），强制终止使用`SIGKILL(9)`（不可捕获，直接终止进程）；  
   - 暂停/恢复：仅支持`SIGSTOP(19)`（暂停）和`SIGCONT(18)`（恢复），`SIGSTOP`不可被进程忽略，暂停后需用`SIGCONT`恢复；  
   - 信号详情：可通过`get_kill_signals`工具查询目标系统支持的所有信号量及功能描述。
4. **进程状态校验建议**：  
   执行`kill_process`/`pause_process`/`resume_process`前，建议先调用`check_process_status`确认进程是否存在，避免对无效PID操作导致错误。


## 四、注意事项
- **权限要求**：  
  本地操作时，若进程归属其他用户，需当前用户具备`sudo`权限；远程操作时，配置文件中SSH用户需对目标进程有`kill`及`ps`命令执行权限（可通过`ps -u 用户名`确认进程归属）。
- **信号量使用风险**：  
  - 使用`SIGKILL(9)`强制终止进程可能导致进程内存数据丢失（如未保存的文件、数据库事务），建议优先使用`SIGTERM(15)`；  
  - `SIGSTOP`仅暂停进程执行，不会释放进程占用的内存/端口资源，长时间暂停需评估系统资源占用情况。
- **系统兼容性**：  
  信号量编号及功能可能因操作系统（如Linux、Unix）存在差异，`get_kill_signals`返回结果以目标系统实际支持为准；不支持Windows系统（无`kill`命令及POSIX信号机制）。
- **错误排查建议**：  
  - 远程连接失败：先通过`ping host`确认网络连通性，再检查配置文件中`host`/`port`/`username`/`password`是否正确；  
  - 进程操作失败：若提示“Operation not permitted”，需检查用户权限；若提示“No such process”，需通过`check_process_status`确认PID是否有效；  
  - 查询信号量失败：确保目标系统支持`kill -l`命令（主流Linux/Unix系统均支持）。