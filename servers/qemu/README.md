# QEMU MCP 工具介绍及使用说明

# QEMU 虚拟机管理控制程序（MCP）规范文档

## 一、服务介绍

本服务是一款基于`QEMU`（Quick Emulator）工具封装实现的虚拟机管理控制程序（MCP），核心功能为对本地或远程服务器的虚拟机进行**全生命周期管理（创建/启动/停止/删除/配置修改）、列表查询、实时状态监控**，支持按虚拟机名称、状态、架构等维度筛选，为虚拟化环境部署、测试场景运维、企业级虚拟机管理提供标准化工具支撑，适配x86_64、arm64等多架构虚拟化需求。

## 二、核心工具信息

|工具名称|工具功能|核心输入参数|关键返回内容|
|---|---|---|---|
|`manage_vm`|本地/远程主机虚拟机全生命周期管理（创建/启动/停止/删除/修改配置）|- `name`：虚拟机名称（必填，唯一标识虚拟机）<br>- `action`：操作类型（create/start/stop/delete/modify，必填）<br>- `arch`：CPU架构（create时必填，如x86_64/arm64）<br>- `memory`：内存大小（create/modify可选，如2G/4096M，默认2G）<br>- `disk`：磁盘配置（create/modify可选，格式"path=/data/vm/disk.qcow2,size=20G"）<br>- `iso`：系统镜像路径（create可选，如/data/iso/ubuntu-22.04.iso）<br>- `vcpus`：CPU核心数（create/modify可选，默认2核）<br>- `vm_dir`：虚拟机存储目录（create可选，默认/var/lib/qemu）<br>- `host`：远程主机名/IP（默认[localhost](http://localhost)，本地操作可不填）<br>- `ssh_port`：SSH端口（默认22，远程操作时使用）<br>- `ssh_user`：SSH用户名（远程操作必填）<br>- `ssh_pwd`：SSH密码（远程操作必填，与ssh_key二选一）<br>- `ssh_key`：SSH私钥路径（远程操作可选，优先于密码）|- `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（如"虚拟机ubuntu-vm create成功"）<br>- `data`：包含虚拟机操作信息的字典<br>  - `host`：操作的主机名/IP<br>  - `vm_name`：虚拟机名称<br>  - `action`：执行的操作类型<br>  - `details`：操作详情（如修改前后配置对比、磁盘路径）|
|`list_vms`|本地/远程主机虚拟机列表查询（支持按状态、架构、名称筛选）|- `status`：虚拟机状态（可选，running/stopped/all，默认all）<br>- `arch`：CPU架构（可选，如x86_64/arm64，筛选指定架构虚拟机）<br>- `filter_name`：名称模糊筛选（可选，如"ubuntu"筛选含该字段的虚拟机）<br>- `vm_dir`：虚拟机存储目录（默认/var/lib/qemu）<br>- `host`/`ssh_port`/`ssh_user`/`ssh_pwd`/`ssh_key`：同`manage_vm`|- `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（如"成功获取本地运行中虚拟机，共3个"）<br>- `data`：包含虚拟机列表的字典<br>  - `host`：操作的主机名/IP<br>  - `vm_count`：虚拟机总数<br>  - `vms`：虚拟机列表，每个设备包含：<br>    - `name`：虚拟机名称<br>    - `arch`：CPU架构<br>    - `vcpus`：CPU核心数<br>    - `memory`：内存大小<br>    - `disk`：磁盘配置（路径+大小）<br>    - `status`：运行状态（running/stopped）|
|`monitor_vm_status`|本地/远程主机虚拟机实时状态监控（CPU/内存/磁盘/网络）|- `name`：虚拟机名称（必填，指定监控目标）<br>- `metrics`：监控指标（可选，cpu/memory/disk/network/all，默认all）<br>- `interval`：监控采样间隔（可选，单位秒，默认5秒，最小值1秒）<br>- `count`：采样次数（可选，默认1次，0表示持续采样直到手动停止）<br>- `host`/`ssh_port`/`ssh_user`/`ssh_pwd`/`ssh_key`：同`manage_vm`|- `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（如"成功获取ubuntu-vm 5次采样数据"）<br>- `data`：包含监控数据的字典<br>  - `host`：操作的主机名/IP<br>  - `vm_name`：虚拟机名称<br>  - `timestamp`：采样时间列表（对应每条数据的时间戳）<br>  - `metrics_data`：监控指标数据（按metrics字段返回对应指标的采样值）|
## 三、工具使用说明

1. **本地操作规则**：不填写`host`、`ssh_user`、`ssh_pwd`、`ssh_key`参数，默认对本机（`localhost`）的虚拟机进行操作；仅需提供`name`、`action`等核心业务参数（如`create`需补充`arch`，`modify`需补充待修改的配置项）。

2. **远程操作规则**：必须提供`host`（远程主机IP/hostname）、`ssh_user`（SSH用户名），以及`ssh_pwd`或`ssh_key`（二选一）；`ssh_port`可选（默认22）；需确保远程主机已安装QEMU工具集（含qemu-system-x86_64/qemu-img等），且SSH用户具备虚拟机文件（磁盘/镜像）的读写权限与QEMU操作权限。

3. **权限要求**：  

    - 本地操作：需运行在具有QEMU操作权限的用户下（普通用户可操作个人虚拟机，系统级虚拟机需`sudo`）。  

    - 远程操作：SSH用户需对QEMU工具及虚拟机存储目录（`vm_dir`）有读写权限，建议通过`usermod -aG kvm 用户名`授予KVM加速权限。

## 四、注意事项

- **虚拟机名称唯一性**：`name`参数在同一主机内不可重复，重复创建会返回"虚拟机已存在"错误，需先执行`delete`操作或更换名称。

- **架构与镜像匹配**：`create`时`arch`参数需与`iso`系统镜像架构一致（如arm64架构需对应arm版本ISO），否则虚拟机无法启动。

- **磁盘格式限制**：工具默认支持qcow2（动态扩容）与raw（固定大小）格式，`modify`操作扩展磁盘时仅支持qcow2格式，raw格式需手动扩容后再更新配置。

- **监控前置条件**：`monitor_vm_status`仅支持监控运行中（running）的虚拟机，未运行虚拟机无法采集指标；且需确保目标主机已安装`iostat`、`iftop`等监控依赖工具。

- **重置与数据风险**：`manage_vm(action=delete)`会删除虚拟机磁盘文件，操作前需确认数据已备份；`modify`操作（如调整内存/CPU）会重启虚拟机，需提前停止该虚拟机上的业务任务。

- **工具依赖性**：所有操作依赖目标主机已安装QEMU工具集（版本6.0+），未安装会返回"qemu-system-xxx: command not found"错误，需通过官方渠道安装对应架构的QEMU组件。

