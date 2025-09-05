| 工具名称 | 工具功能 | 核心输入参数 | 关键返回内容 |
| ---- | ---- | ---- | ---- |
| `numa_bind_docker_tool` | 在目标设备（本地/远程）上为 Docker 容器配置 NUMA 绑定 | - `host`：远程主机名/IP（本地采集可不填）、`image`镜像名称、`cpuset_cpus`允许使用的 CPU 核心范围、`cpuset_mems`允许使用的内存节点、`detach`是否后台运行容器（默认 False） | `status`操作状态（success / error）、`message`操作结果信息、`output`命令的原始输出（如有） |