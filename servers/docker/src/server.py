import logging
import json
import subprocess
from typing import Dict
import paramiko
from config.private.docker.config_loader import DockerConfig
from servers.docker.src.base import get_language, get_remote_auth, execute_remote_command, execute_local_command, parse_container_list, parse_image_list
from mcp.server import FastMCP

# 初始化MCP服务
mcp = FastMCP(
    "Docker Container Management MCP",
    host="0.0.0.0",
    port=DockerConfig().get_config().private_config.port
)

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)




@mcp.tool(
    name="manage_container" if get_language() else "manage_container",
    description="""
    容器增删改查核心操作（创建/启动/停止/删除/重启）
    
    参数:
        -name: 容器名称（必填，创建/操作容器时使用）
        -image: 镜像名称（创建容器必填，如nginx:latest）
        -action: 操作类型（必填，create/start/stop/delete/restart）
        -ports: 端口映射（创建容器可选，格式"8080:80,443:443"）
        -volumes: 数据卷挂载（创建容器可选，格式"/host/path:/container/path:ro"）
        -env: 环境变量（创建容器可选，格式"KEY1=VALUE1,KEY2=VALUE2"）
        -cmd: 容器启动命令（创建容器可选，如"nginx -g 'daemon off;'"）
        -restart_policy: 重启策略（no/always/on-failure/unless-stopped，默认no）
        -host: 远程主机名/IP（默认localhost）
        -ssh_port: SSH端口（默认22）
    
    返回:
        -success: 操作是否成功
        -message: 操作结果描述
        -data: 容器操作详情
    """ if get_language() else """
    Core container management operations (create/start/stop/delete/restart)
    
    Parameters:
        -name: Container name (required for creating/operating containers)
        -image: Image name (required for creating containers, e.g., nginx:latest)
        -action: Operation type (required, create/start/stop/delete/restart)
        -ports: Port mapping (optional for creating containers, format "8080:80,443:443")
        -volumes: Volume mount (optional for creating containers, format "/host/path:/container/path:ro")
        -env: Environment variables (optional for creating containers, format "KEY1=VALUE1,KEY2=VALUE2")
        -cmd: Container start command (optional for creating containers, e.g., "nginx -g 'daemon off;'")
        -restart_policy: Restart policy (no/always/on-failure/unless-stopped, default no)
        -host: Remote hostname/IP (default localhost)
        -ssh_port: SSH port (default 22)
    
    Returns:
        -success: Operation success status
        -message: Operation result description
        -data: Container operation details
    """
)
def manage_container(
    name: str,
    image: str = "",
    action: str = "start",
    ports: str = "",
    volumes: str = "",
    env: str = "",
    cmd: str = "",
    restart_policy: str = "no",
    host: str = "localhost",
    ssh_port: int = 22
) -> Dict:
    is_zh = get_language()
    result = {
        "success": False,
        "message": "",
        "data": {
            "host": host,
            "container_name": name,
            "action": action
        }
    }

    # 参数校验
    valid_actions = ["create", "start", "stop", "delete", "restart"]
    if action not in valid_actions:
        result["message"] = f"操作类型必须是{valid_actions}之一" if is_zh else f"Action must be one of {valid_actions}"
        return result
    
    if action == "create" and not image:
        result["message"] = "创建容器时必须指定镜像名称" if is_zh else "Image name is required when creating container"
        return result
    
    valid_restart = ["no", "always", "on-failure", "unless-stopped"]
    if restart_policy not in valid_restart:
        result["message"] = f"重启策略必须是{valid_restart}之一" if is_zh else f"Restart policy must be one of {valid_restart}"
        return result

    # 构建Docker命令
    command = ""
    if action == "create":
        # 构建创建容器命令
        port_params = f"-p {ports.replace(',', ' -p ')}" if ports else ""
        volume_params = f"-v {volumes.replace(',', ' -v ')}" if volumes else ""
        env_params = f"-e {env.replace(',', ' -e ')}" if env else ""
        cmd_param = f"--entrypoint '{cmd}'" if cmd else ""
        restart_param = f"--restart {restart_policy}"
        
        command_parts = [
            "docker create",
            port_params,
            volume_params,
            env_params,
            cmd_param,
            restart_param,
            f"--name {name}",
            image
        ]
        command = " ".join(filter(None, command_parts)).strip()
    elif action == "delete":
        command = f"docker rm -f {name}"  # -f强制删除运行中的容器
    else:
        command = f"docker {action} {name}"

    # 执行命令
    if host in ["localhost", "127.0.0.1"]:
        exec_result = execute_local_command(command)
    else:
        auth = get_remote_auth(host)
        if not auth:
            result["message"] = f"未找到远程主机{host}的认证配置" if is_zh else f"Authentication config for {host} not found"
            return result
        auth["port"] = ssh_port
        exec_result = execute_remote_command(auth, command)

    if exec_result["success"]:
        result["success"] = True
        result["message"] = f"容器{name} {action}成功" if is_zh else f"Container {name} {action} succeeded"
        result["data"]["details"] = exec_result["output"]
    else:
        result["message"] = f"容器{name} {action}失败：{exec_result['error']}" if is_zh else f"Container {name} {action} failed: {exec_result['error']}"

    return result


@mcp.tool(
    name="manage_image" if get_language() else "manage_image",
    description="""
    镜像增删改查核心操作（拉取/删除/标签/推送/详情）
    
    参数:
        -image: 镜像名称（必填，如nginx:latest）
        -action: 操作类型（必填，pull/delete/tag/push/inspect）
        -new_tag: 新标签（tag操作必填，格式"mynginx:v1"）
        -registry_auth: 镜像仓库认证（格式"username:password"，私有仓库用）
        -host: 远程主机名/IP（默认localhost）
        -ssh_port: SSH端口（默认22）
    
    返回:
        -success: 操作是否成功
        -message: 操作结果描述
        -data: 镜像操作详情
    """ if get_language() else """
    Core image management operations (pull/delete/tag/push/inspect)
    
    Parameters:
        -image: Image name (required, e.g., nginx:latest)
        -action: Operation type (required, pull/delete/tag/push/inspect)
        -new_tag: New tag (required for tag operation, format "mynginx:v1")
        -registry_auth: Registry authentication (format "username:password" for private registries)
        -host: Remote hostname/IP (default localhost)
        -ssh_port: SSH port (default 22)
    
    Returns:
        -success: Operation success status
        -message: Operation result description
        -data: Image operation details
    """
)
def manage_image(
    image: str,
    action: str = "pull",
    new_tag: str = "",
    registry_auth: str = "",
    host: str = "localhost",
    ssh_port: int = 22
) -> Dict:
    is_zh = get_language()
    result = {
        "success": False,
        "message": "",
        "data": {
            "host": host,
            "image": image,
            "action": action
        }
    }

    valid_actions = ["pull", "delete", "tag", "push", "inspect"]
    if action not in valid_actions:
        result["message"] = f"操作类型必须是{valid_actions}之一" if is_zh else f"Action must be one of {valid_actions}"
        return result
    
    if action == "tag" and not new_tag:
        result["message"] = "tag操作必须指定新标签名称" if is_zh else "New tag is required for tag operation"
        return result
    
    if action in ["push", "pull"] and registry_auth and ":" not in registry_auth:
        result["message"] = "仓库认证格式应为username:password" if is_zh else "Registry auth format must be username:password"
        return result

    # 构建命令
    command = ""
    if action == "pull":
        auth_param = f"docker login -u {registry_auth.split(':')[0]} -p {registry_auth.split(':')[1]} && " if registry_auth else ""
        command = f"{auth_param}docker pull {image}"
    elif action == "delete":
        command = f"docker rmi -f {image}"  # -f强制删除
    elif action == "tag":
        command = f"docker tag {image} {new_tag}"
    elif action == "push":
        auth_param = f"docker login -u {registry_auth.split(':')[0]} -p {registry_auth.split(':')[1]} && " if registry_auth else ""
        command = f"{auth_param}docker push {image}"
    elif action == "inspect":
        command = f"docker inspect {image}"

    # 执行命令
    if host in ["localhost", "127.0.0.1"]:
        exec_result = execute_local_command(command)
    else:
        auth = get_remote_auth(host)
        if not auth:
            result["message"] = f"未找到远程主机{host}的认证配置" if is_zh else f"Authentication config for {host} not found"
            return result
        auth["port"] = ssh_port
        exec_result = execute_remote_command(auth, command)

    if exec_result["success"]:
        result["success"] = True
        if action == "inspect":
            # 解析镜像详情
            try:
                inspect_data = json.loads(exec_result["output"])[0]
                result["data"]["inspect"] = {
                    "id": inspect_data["Id"],
                    "repo_tags": inspect_data["RepoTags"],
                    "created": inspect_data["Created"],
                    "size": inspect_data["Size"],
                    "architecture": inspect_data["Architecture"],
                    "os": inspect_data["Os"],
                    "config": inspect_data["Config"]
                }
            except Exception as e:
                result["data"]["inspect"] = f"解析失败: {str(e)}" if is_zh else f"Parse failed: {str(e)}"
        result["message"] = f"镜像{image} {action}成功" if is_zh else f"Image {image} {action} succeeded"
        result["data"]["details"] = exec_result["output"] if action != "inspect" else ""
    else:
        result["message"] = f"镜像{image} {action}失败：{exec_result['error']}" if is_zh else f"Image {image} {action} failed: {exec_result['error']}"

    return result


@mcp.tool(
    name="list_containers" if get_language() else "list_containers",
    description="""
    列出容器列表（支持过滤运行状态）
    
    参数:
        -all: 是否显示所有容器（True/False，默认False仅显示运行中）
        -filter: 过滤条件（可选，格式"name=nginx,image=nginx"）
        -host: 远程主机名/IP（默认localhost）
        -ssh_port: SSH端口（默认22）
    
    返回:
        -success: 操作是否成功
        -message: 操作结果描述
        -data: 容器列表及统计信息
    """ if get_language() else """
    List containers (supports filtering by running status)
    
    Parameters:
        -all: Whether to show all containers (True/False, default False for running only)
        -filter: Filter conditions (optional, format "name=nginx,image=nginx")
        -host: Remote hostname/IP (default localhost)
        -ssh_port: SSH port (default 22)
    
    Returns:
        -success: Operation success status
        -message: Operation result description
        -data: Container list and statistics
    """
)
def list_containers(
    all: bool = False,
    filter: str = "",
    host: str = "localhost",
    ssh_port: int = 22
) -> Dict:
    is_zh = get_language()
    result = {
        "success": False,
        "message": "",
        "data": {
            "host": host,
            "all_containers": all,
            "container_count": 0,
            "containers": []
        }
    }

    # 构建命令
    all_param = "-a" if all else ""
    filter_params = ""
    if filter:
        filter_parts = [f"--filter {f.split('=')[0]}={f.split('=')[1]}" for f in filter.split(",")]
        filter_params = " ".join(filter_parts)
    
    command = f"docker ps {all_param} {filter_params} --format 'table {{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Command}}\t{{.CreatedSince}}\t{{.Status}}\t{{.Ports}}\t{{.Networks}}'"

    # 执行命令
    if host in ["localhost", "127.0.0.1"]:
        exec_result = execute_local_command(command)
    else:
        auth = get_remote_auth(host)
        if not auth:
            result["message"] = f"未找到远程主机{host}的认证配置" if is_zh else f"Authentication config for {host} not found"
            return result
        auth["port"] = ssh_port
        exec_result = execute_remote_command(auth, command)

    if exec_result["success"]:
        containers = parse_container_list(exec_result["output"])
        result["data"]["containers"] = containers
        result["data"]["container_count"] = len(containers)
        result["success"] = True
        status = "所有" if all else "运行中"
        result["message"] = f"成功获取{status}容器，共{len(containers)}个" if is_zh else f"Successfully obtained {status} containers, total {len(containers)}"
    else:
        result["message"] = f"获取容器列表失败：{exec_result['error']}" if is_zh else f"Failed to get container list: {exec_result['error']}"

    return result


@mcp.tool(
    name="list_images" if get_language() else "list_images",
    description="""
    列出镜像列表（支持过滤）
    
    参数:
        -filter: 过滤条件（可选，格式"repository=nginx,tag=latest"）
        -host: 远程主机名/IP（默认localhost）
        -ssh_port: SSH端口（默认22）
    
    返回:
        -success: 操作是否成功
        -message: 操作结果描述
        -data: 镜像列表及统计信息
    """ if get_language() else """
    List images (supports filtering)
    
    Parameters:
        -filter: Filter conditions (optional, format "repository=nginx,tag=latest")
        -host: Remote hostname/IP (default localhost)
        -ssh_port: SSH port (default 22)
    
    Returns:
        -success: Operation success status
        -message: Operation result description
        -data: Image list and statistics
    """
)
def list_images(
    filter: str = "",
    host: str = "localhost",
    ssh_port: int = 22
) -> Dict:
    is_zh = get_language()
    result = {
        "success": False,
        "message": "",
        "data": {
            "host": host,
            "image_count": 0,
            "images": []
        }
    }

    # 构建命令
    filter_params = ""
    if filter:
        filter_parts = [f"--filter {f.split('=')[0]}={f.split('=')[1]}" for f in filter.split(",")]
        filter_params = " ".join(filter_parts)
    
    command = f"docker images {filter_params} --format 'table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.CreatedSince}}\t{{.Size}}'"

    # 执行命令
    if host in ["localhost", "127.0.0.1"]:
        exec_result = execute_local_command(command)
    else:
        auth = get_remote_auth(host)
        if not auth:
            result["message"] = f"未找到远程主机{host}的认证配置" if is_zh else f"Authentication config for {host} not found"
            return result
        auth["port"] = ssh_port
        exec_result = execute_remote_command(auth, command)

    if exec_result["success"]:
        images = parse_image_list(exec_result["output"])
        result["data"]["images"] = images
        result["data"]["image_count"] = len(images)
        result["success"] = True
        result["message"] = f"成功获取镜像列表，共{len(images)}个" if is_zh else f"Successfully obtained image list, total {len(images)}"
    else:
        result["message"] = f"获取镜像列表失败：{exec_result['error']}" if is_zh else f"Failed to get image list: {exec_result['error']}"

    return result


@mcp.tool(
    name="container_data_operate" if get_language() else "container_data_operate",
    description="""
    容器数据操作（导入/导出容器、文件拷贝）
    
    参数:
        -name: 容器名称（必填，import时为镜像名称前缀）
        -action: 操作类型（必填，export/import/cp）
        -file_path: 文件路径（必填，export时为输出路径，import时为输入路径，cp时为"src:dst"）
        -host: 远程主机名/IP（默认localhost）
        -ssh_port: SSH端口（默认22）
    
    返回:
        -success: 操作是否成功
        -message: 操作结果描述
        -data: 数据操作详情
    """ if get_language() else """
    Container data operations (export/import container, file copy)
    
    Parameters:
        -name: Container name (required, image name prefix for import)
        -action: Operation type (required, export/import/cp)
        -file_path: File path (required, output path for export, input path for import, "src:dst" for cp)
        -host: Remote hostname/IP (default localhost)
        -ssh_port: SSH port (default 22)
    
    Returns:
        -success: Operation success status
        -message: Operation result description
        -data: Data operation details
    """
)
def container_data_operate(
    name: str,
    action: str,
    file_path: str,
    host: str = "localhost",
    ssh_port: int = 22
) -> Dict:
    is_zh = get_language()
    result = {
        "success": False,
        "message": "",
        "data": {
            "host": host,
            "container_name": name,
            "action": action,
            "file_path": file_path
        }
    }

    valid_actions = ["export", "import", "cp"]
    if action not in valid_actions:
        result["message"] = f"操作类型必须是{valid_actions}之一" if is_zh else f"Action must be one of {valid_actions}"
        return result

    # 构建命令
    command = ""
    if action == "export":
        command = f"docker export {name} > {file_path}"
    elif action == "import":
        command = f"cat {file_path} | docker import - {name}:imported"
    elif action == "cp":
        if ":" not in file_path:
            result["message"] = "cp操作路径格式应为'src:dst'（本地到容器或容器到本地）" if is_zh else "cp operation path format should be 'src:dst' (local to container or container to local)"
            return result
        # 判断是容器到本地还是本地到容器
        if file_path.startswith(f"{name}:"):
            # 容器到本地：docker cp 容器名:路径 本地路径
            container_path = file_path[len(f"{name}:"):]
            command = f"docker cp {name}:{container_path} {file_path.split(':')[1]}"
        else:
            # 本地到容器：docker cp 本地路径 容器名:路径
            local_path, container_path = file_path.split(":", 1)
            command = f"docker cp {local_path} {name}:{container_path}"

    # 执行命令
    if host in ["localhost", "127.0.0.1"]:
        exec_result = execute_local_command(command)
    else:
        auth = get_remote_auth(host)
        if not auth:
            result["message"] = f"未找到远程主机{host}的认证配置" if is_zh else f"Authentication config for {host} not found"
            return result
        auth["port"] = ssh_port
        exec_result = execute_remote_command(auth, command)

    if exec_result["success"]:
        result["success"] = True
        result["message"] = f"容器{name} {action}操作成功" if is_zh else f"Container {name} {action} operation succeeded"
    else:
        result["message"] = f"容器{name} {action}操作失败：{exec_result['error']}" if is_zh else f"Container {name} {action} operation failed: {exec_result['error']}"

    return result


@mcp.tool(
    name="container_exec_command" if get_language() else "container_exec_command",
    description="""
    在容器内执行命令
    
    参数:
        -name: 容器名称（必填）
        -cmd: 执行命令（必填，如"ls -l /var/log"）
        -interactive: 是否交互式（True/False，默认False）
        -host: 远程主机名/IP（默认localhost）
        -ssh_port: SSH端口（默认22）
    
    返回:
        -success: 操作是否成功
        -message: 操作结果描述
        -data: 命令执行输出
    """ if get_language() else """
    Execute command inside container
    
    Parameters:
        -name: Container name (required)
        -cmd: Command to execute (required, e.g., "ls -l /var/log")
        -interactive: Whether interactive (True/False, default False)
        -host: Remote hostname/IP (default localhost)
        -ssh_port: SSH port (default 22)
    
    Returns:
        -success: Operation success status
        -message: Operation result description
        -data: Command execution output
    """
)
def container_exec_command(
    name: str,
    cmd: str,
    interactive: bool = False,
    host: str = "localhost",
    ssh_port: int = 22
) -> Dict:
    is_zh = get_language()
    result = {
        "success": False,
        "message": "",
        "data": {
            "host": host,
            "container_name": name,
            "command": cmd,
            "output": ""
        }
    }

    if not cmd.strip():
        result["message"] = "执行命令不能为空" if is_zh else "Command to execute cannot be empty"
        return result

    # 构建命令
    interactive_param = "-it" if interactive else ""
    command = f"docker exec {interactive_param} {name} {cmd}"

    # 执行命令
    if host in ["localhost", "127.0.0.1"]:
        exec_result = execute_local_command(command)
    else:
        auth = get_remote_auth(host)
        if not auth:
            result["message"] = f"未找到远程主机{host}的认证配置" if is_zh else f"Authentication config for {host} not found"
            return result
        auth["port"] = ssh_port
        exec_result = execute_remote_command(auth, command)

    result["data"]["output"] = exec_result["output"]
    # 命令执行成功可能有非零退出码但有输出（如grep未匹配），放宽判断条件
    if exec_result["success"] or len(exec_result["output"]) > 0:
        result["success"] = True
        result["message"] = f"在容器{name}内执行命令成功" if is_zh else f"Successfully executed command inside container {name}"
    else:
        result["message"] = f"在容器{name}内执行命令失败：{exec_result['error']}" if is_zh else f"Failed to execute command inside container {name}: {exec_result['error']}"

    return result


@mcp.tool(
    name="container_logs" if get_language() else "container_logs",
    description="""
    查看容器日志
    
    参数:
        -name: 容器名称（必填）
        -tail: 显示末尾行数（默认100行，0表示全部）
        -follow: 是否实时跟踪（True/False，默认False）
        -since: 显示指定时间之后的日志（如"10m"表示10分钟内，"2024-01-01T00:00:00"）
        -host: 远程主机名/IP（默认localhost）
        -ssh_port: SSH端口（默认22）
    
    返回:
        -success: 操作是否成功
        -message: 操作结果描述
        -data: 容器日志内容
    """ if get_language() else """
    View container logs
    
    Parameters:
        -name: Container name (required)
        -tail: Number of tail lines to show (default 100, 0 for all)
        -follow: Whether to follow logs in real-time (True/False, default False)
        -since: Show logs since specified time (e.g., "10m" for 10 minutes ago, "2024-01-01T00:00:00")
        -host: Remote hostname/IP (default localhost)
        -ssh_port: SSH port (default 22)
    
    Returns:
        -success: Operation success status
        -message: Operation result description
        -data: Container log content
    """
)
def container_logs(
    name: str,
    tail: int = 100,
    follow: bool = False,
    since: str = "",
    host: str = "localhost",
    ssh_port: int = 22
) -> Dict:
    is_zh = get_language()
    result = {
        "success": False,
        "message": "",
        "data": {
            "host": host,
            "container_name": name,
            "logs": ""
        }
    }

    # 构建命令
    tail_param = f"--tail {tail}" if tail != 0 else ""
    follow_param = "-f" if follow else ""
    since_param = f"--since {since}" if since else ""
    
    command = f"docker logs {tail_param} {follow_param} {since_param} {name}"
    # 实时跟踪时设置较短超时（避免长期阻塞）
    timeout = 10 if follow else 60

    # 执行命令（单独处理超时逻辑）
    try:
        if host in ["localhost", "127.0.0.1"]:
            output = subprocess.check_output(
                command,
                shell=True,
                text=True,
                stderr=subprocess.STDOUT,
                timeout=timeout
            )
            result["data"]["logs"] = output.strip()
            result["success"] = True
            result["message"] = f"成功获取容器{name}日志" if is_zh else f"Successfully obtained logs for container {name}"
        else:
            auth = get_remote_auth(host)
            if not auth:
                result["message"] = f"未找到远程主机{host}的认证配置" if is_zh else f"Authentication config for {host} not found"
                return result
            
            ssh_conn = paramiko.SSHClient()
            ssh_conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh_conn.connect(
                hostname=auth["host"],
                port=ssh_port,
                username=auth["username"],
                password=auth["password"],
                timeout=15
            )
            
            stdin, stdout, stderr = ssh_conn.exec_command(command, timeout=timeout)
            result["data"]["logs"] = stdout.read().decode("utf-8", errors="replace").strip()
            error = stderr.read().decode("utf-8", errors="replace").strip()
            
            if not error or len(result["data"]["logs"]) > 0:
                result["success"] = True
                result["message"] = f"成功获取远程容器{name}日志" if is_zh else f"Successfully obtained logs for remote container {name}"
            else:
                result["message"] = f"获取远程容器日志失败：{error}" if is_zh else f"Failed to get remote container logs: {error}"
                
            ssh_conn.close()
    except subprocess.TimeoutExpired:
        # 实时跟踪超时属于正常现象，返回已获取的日志
        if follow and len(result["data"]["logs"]) > 0:
            result["success"] = True
            result["message"] = f"已获取容器{name}部分日志（实时跟踪超时）" if is_zh else f"Obtained partial logs for container {name} (follow timeout)"
        else:
            result["message"] = f"获取日志超时（>{timeout}秒）" if is_zh else f"Log retrieval timed out (> {timeout}s)"
    except Exception as e:
        result["message"] = f"获取日志失败：{str(e)}" if is_zh else f"Failed to get logs: {str(e)}"

    return result


@mcp.tool(
    name="manage_network" if get_language() else "manage_network",
    description="""
    Docker网络管理（创建/删除/连接容器）
    
    参数:
        -name: 网络名称（必填）
        -action: 操作类型（必填，create/delete/connect/disconnect）
        -driver: 网络驱动（create时必填，bridge/overlay/macvlan，默认bridge）
        -subnet: 子网网段（create可选，如172.20.0.0/16）
        -container: 容器名称（connect/disconnect时必填）
        -host: 远程主机名/IP（默认localhost）
        -ssh_port: SSH端口（默认22）
    
    返回:
        -success: 操作是否成功
        -message: 操作结果描述
        -data: 网络操作详情
    """ if get_language() else """
    Docker network management (create/delete/connect container)
    
    Parameters:
        -name: Network name (required)
        -action: Operation type (required, create/delete/connect/disconnect)
        -driver: Network driver (required for create, bridge/overlay/macvlan, default bridge)
        -subnet: Subnet CIDR (optional for create, e.g., 172.20.0.0/16)
        -container: Container name (required for connect/disconnect)
        -host: Remote hostname/IP (default localhost)
        -ssh_port: SSH port (default 22)
    
    Returns:
        -success: Operation success status
        -message: Operation result description
        -data: Network operation details
    """
)
def manage_network(
    name: str,
    action: str,
    driver: str = "bridge",
    subnet: str = "",
    container: str = "",
    host: str = "localhost",
    ssh_port: int = 22
) -> Dict:
    is_zh = get_language()
    result = {
        "success": False,
        "message": "",
        "data": {
            "host": host,
            "network_name": name,
            "action": action
        }
    }

    valid_actions = ["create", "delete", "connect", "disconnect"]
    if action not in valid_actions:
        result["message"] = f"操作类型必须是{valid_actions}之一" if is_zh else f"Action must be one of {valid_actions}"
        return result
    
    valid_drivers = ["bridge", "overlay", "macvlan", "host", "none"]
    if action == "create" and driver not in valid_drivers:
        result["message"] = f"网络驱动必须是{valid_drivers}之一" if is_zh else f"Network driver must be one of {valid_drivers}"
        return result
    
    if action in ["connect", "disconnect"] and not container:
        result["message"] = f"{action}操作必须指定容器名称" if is_zh else f"Container name is required for {action} operation"
        return result

    # 构建命令
    command = ""
    if action == "create":
        driver_param = f"--driver {driver}"
        subnet_param = f"--subnet {subnet}" if subnet else ""
        command = f"docker network create {driver_param} {subnet_param} {name}"
    elif action == "delete":
        command = f"docker network rm {name}"
    elif action == "connect":
        command = f"docker network connect {name} {container}"
    elif action == "disconnect":
        command = f"docker network disconnect {name} {container}"

    # 执行命令
    if host in ["localhost", "127.0.0.1"]:
        exec_result = execute_local_command(command)
    else:
        auth = get_remote_auth(host)
        if not auth:
            result["message"] = f"未找到远程主机{host}的认证配置" if is_zh else f"Authentication config for {host} not found"
            return result
        auth["port"] = ssh_port
        exec_result = execute_remote_command(auth, command)

    if exec_result["success"]:
        result["success"] = True
        result["message"] = f"网络{name} {action}成功" if is_zh else f"Network {name} {action} succeeded"
        result["data"]["details"] = exec_result["output"]
    else:
        result["message"] = f"网络{name} {action}失败：{exec_result['error']}" if is_zh else f"Network {name} {action} failed: {exec_result['error']}"

    return result
    

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='sse')