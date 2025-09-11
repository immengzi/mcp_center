# mcp_center

## 一、介绍
mcp_center 用于构建 oe 智能助手，其目录结构如下：
```
├── client 测试用客户端
├── config 公共和私有配置文件
├── mcp_config mcp注册到框架的配置文件
├── README.en.md 英文版本说明
├── README.md 中文版本说明
├── requiremenets.txt 整体的依赖
├── run.sh 唤起mcp服务的脚本
├── servers mcp server源码所在目录
└── service mcp的.serivce文件所在目录
```

### 运行说明
1. 运行 mcp server 前，需在 mcp_center 目录下执行：
   ```
   export PYTHONPATH=$(pwd)
   ```
2. 通过 Python 唤起 mcp server 进行测试
3. 可通过 client 目录下的 client.py 对每个 mcp 工具进行测试，具体的 URL、工具名称和入参可自行调整


## 二、新增 mcp 规则
1. **创建服务源码目录**  
   在 `mcp_center/servers` 目录下新建文件夹，示例（以 top mcp 为例）：
   ```
   servers/top/
   ├── README.en.md       英文版本的 mcp 服务详情描述
   ├── README.md          中文版本的 mcp 服务详情描述
   ├── requirements.txt   仅包含私有安装依赖（避免与公共依赖冲突）
   └── src                源码目录（含 server 主入口）
       └── server.py
   ```

2. **配置文件设置**  
   在 `mcp_center/config/private` 目录下新建配置文件，示例（以 top mcp 为例）：
   ```
   config/private/top
   ├── config_loader.py   配置加载器（含公共配置和私有自定义配置）
   └── config.toml        私有自定义配置
   ```

3. **文档更新**  
   每新增一个 mcp，需在主目录的 README 中现有 mcp 板块同步新增该 mcp 的基本信息（确保端口不冲突，端口从 12100 开始）。
   每新增一个 mcp，需要在主目录中的 service 中增加.service文件用于将mcp制作成服务
   每新增一个 mcp，需要在主目录中的 mcp_config 中新建对应名称的目录并在下面创建一个config.json（用于将mcp注册到框架）
   每新增一个 mcp，需要在主目录中的 run.sh 中增加一条命令用于唤起mcp服务
4. **通用参数要求**  
   每个 mcp 的工具都需要一个 host 作为入参，用于与远端服务器通信。

5. **远程命令执行**  
   可通过 `paramiko` 实现远程命令执行。


## 三、现有的 MCP 服务

| 类别   | 详情                     |
|--------|--------------------------|
| 名称   | servers/remote_info                      |
| 目录   | mcp_center/servers/servers/remote_info   |
| 占用端口 | 12100                    |
| 简介   | 获取端点信息   |

| 类别   | 详情                     |
|--------|--------------------------|
| 名称   | servers/shell_generator                     |
| 目录   | mcp_center/servers/servers/shell_generator  |
| 占用端口 | 12101                    |
| 简介   | 生成&执行shell命令   |

| 类别   | 详情                     |
|--------|--------------------------|
| 名称   | servers/                      |
| 目录   | mcp_center/servers/servers/lscpu  |
| 占用端口 | 12202                    |
| 简介   | cpu架构等静态信息收集   |

| 类别   | 详情                     |
|--------|--------------------------|
| 名称   | servers/numa_topo                     |
| 目录   | mcp_center/servers/servers/numa_topo  |
| 占用端口 | 12203                    |
| 简介   | 查询 NUMA 硬件拓扑与系统配置   |

| 类别   | 详情                     |
|--------|--------------------------|
| 名称   | servers/numa_bind_proc                     |
| 目录   | mcp_center/servers/servers/numa_bind_proc  |
| 占用端口 | 12204                    |
| 简介   | 启动时绑定进程到指定 NUMA 节点   |

| 类别   | 详情                     |
|--------|--------------------------|
| 名称   | servers/numa_rebind_proc                     |
| 目录   | mcp_center/servers/servers/numa_rebind_proc  |
| 占用端口 | 12205                    |
| 简介   | 修改已启动进程的 NUMA 绑定   |

| 类别   | 详情                     |
|--------|--------------------------|
| 名称   | servers/numa_bind_docker                     |
| 目录   | mcp_center/servers/servers/numa_bind_docker  |
| 占用端口 | 12206                    |
| 简介   | 为 Docker 容器配置 NUMA 绑定   |

| 类别   | 详情                     |
|--------|--------------------------|
| 名称   | servers/numa_perf_compare                     |
| 目录   | mcp_center/servers/servers/numa_perf_compare  |
| 占用端口 | 12208                    |
| 简介   | 用 NUMA 绑定控制测试变量   |

| 类别   | 详情                     |
|--------|--------------------------|
| 名称   | servers/numa_diagnose                     |
| 目录   | mcp_center/servers/servers/numa_diagnose  |
| 占用端口 | 12209                     |
| 简介   | 用 NUMA 绑定定位硬件问题   |

| 类别   | 详情                     |
|--------|--------------------------|
| 名称   | servers/numastat                     |
| 目录   | mcp_center/servers/servers/numastat  |
| 占用端口 | 12210                    |
| 简介   | 查看系统整体 NUMA 内存访问状态   |

| 类别   | 详情                     |
|--------|--------------------------|
| 名称   | servers/numa_cross_node                     |
| 目录   | mcp_center/servers/servers/numa_cross_node  |
| 占用端口 | 12211                    |
| 简介   | 定位跨节点内存访问过高的进程   |

| 类别   | 详情                     |
|--------|--------------------------|
| 名称   | servers/numa_container                     |
| 目录   | mcp_center/servers/servers/numa_container  |
| 占用端口 | 12214                    |
| 简介   | 监控 Docker 容器的 NUMA 内存访问   |

| 类别   | 详情                     |
|--------|--------------------------|
| 名称   | servers/hotspot_trace                     |
| 目录   | mcp_center/servers/servers/hotspot_trace  |
| 占用端口 | 12216                    |
| 简介   | 快速定位系统 / 进程的 CPU 性能瓶颈   |

| 类别   | 详情                     |
|--------|--------------------------|
| 名称   | servers/cache_miss_audit                     |
| 目录   | mcp_center/servers/servers/cache_miss_audit  |
| 占用端口 | 12217                    |
| 简介   | 定位 CPU 缓存失效导致的性能损耗   |

| 类别   | 详情                     |
|--------|--------------------------|
| 名称   | servers/func_timing_trace                     |
| 目录   | mcp_center/servers/servers/func_timing_trace  |
| 占用端口 | 12218                    |
| 简介   | 精准测量函数执行时间（含调用栈）   |

| 类别   | 详情                     |
|--------|--------------------------|
| 名称   | servers/strace_syscall                     |
| 目录   | mcp_center/servers/servers/strace_syscall  |
| 占用端口 | 12219                    |
| 简介   | 排查不合理的系统调用（高频 / 耗时）  |

| 类别   | 详情                     |
|--------|--------------------------|
| 名称   | servers/perf_interrupt                     |
| 目录   | mcp_center/servers/servers/perf_interrupt  |
| 占用端口 | 12220                    |
| 简介   | 定位高频中断导致的 CPU 占用   |

| 类别   | 详情                     |
|--------|--------------------------|
| 名称   | servers/flame_graph                     |
| 目录   | mcp_center/servers/servers/flame_graph  |
| 占用端口 | 12222                    |
| 简介   | 火焰图生成：可视化展示性能瓶颈   |