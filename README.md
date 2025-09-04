# mcp_center

## 一、介绍
mcp_center 用于构建 oe 智能助手，其目录结构如下：
```
├── client
├── config
├── mcp_config
├── README.en.md
├── README.md
├── requiremenets.txt
├── run.sh
├── servers
└── service
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
4. **通用参数要求**  
   每个 mcp 的工具都需要一个 host 作为入参，用于与远端服务器通信。

5. **远程命令执行**  
   可通过 `paramiko` 实现远程命令执行。


## 三、现有的 MCP 服务

| 类别   | 详情                     |
|--------|--------------------------|
| 名称   | top                      |
| 目录   | mcp_center/servers/top   |
| 占用端口 | 12100                    |
| 简介   | 通过 top 获取进程信息    |