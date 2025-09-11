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
| 名称   | servers/free                      |
| 目录   | mcp_center/servers/free   |
| 占用端口 | 13100                    |
| 简介   | 获取系统内存整体状态   |

| 类别   | 详情                     |
|--------|--------------------------|
| 名称   | servers/vmstat                     |
| 目录   | mcp_center/servers/vmstat   |
| 占用端口 | 13101                    |
| 简介   | 系统资源交互瓶颈信息采集   |

| 类别   | 详情                     |
|--------|--------------------------|
| 名称   | servers/sar                      |
| 目录   | mcp_center/servers/sar   |
| 占用端口 | 13102                    |
| 简介   | ​​系统资源监控与故障诊断   |

| 类别   | 详情                     |
|--------|--------------------------|
| 名称   | servers/sync                     |
| 目录   | mcp_center/servers/sync   |
| 占用端口 | 13103                    |
| 简介   | 内存缓冲区数据写入磁盘   |

| 类别   | 详情                     |
|--------|--------------------------|
| 名称   | servers/swapon                      |
| 目录   | mcp_center/servers/swapon   |
| 占用端口 | 13104                    |
| 简介   | 查看swap设备状态   |

| 类别   | 详情                     |
|--------|--------------------------|
| 名称   | servers/swapoff                     |
| 目录   | mcp_center/servers/swapoff   |
| 占用端口 | 13105                    |
| 简介   | swap设备停用   |

| 类别   | 详情                     |
|--------|--------------------------|
| 名称   | servers/fallocate                      |
| 目录   | mcp_center/servers/fallocate   |
| 占用端口 | 13106                    |
| 简介   | 临时创建并启用swap文件   |

| 类别   | 详情                     |
|--------|--------------------------|
| 名称   | servers/find                     |
| 目录   | mcp_center/servers/find   |
| 占用端口 | 13107                    |
| 简介   | 文件查找   |

| 类别   | 详情                     |
|--------|--------------------------|
| 名称   | servers/touch                      |
| 目录   | mcp_center/servers/touch   |
| 占用端口 | 13108                    |
| 简介   | 文件创建与时间校准   |

| 类别   | 详情                     |
|--------|--------------------------|
| 名称   | servers/mkdir                     |
| 目录   | mcp_center/servers/mkdir   |
| 占用端口 | 13109                    |
| 简介   | 文件夹创建   |

| 类别   | 详情                     |
|--------|--------------------------|
| 名称   | servers/rm                      |
| 目录   | mcp_center/servers/rm   |
| 占用端口 | 13110                    |
| 简介   | 文件删除   |

| 类别   | 详情                     |
|--------|--------------------------|
| 名称   | servers/mv                     |
| 目录   | mcp_center/servers/mv   |
| 占用端口 | 13111                    |
| 简介   | 文件移动或重命名   |

| 类别   | 详情                     |
|--------|--------------------------|
| 名称   | servers/ls                      |
| 目录   | mcp_center/servers/ls   |
| 占用端口 | 13112                    |
| 简介   | 查看目录内容   |
