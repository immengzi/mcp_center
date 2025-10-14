# Docker MCP 工具使用说明

# Docker 容器管理 MCP（管理控制程序）规范文档

## 一、服务介绍

本服务是一款基于 Docker CLI 封装实现的容器全生命周期管理控制程序（MCP），核心功能为对本地或远程服务器的**容器创建/启停/删除、镜像拉取/推送/标签管理、数据卷与网络配置、容器日志查询与命令交互**，支持按容器名称、镜像版本、端口映射等维度筛选，可快速实现容器化应用的部署运维与故障定位，为 DevOps 流程与系统运维提供标准化工具支撑。

## 二、核心工具信息

|工具名称|工具功能|核心输入参数|关键返回内容|
|---|---|---|---|
|`manage_container`|本地/远程主机容器全生命周期管理（创建/启动/停止/删除/重启，支持端口、数据卷配置）|- `name`：容器名称（必填，唯一标识容器）<br>- `image`：镜像名称（创建时必填，如nginx:latest）<br>- `action`：操作类型（create/start/stop/delete/restart，必填）<br>- `ports`：端口映射（可选，格式"8080:80,443:443"）<br>- `volumes`：数据卷挂载（可选，格式"/host/path:/container/path:ro"）<br>- `restart_policy`：重启策略（no/always/on-failure/unless-stopped，默认no）<br>- `host`：远程主机名/IP（默认[localhost](http://localhost)）<br>- `ssh_port`：SSH端口（默认22，远程操作时使用）|- `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（如"容器my-nginx start成功"）<br>- `data`：包含容器操作信息的字典<br>  - `host`：操作的主机名/IP<br>  - `container_name`：容器名称<br>  - `action`：执行的操作类型<br>  - `details`：操作详情（如容器ID、配置参数）|
|`manage_image`|本地/远程主机镜像管理（拉取/删除/标签/推送，支持私有仓库认证）|- `image`：镜像名称（必填，如nginx:latest、[registry.com/app:v1](http://registry.com/app:v1)）<br>- `action`：操作类型（pull/delete/tag/push/inspect，必填）<br>- `new_tag`：新标签（tag操作必填，格式"my-app:v1"）<br>- `registry_auth`：仓库认证（可选，格式"username:password"，私有仓库用）<br>- `host`：远程主机名/IP（默认[localhost](http://localhost)）<br>- `ssh_port`：SSH端口（默认22，远程操作时使用）|- `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（如"镜像nginx:latest pull成功"）<br>- `data`：包含镜像信息的字典<br>  - `host`：操作的主机名/IP<br>  - `image`：镜像名称<br>  - `action`：执行的操作类型<br>  - `inspect`：镜像详情（inspect操作返回，含架构、配置等）|
|`container_data_operate`|本地/远程主机容器数据交互（容器导入/导出、容器与本地文件拷贝）|- `name`：容器名称（必填，import时为镜像前缀）<br>- `action`：操作类型（export/import/cp，必填）<br>- `file_path`：文件路径（必填，cp时格式"src:dst"）<br>- `host`：远程主机名/IP（默认[localhost](http://localhost)）<br>- `ssh_port`：SSH端口（默认22，远程操作时使用）|- `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（如"容器my-nginx export成功"）<br>- `data`：包含数据操作信息的字典<br>  - `host`：操作的主机名/IP<br>  - `container_name`：容器名称<br>  - `action`：执行的操作类型<br>  - `file_path`：操作的文件路径|
|`container_logs`|本地/远程主机容器日志查询（支持实时跟踪、时间与行数筛选）|- `name`：容器名称（必填）<br>- `tail`：日志行数（默认100，0表示全部）<br>- `follow`：实时跟踪（True/False，默认False）<br>- `since`：时间筛选（可选，格式"10m"/"2024-01-01T00:00:00"）<br>- `host`：远程主机名/IP（默认[localhost](http://localhost)）<br>- `ssh_port`：SSH端口（默认22，远程操作时使用）|- `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（如"成功获取my-nginx日志"）<br>- `data`：包含日志信息的字典<br>  - `host`：操作的主机名/IP<br>  - `container_name`：容器名称<br>  - `logs`：日志内容（字符串格式）<br>  - `filter`：筛选条件（tail/since）|
|`list_containers`|本地/远程主机容器列表查询（支持运行状态、名称/镜像筛选）|- `all`：显示所有容器（True/False，默认False仅显示运行中）<br>- `filter`：筛选条件（可选，格式"name=nginx,image=nginx:latest"）<br>- `host`：远程主机名/IP（默认[localhost](http://localhost)）<br>- `ssh_port`：SSH端口（默认22，远程操作时使用）|- `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（如"成功获取本地运行中容器，共5个"）<br>- `data`：包含容器列表的字典<br>  - `host`：操作的主机名/IP<br>  - `container_count`：容器总数<br>  - `containers`：容器列表（含ID、名称、镜像、状态等）<br>  - `filter`：筛选条件（all/name/image）|
## 三、工具使用说明

1. **前置依赖**：目标主机需安装 Docker（版本19.03+）并启动服务，本地操作需执行用户加入`docker`组或具备`sudo`权限；远程操作需目标主机开启SSH服务，且SSH用户有Docker操作权限（可通过`usermod -aG docker 用户名`授权）。

2. **本地操作流程**：① 容器部署：调用`manage_container`，传入`action=create`、`name=my-nginx`、`image=nginx:latest`及`ports=8080:80`，再执行`action=start`启动容器；② 镜像管理：调用`manage_image`，`action=pull`拉取镜像，`action=tag`添加标签，私有镜像需补充`registry_auth`；③ 日志查询：调用`container_logs`，传入`name=my-nginx`、`tail=50`查看最近50行日志，`follow=True`开启实时跟踪。

3. **远程操作流程**：① 配置准备：在`DockerConfig`的`remote_hosts`中添加目标主机（含host、name、port、username、password）；② 远程执行：调用工具时传入`host=远程IP/别名`，如`list_containers(host=prod-server, all=True)`查询远程所有容器；③ 端口覆盖：若远程SSH端口非22，补充`ssh_port=2222`参数（如`manage_container(name=my-app, action=restart, host=prod-server, ssh_port=2222)`）。

## 四、注意事项

- **容器名称唯一性**：`name`参数在同一主机内不可重复，重复创建会返回"容器已存在"错误，需先执行`delete`操作或更换名称。

- **镜像格式规范**：`image`参数需包含名称与标签（如ubuntu:20.04），未指定标签默认拉取`latest`版本，私有镜像需带仓库地址（如[registry.com/app:v1](http://registry.com/app:v1)）。

- **数据卷权限**：`volumes`挂载本地目录时，需确保本地目录存在且权限正确（容器内用户需有读写权限，可通过`chmod 755 /host/path`调整）。

- **私有仓库安全**：`registry_auth`参数需传入"用户名:密码"，生产环境建议通过配置文件加密存储，避免明文硬编码。

- **实时日志超时**：`follow=True`时工具默认10秒超时，避免长期阻塞进程，如需持续跟踪需在代码中循环调用。

- **大镜像操作**：拉取/推送GB级以上镜像时，可在`execute_local_command`/`execute_remote_command`中调整超时参数（默认60秒），防止超时失败。
