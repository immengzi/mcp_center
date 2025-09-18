import logging
import paramiko
import subprocess
from typing import Dict, Optional
from mcp.server import FastMCP
from config.private.file_content_tool.config_loader import FileCommandConfig
from config.public.base_config_loader import LanguageEnum

# 初始化MCP服务
mcp = FastMCP(
    "File Grep Tool",
    host="0.0.0.0",
    port=FileCommandConfig().get_config().private_config.port
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def get_language() -> bool:
    """获取语言配置：True=中文，False=英文"""
    return FileCommandConfig().get_config().public_config.language == LanguageEnum.ZH

def get_remote_auth(ip: str) -> Optional[Dict]:
    """
    获取服务器认证信息：匹配IP/主机名对应的连接配置
    """
    for host_config in FileCommandConfig().get_config().public_config.remote_hosts:
        if ip in [host_config.host, host_config.name]:
            # 返回标准连接字典，确保键与后续使用一致
            return {
                "host": host_config.host,  # 默认为目标IP
                "port": host_config.port,  # 默认为SSH默认端口22
                "username": host_config.username,
                "password": host_config.password
            }
    return None


@mcp.tool(
    name="file_grep_tool" if get_language() else "file_grep_tool",
    description="""
    搜索文件中匹配指定模式的内容（本地/远程均支持）
    
    参数:
        -target: 目标主机IP/hostname，None表示本地
        -file_path: 目标文件路径（必填，如"/var/log/syslog"）
        -pattern: 搜索模式（支持正则，必填，如"error"）
        -options: grep可选参数（如"-i"忽略大小写、"-n"显示行号）
    
    返回:
        -success: 执行结果（True/False）
        -message: 执行信息/错误提示
        -result: 匹配结果列表（成功时返回）
        -target: 执行目标主机
    """
    if get_language() else
    """
    Search for content matching the specified pattern in the file (supports local/remote)
    
    Parameters:
        -target: Target host IP/hostname, None for local
        -file_path: Target file path (required, e.g. "/var/log/syslog")
        -pattern: Search pattern (supports regex, required, e.g. "error")
        -options: Optional grep parameters (e.g. "-i" ignore case, "-n" show line numbers)
    
    Returns:
        -success: Execution result (True/False)
        -message: Execution info/error prompt
        -result: List of matching results (returned on success)
        -target: Target host for execution
    """
)
def file_grep_tool(
    target: Optional[str] = None,
    file_path: str = "",
    pattern: str = "",
    options: str = ""
) -> Dict:
    is_zh = get_language()
    target_host = target or "127.0.0.1"
    result = {
        "success": False,
        "message": "",
        "result": [],
        "target": target_host
    }

    # 基础参数校验
    if not file_path.strip():
        result["message"] = "文件路径不能为空" if is_zh else "File path cannot be empty"
        return result
    if not pattern.strip():
        result["message"] = "搜索模式不能为空" if is_zh else "Search pattern cannot be empty"
        return result

    # 构建grep命令
    grep_cmd = f"grep {options.strip()} '{pattern.strip()}' {file_path.strip()}"

    # 本地执行
    if target_host == "127.0.0.1":
        try:
            output = subprocess.check_output(
                grep_cmd, shell=True, text=True, stderr=subprocess.STDOUT
            )
            result["success"] = True
            result["message"] = f"本地文件搜索完成（路径：{file_path}）" if is_zh else f"Local file search completed (path: {file_path})"
            result["result"] = output.strip().split("\n") if output.strip() else []
        except subprocess.CalledProcessError as e:
            # grep无匹配时退出码1，不算错误
            if e.returncode == 1:
                result["success"] = True
                result["message"] = "未找到匹配内容" if is_zh else "No matching content found"
            else:
                result["message"] = f"本地执行失败：{e.output.strip()}" if is_zh else f"Local execution failed: {e.output.strip()}"
        return result

    # 远程执行
    remote_auth = get_remote_auth(target_host)
    if not remote_auth:
        result["message"] = f"未找到远程主机（{target_host}）的认证配置" if is_zh else f"Authentication config for remote host ({target_host}) not found"
        return result
    if not (remote_auth["username"] and remote_auth["password"]):
        result["message"] = "远程执行需用户名和密码" if is_zh else "Username and password required for remote execution"
        return result

    ssh_conn: Optional[paramiko.SSHClient] = None
    try:
        ssh_conn = paramiko.SSHClient()
        ssh_conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_conn.connect(
            hostname=remote_auth["host"],
            port=remote_auth["port"],
            username=remote_auth["username"],
            password=remote_auth["password"],
            timeout=10
        )

        stdin, stdout, stderr = ssh_conn.exec_command(grep_cmd)
        stdout_msg = stdout.read().decode("utf-8").strip()
        stderr_msg = stderr.read().decode("utf-8").strip()

        if stderr_msg and "No such file or directory" in stderr_msg:
            result["message"] = f"远程文件不存在：{file_path}" if is_zh else f"Remote file does not exist: {file_path}"
        elif stderr_msg:
            result["message"] = f"远程执行失败：{stderr_msg}" if is_zh else f"Remote execution failed: {stderr_msg}"
        else:
            result["success"] = True
            result["message"] = f"远程文件搜索完成（主机：{target_host}，路径：{file_path}）" if is_zh else f"Remote file search completed (host: {target_host}, path: {file_path})"
            result["result"] = stdout_msg.split("\n") if stdout_msg else []
    except Exception as e:
        result["message"] = f"远程连接异常：{str(e)}" if is_zh else f"Remote connection exception: {str(e)}"
    finally:
        if ssh_conn:
            transport = ssh_conn.get_transport()
            if transport and transport.is_active():
                ssh_conn.close()
    return result

@mcp.tool(
    name="file_sed_tool" if get_language() else "file_sed_tool",
    description="""
    替换文件中匹配的内容（本地/远程均支持，默认不修改原文件）
    
    参数:
        -target: 目标主机IP/hostname，None表示本地
        -file_path: 目标文件路径（必填）
        -pattern: 匹配模式（如"s/old/new/g"，必填，g表示全局替换）
        -in_place: 是否直接修改原文件（True/False，默认False，仅输出结果）
        -options: sed可选参数（如"-i.bak"备份原文件）
    
    返回:
        -success: 执行结果（True/False）
        -message: 执行信息/错误提示
        -result: 替换后内容（in_place=False时返回）
        -target: 执行目标主机
    """
    if get_language() else
    """
    Replace matching content in the file (supports local/remote, no original file modification by default)
    
    Parameters:
        -target: Target host IP/hostname, None for local
        -file_path: Target file path (required)
        -pattern: Matching pattern (e.g. "s/old/new/g", required, g for global replacement)
        -in_place: Whether to modify the original file directly (True/False, default False, only output result)
        -options: Optional sed parameters (e.g. "-i.bak" backup original file)
    
    Returns:
        -success: Execution result (True/False)
        -message: Execution info/error prompt
        -result: Content after replacement (returned when in_place=False)
        -target: Target host for execution
    """
)
def file_sed_tool(
    target: Optional[str] = None,
    file_path: str = "",
    pattern: str = "",
    in_place: bool = False,
    options: str = ""
) -> Dict:
    is_zh = get_language()
    target_host = target or "127.0.0.1"
    result = {
        "success": False,
        "message": "",
        "result": "",
        "target": target_host
    }

    # 基础校验
    if not file_path.strip():
        result["message"] = "文件路径不能为空" if is_zh else "File path cannot be empty"
        return result
    if not pattern.strip() or "s/" not in pattern:
        result["message"] = "替换模式格式错误（需含s/）" if is_zh else "Replacement pattern format error (must contain s/)"
        return result

    # 构建sed命令
    in_place_opt = "-i" if in_place else ""
    sed_cmd = f"sed {options.strip()} {in_place_opt} '{pattern.strip()}' {file_path.strip()}"

    # 本地执行
    if target_host == "127.0.0.1":
        try:
            output = subprocess.check_output(
                sed_cmd, shell=True, text=True, stderr=subprocess.STDOUT
            )
            result["success"] = True
            msg = "原文件已修改" if in_place else "替换后内容已输出"
            result["message"] = f"本地sed执行成功（{msg}，路径：{file_path}）" if is_zh else f"Local sed executed successfully ({msg}, path: {file_path})"
            result["result"] = output.strip() if not in_place else ""
        except subprocess.CalledProcessError as e:
            result["message"] = f"本地执行失败：{e.output.strip()}" if is_zh else f"Local execution failed: {e.output.strip()}"
        return result

    # 远程执行（逻辑同grep，省略重复注释）
    remote_auth = get_remote_auth(target_host)
    if not remote_auth or not (remote_auth["username"] and remote_auth["password"]):
        result["message"] = "远程认证配置缺失" if is_zh else "Remote authentication config missing"
        return result

    ssh_conn: Optional[paramiko.SSHClient] = None
    try:
        ssh_conn = paramiko.SSHClient()
        ssh_conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_conn.connect(**remote_auth, timeout=10)

        stdin, stdout, stderr = ssh_conn.exec_command(sed_cmd)
        stdout_msg = stdout.read().decode("utf-8").strip()
        stderr_msg = stderr.read().decode("utf-8").strip()

        if stderr_msg:
            result["message"] = f"远程执行失败：{stderr_msg}" if is_zh else f"Remote execution failed: {stderr_msg}"
        else:
            result["success"] = True
            msg = "原文件已修改" if in_place else "替换后内容已输出"
            result["message"] = f"远程sed执行成功（{msg}，主机：{target_host}）" if is_zh else f"Remote sed executed successfully ({msg}, host: {target_host})"
            result["result"] = stdout_msg if not in_place else ""
    except Exception as e:
        result["message"] = f"远程异常：{str(e)}" if is_zh else f"Remote exception: {str(e)}"
    finally:
        if ssh_conn and ssh_conn.get_transport():
            ssh_conn.close()
    return result


@mcp.tool(
    name="file_awk_tool" if get_language() else "file_awk_tool",
    description="""
    用awk处理文本文件（支持列提取、条件过滤等，本地/远程均支持）
    
    参数:
        -target: 目标主机IP/hostname，None表示本地（127.0.0.1）
        -file_path: 目标文件路径（必填，如"/etc/passwd"或"/var/log/access.log"）
        -script: awk脚本（必填，示例："'{print $1,$3}'"提取1、3列；"'$3>100 {print $0}'"过滤第3列大于100的行）
        -options: awk可选参数（示例："-F:"指定分隔符为冒号；"-v OFS=,"指定输出分隔符为逗号）
    
    返回:
        -success: 执行结果（True=成功，False=失败）
        -message: 执行状态描述/错误提示（中文/英文根据配置自动切换）
        -result: awk处理结果列表（每行一个元素，无结果时返回空列表）
        -target: 实际执行的目标主机IP/hostname
    """
    if get_language() else
    """
    Process text files with awk (supports column extraction, condition filtering, local/remote execution)
    
    Parameters:
        -target: Target host IP/hostname, None for localhost (127.0.0.1)
        -file_path: Target file path (required, e.g. "/etc/passwd" or "/var/log/access.log")
        -script: awk script (required, example: "'{print $1,$3}'" extract column 1&3; "'$3>100 {print $0}'" filter rows where column3>100)
        -options: Optional awk parameters (example: "-F:" set delimiter to colon; "-v OFS=," set output delimiter to comma)
    
    Returns:
        -success: Execution result (True=success, False=failure)
        -message: Execution status/error prompt (auto-switch between Chinese/English)
        -result: List of awk processing results (one element per line, empty list if no result)
        -target: Actual target host IP/hostname for execution
    """
)
def file_awk_tool(
    target: Optional[str] = None,
    file_path: str = "",
    script: str = "",
    options: str = ""
) -> Dict:
    is_zh = get_language()
    # 标准化目标主机：None→本地（127.0.0.1），非空则去空格
    target_host = target.strip() if (target and isinstance(target, str)) else "127.0.0.1"
    # 初始化返回结果结构
    result = {
        "success": False,
        "message": "",
        "result": [],
        "target": target_host
    }

    # -------------------------- 1. 基础参数校验 --------------------------
    # 校验文件路径非空
    if not file_path.strip():
        result["message"] = "文件路径不能为空，请传入有效的文件路径（如\"/etc/passwd\"）" if is_zh else "File path cannot be empty, please pass a valid path (e.g. \"/etc/passwd\")"
        logger.warning(result["message"])
        return result
    # 校验awk脚本非空
    if not script.strip():
        result["message"] = "awk脚本不能为空，请传入有效的处理逻辑（如\"'{print $1,$3}'\"）" if is_zh else "awk script cannot be empty, please pass valid logic (e.g. \"'{print $1,$3}'\")"
        logger.warning(result["message"])
        return result

    # -------------------------- 2. 构建awk命令 --------------------------
    # 处理可选参数（去前后空格，避免多余空格导致命令错误）
    options_clean = options.strip()
    # 拼接命令：awk [选项] [脚本] [文件路径]
    awk_cmd = f"awk {options_clean} {script.strip()} {file_path.strip()}"
    logger.info(f"待执行awk命令：{awk_cmd}（目标主机：{target_host}）")

    # -------------------------- 3. 本地执行逻辑（127.0.0.1） --------------------------
    if target_host == "127.0.0.1":
        try:
            # 执行本地命令：捕获stdout，将stderr重定向到stdout（统一处理错误）
            output = subprocess.check_output(
                awk_cmd,
                shell=True,
                text=True,
                stderr=subprocess.STDOUT  # 把错误输出也捕获到output中
            )
            # 执行成功：处理结果（空输出→空列表，非空→按行分割）
            result["success"] = True
            result["result"] = output.strip().split("\n") if output.strip() else []
            result["message"] = f"本地awk处理成功（文件：{file_path.strip()}），共返回{len(result['result'])}行结果" if is_zh else f"Local awk processing succeeded (file: {file_path.strip()}), returned {len(result['result'])} lines"
            logger.info(result["message"])
        except subprocess.CalledProcessError as e:
            # awk执行失败（如文件不存在、脚本语法错误）
            result["message"] = f"本地awk执行失败：{e.output.strip()}" if is_zh else f"Local awk execution failed: {e.output.strip()}"
            logger.error(result["message"])
        except Exception as e:
            # 其他异常（如权限不足）
            result["message"] = f"本地处理异常：{str(e)}" if is_zh else f"Local processing exception: {str(e)}"
            logger.error(result["message"])
        finally:
            return result

    # -------------------------- 4. 远程执行逻辑（非127.0.0.1） --------------------------
    # 4.1 获取远程认证配置
    remote_auth = get_remote_auth(target_host)
    if not remote_auth:
        result["message"] = f"未找到远程主机（{target_host}）的认证配置，请检查配置文件中的remote_hosts" if is_zh else f"Authentication config for remote host ({target_host}) not found, check remote_hosts in config"
        logger.error(result["message"])
        return result
    # 校验用户名/密码非空（避免无效连接）
    if not (remote_auth.get("username") and remote_auth.get("password")):
        result["message"] = f"远程主机（{target_host}）的认证配置缺失用户名或密码，无法建立SSH连接" if is_zh else f"Remote host ({target_host}) auth config lacks username/password, cannot establish SSH connection"
        logger.error(result["message"])
        return result

    # 4.2 建立SSH连接并执行命令
    ssh_conn: Optional[paramiko.SSHClient] = None
    try:
        # 初始化SSH客户端
        ssh_conn = paramiko.SSHClient()
        # 自动接受未知主机密钥（避免首次连接时手动确认）
        ssh_conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        # 建立SSH连接（超时10秒，避免长时间阻塞）
        ssh_conn.connect(
            hostname=remote_auth["host"],
            port=remote_auth["port"],
            username=remote_auth["username"],
            password=remote_auth["password"],
            timeout=10,
            banner_timeout=10  # 适配慢网络环境，避免banner超时
        )
        logger.info(f"已成功建立与远程主机（{target_host}）的SSH连接")

        # 执行awk命令
        stdin, stdout, stderr = ssh_conn.exec_command(awk_cmd)
        # 读取输出（解码为UTF-8，处理中文乱码）
        stdout_msg = stdout.read().decode("utf-8", errors="replace").strip()
        stderr_msg = stderr.read().decode("utf-8", errors="replace").strip()

        # 4.3 处理执行结果
        if stderr_msg:
            # 有错误输出（如文件不存在、脚本错误）
            result["message"] = f"远程awk执行失败：{stderr_msg}" if is_zh else f"Remote awk execution failed: {stderr_msg}"
            logger.error(result["message"])
        else:
            # 执行成功：处理结果列表
            result["success"] = True
            result["result"] = stdout_msg.split("\n") if stdout_msg else []
            result["message"] = f"远程awk处理成功（主机：{target_host}，文件：{file_path.strip()}），共返回{len(result['result'])}行结果" if is_zh else f"Remote awk processing succeeded (host: {target_host}, file: {file_path.strip()}), returned {len(result['result'])} lines"
            logger.info(result["message"])

    except paramiko.AuthenticationException:
        # SSH认证失败（用户名/密码错误）
        result["message"] = f"远程主机（{target_host}）SSH认证失败，请检查用户名或密码" if is_zh else f"SSH authentication failed for remote host ({target_host}), check username/password"
        logger.error(result["message"])
    except TimeoutError:
        # 连接超时（网络不通或主机未在线）
        result["message"] = f"远程主机（{target_host}）SSH连接超时，请检查网络连通性或主机状态" if is_zh else f"SSH connection timed out for remote host ({target_host}), check network or host status"
        logger.error(result["message"])
    except Exception as e:
        # 其他远程异常（如SSH服务未启动）
        result["message"] = f"远程处理异常：{str(e)}" if is_zh else f"Remote processing exception: {str(e)}"
        logger.error(result["message"])
    finally:
        # 确保SSH连接关闭（避免资源泄漏）
        if ssh_conn:
            ssh_transport = ssh_conn.get_transport()
            if ssh_transport and ssh_transport.is_active():
                ssh_conn.close()
                logger.info(f"已关闭与远程主机（{target_host}）的SSH连接")
        return result
    
@mcp.tool(
    name="file_sort_tool" if get_language() else "file_sort_tool",
    description="""
    对文本文件进行排序（支持按列、升序/降序、去重等，本地/远程均支持）
    
    参数:
        -target: 目标主机IP/hostname，None表示本地（127.0.0.1）
        -file_path: 目标文件路径（必填，如"/tmp/logs.txt"）
        -options: sort可选参数（示例：
            "-n"按数字排序；"-k3"按第3列排序；
            "-r"降序排列；"-u"去重后排序；
            "-t,"指定逗号为分隔符）
        -output_file: 排序结果输出路径（可选，默认不保存到文件，仅返回结果）
    
    返回:
        -success: 执行结果（True=成功，False=失败）
        -message: 执行状态描述/错误提示（根据语言配置自动切换）
        -result: 排序结果列表（output_file为空时返回，每行一个元素）
        -target: 实际执行的目标主机
    """
    if get_language() else
    """
    Sort text files (supports column-based sorting, ascending/descending, deduplication, local/remote)
    
    Parameters:
        -target: Target host IP/hostname, None for localhost (127.0.0.1)
        -file_path: Target file path (required, e.g. "/tmp/logs.txt")
        -options: Optional sort parameters (examples:
            "-n" numeric sort; "-k3" sort by 3rd column;
            "-r" reverse order; "-u" unique then sort;
            "-t," set comma as delimiter)
        -output_file: Output path for sorted results (optional, default returns in result without saving)
    
    Returns:
        -success: Execution result (True=success, False=failure)
        -message: Execution status/error prompt (auto-switch language)
        -result: List of sorted results (returned if output_file is empty, one element per line)
        -target: Actual target host for execution
    """
)
def file_sort_tool(
    target: Optional[str] = None,
    file_path: str = "",
    options: str = "",
    output_file: str = ""
) -> Dict:
    is_zh = get_language()
    # 标准化目标主机：None→本地，非空则去空格
    target_host = target.strip() if (target and isinstance(target, str)) else "127.0.0.1"
    # 初始化返回结果结构
    result = {
        "success": False,
        "message": "",
        "result": [],
        "target": target_host
    }

    # -------------------------- 1. 参数校验 --------------------------
    if not file_path.strip():
        result["message"] = "文件路径不能为空，请提供有效的文件路径" if is_zh else "File path cannot be empty, please provide a valid path"
        logger.warning(result["message"])
        return result

    # -------------------------- 2. 构建sort命令 --------------------------
    options_clean = options.strip()
    if output_file.strip():
        # 结果输出到指定文件（使用-o参数）
        sort_cmd = f"sort {options_clean} {file_path.strip()} -o {output_file.strip()}"
    else:
        # 结果输出到stdout（用于返回结果列表）
        sort_cmd = f"sort {options_clean} {file_path.strip()}"
    logger.info(f"待执行sort命令：{sort_cmd}（目标主机：{target_host}）")

    # -------------------------- 3. 本地执行逻辑 --------------------------
    if target_host == "127.0.0.1":
        try:
            # 执行本地命令，捕获输出（含错误）
            output = subprocess.check_output(
                sort_cmd,
                shell=True,
                text=True,
                stderr=subprocess.STDOUT
            )
            # 执行成功处理
            result["success"] = True
            if output_file.strip():
                # 结果保存到文件的场景
                result["message"] = f"本地排序完成，结果已保存至：{output_file.strip()}" if is_zh else f"Local sort completed, result saved to: {output_file.strip()}"
            else:
                # 结果返回的场景
                result["result"] = output.strip().split("\n") if output.strip() else []
                result["message"] = f"本地排序完成，共返回{len(result['result'])}行数据" if is_zh else f"Local sort completed, returned {len(result['result'])} lines"
            logger.info(result["message"])
        except subprocess.CalledProcessError as e:
            # 命令执行失败（如文件不存在、权限不足）
            result["message"] = f"本地排序失败：{e.output.strip()}" if is_zh else f"Local sort failed: {e.output.strip()}"
            logger.error(result["message"])
        except Exception as e:
            # 其他异常
            result["message"] = f"本地处理异常：{str(e)}" if is_zh else f"Local processing exception: {str(e)}"
            logger.error(result["message"])
        finally:
            return result

    # -------------------------- 4. 远程执行逻辑 --------------------------
    # 4.1 获取远程认证配置
    remote_auth = get_remote_auth(target_host)
    if not remote_auth:
        result["message"] = f"未找到远程主机（{target_host}）的认证配置" if is_zh else f"Authentication config for remote host ({target_host}) not found"
        logger.error(result["message"])
        return result
    if not (remote_auth.get("username") and remote_auth.get("password")):
        result["message"] = f"远程主机（{target_host}）的认证信息不完整（缺少用户名或密码）" if is_zh else f"Remote host ({target_host}) auth info incomplete (missing username/password)"
        logger.error(result["message"])
        return result

    # 4.2 建立SSH连接并执行命令
    ssh_conn: Optional[paramiko.SSHClient] = None
    try:
        # 初始化SSH客户端
        ssh_conn = paramiko.SSHClient()
        ssh_conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # 自动接受未知密钥
        # 建立连接（超时10秒）
        ssh_conn.connect(
            hostname=remote_auth["host"],
            port=remote_auth["port"],
            username=remote_auth["username"],
            password=remote_auth["password"],
            timeout=10,
            banner_timeout=10
        )
        logger.info(f"已成功连接远程主机：{target_host}")

        # 执行sort命令
        stdin, stdout, stderr = ssh_conn.exec_command(sort_cmd)
        stdout_msg = stdout.read().decode("utf-8", errors="replace").strip()
        stderr_msg = stderr.read().decode("utf-8", errors="replace").strip()

        # 4.3 处理执行结果
        if stderr_msg:
            # 命令执行出错
            result["message"] = f"远程排序失败：{stderr_msg}" if is_zh else f"Remote sort failed: {stderr_msg}"
            logger.error(result["message"])
        else:
            # 执行成功
            result["success"] = True
            if output_file.strip():
                result["message"] = f"远程排序完成，结果已保存至：{output_file.strip()}（主机：{target_host}）" if is_zh else f"Remote sort completed, result saved to: {output_file.strip()} (host: {target_host})"
            else:
                result["result"] = stdout_msg.split("\n") if stdout_msg else []
                result["message"] = f"远程排序完成，共返回{len(result['result'])}行数据（主机：{target_host}）" if is_zh else f"Remote sort completed, returned {len(result['result'])} lines (host: {target_host})"
            logger.info(result["message"])

    except paramiko.AuthenticationException:
        result["message"] = f"远程主机（{target_host}）SSH认证失败，请检查用户名和密码" if is_zh else f"SSH authentication failed for {target_host}, check username/password"
        logger.error(result["message"])
    except TimeoutError:
        result["message"] = f"远程主机（{target_host}）连接超时，请检查网络或主机状态" if is_zh else f"Connection to {target_host} timed out, check network or host status"
        logger.error(result["message"])
    except Exception as e:
        result["message"] = f"远程处理异常：{str(e)}" if is_zh else f"Remote processing exception: {str(e)}"
        logger.error(result["message"])
    finally:
        # 确保SSH连接关闭
        if ssh_conn:
            transport = ssh_conn.get_transport()
            if transport and transport.is_active():
                ssh_conn.close()
                logger.info(f"已关闭与{target_host}的SSH连接")
        return result
    
@mcp.tool(
    name="file_unique_tool" if get_language() else "file_unique_tool",
    description="""
    对文本文件进行去重处理（通常与sort配合使用，本地/远程均支持）
    
    参数:
        -target: 目标主机IP/hostname，None表示本地
        -file_path: 目标文件路径（必填，如"/tmp/duplicates.txt"）
        -options: unique可选参数（示例：
            "-u"仅显示唯一行；"-d"仅显示重复行；
            "-c"显示每行出现的次数；"-i"忽略大小写）
        -output_file: 去重结果输出路径（可选，默认不保存到文件）
    
    返回:
        -success: 执行结果（True/False）
        -message: 执行信息/错误提示
        -result: 去重结果列表（output_file为空时返回）
        -target: 执行目标主机
    """
    if get_language() else
    """
    Deduplicate text files (usually used with sort, supports local/remote execution)
    
    Parameters:
        -target: Target host IP/hostname, None for localhost
        -file_path: Target file path (required, e.g. "/tmp/duplicates.txt")
        -options: Optional unique parameters (examples:
            "-u" show only unique lines; "-d" show only duplicate lines;
            "-c" show count of each line; "-i" ignore case)
        -output_file: Output path for deduplicated results (optional, default returns in result)
    
    Returns:
        -success: Execution result (True/False)
        -message: Execution info/error prompt
        -result: List of deduplicated results (returned if output_file is empty)
        -target: Target host for execution
    """
)
def file_unique_tool(
    target: Optional[str] = None,
    file_path: str = "",
    options: str = "",
    output_file: str = ""
) -> Dict:
    is_zh = get_language()
    target_host = target.strip() if (target and isinstance(target, str)) else "127.0.0.1"
    result = {
        "success": False,
        "message": "",
        "result": [],
        "target": target_host
    }

    # 1. 参数校验
    if not file_path.strip():
        result["message"] = "文件路径不能为空" if is_zh else "File path cannot be empty"
        return result

    # 2. 构建unique命令
    options_clean = options.strip()
    # 注意：unique通常需要先排序，这里保留原始命令，由用户决定是否配合sort
    if output_file.strip():
        unique_cmd = f"uniq {options_clean} {file_path.strip()} {output_file.strip()}"
    else:
        unique_cmd = f"uniq {options_clean} {file_path.strip()}"
    logger.info(f"待执行uniq命令：{unique_cmd}（目标：{target_host}）")

    # 3. 本地执行
    if target_host == "127.0.0.1":
        try:
            output = subprocess.check_output(
                unique_cmd, shell=True, text=True, stderr=subprocess.STDOUT
            )
            result["success"] = True
            if output_file.strip():
                result["message"] = f"本地去重完成，结果已保存至：{output_file.strip()}" if is_zh else f"Local deduplication completed, result saved to: {output_file.strip()}"
            else:
                result["result"] = output.strip().split("\n") if output.strip() else []
                result["message"] = f"本地去重完成，共返回{len(result['result'])}行数据" if is_zh else f"Local deduplication completed, returned {len(result['result'])} lines"
        except subprocess.CalledProcessError as e:
            result["message"] = f"本地去重失败：{e.output.strip()}" if is_zh else f"Local deduplication failed: {e.output.strip()}"
        except Exception as e:
            result["message"] = f"本地处理异常：{str(e)}" if is_zh else f"Local processing exception: {str(e)}"
        finally:
            return result

    # 4. 远程执行
    remote_auth = get_remote_auth(target_host)
    if not remote_auth or not (remote_auth["username"] and remote_auth["password"]):
        result["message"] = "远程认证配置缺失" if is_zh else "Remote auth config missing"
        return result

    ssh_conn: Optional[paramiko.SSHClient] = None
    try:
        ssh_conn = paramiko.SSHClient()
        ssh_conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_conn.connect(**remote_auth, timeout=10)
        logger.info(f"已连接远程主机：{target_host}")

        stdin, stdout, stderr = ssh_conn.exec_command(unique_cmd)
        stdout_msg = stdout.read().decode("utf-8", errors="replace").strip()
        stderr_msg = stderr.read().decode("utf-8", errors="replace").strip()

        if stderr_msg:
            result["message"] = f"远程去重失败：{stderr_msg}" if is_zh else f"Remote deduplication failed: {stderr_msg}"
        else:
            result["success"] = True
            if output_file.strip():
                result["message"] = f"远程去重完成，结果已保存至：{output_file.strip()}（主机：{target_host}）" if is_zh else f"Remote deduplication completed, result saved to: {output_file.strip()} (host: {target_host})"
            else:
                result["result"] = stdout_msg.split("\n") if stdout_msg else []
                result["message"] = f"远程去重完成，共返回{len(result['result'])}行数据（主机：{target_host}）" if is_zh else f"Remote deduplication completed, returned {len(result['result'])} lines (host: {target_host})"
    except Exception as e:
        result["message"] = f"远程处理异常：{str(e)}" if is_zh else f"Remote processing exception: {str(e)}"
    finally:
        if ssh_conn:
            transport = ssh_conn.get_transport()
            if transport and transport.is_active():
                ssh_conn.close()
        return result


@mcp.tool(
    name="file_echo_tool" if get_language() else "file_echo_tool",
    description="""
    向文件写入内容（支持创建文件、追加内容，本地/远程均支持）
    
    参数:
        -target: 目标主机IP/hostname，None表示本地
        -content: 要写入的内容（必填，如"Hello World"）
        -file_path: 目标文件路径（必填，如"/tmp/message.txt"）
        -append: 是否追加内容（True=追加，False=覆盖，默认False）
    
    返回:
        -success: 执行结果（True/False）
        -message: 执行信息/错误提示
        -target: 执行目标主机
        -file_path: 实际写入的文件路径
    """
    if get_language() else
    """
    Write content to file (supports file creation, appending content, local/remote execution)
    
    Parameters:
        -target: Target host IP/hostname, None for localhost
        -content: Content to write (required, e.g. "Hello World")
        -file_path: Target file path (required, e.g. "/tmp/message.txt")
        -append: Whether to append content (True=append, False=overwrite, default False)
    
    Returns:
        -success: Execution result (True/False)
        -message: Execution info/error prompt
        -target: Target host for execution
        -file_path: Actual file path written to
    """
)
def file_echo_tool(
    target: Optional[str] = None,
    content: str = "",
    file_path: str = "",
    append: bool = False
) -> Dict:
    is_zh = get_language()
    target_host = target.strip() if (target and isinstance(target, str)) else "127.0.0.1"
    result = {
        "success": False,
        "message": "",
        "target": target_host,
        "file_path": file_path.strip()
    }

    # 1. 参数校验
    if not content.strip():
        result["message"] = "写入内容不能为空" if is_zh else "Content to write cannot be empty"
        return result
    if not file_path.strip():
        result["message"] = "文件路径不能为空" if is_zh else "File path cannot be empty"
        return result

    # 2. 构建echo命令（处理特殊字符转义）
    # 对内容中的单引号进行转义，避免命令语法错误
    escaped_content = content.replace("'", "'\\''")
    # 选择重定向符号（覆盖>或追加>>）
    redirect = ">>" if append else ">"
    echo_cmd = f"echo '{escaped_content}' {redirect} {file_path.strip()}"
    logger.info(f"待执行echo命令：{echo_cmd}（目标：{target_host}）")

    # 3. 本地执行
    if target_host == "127.0.0.1":
        try:
            # 执行命令（无需捕获stdout，因为结果写入文件）
            subprocess.check_output(
                echo_cmd,
                shell=True,
                text=True,
                stderr=subprocess.STDOUT
            )
            action = "追加" if append else "写入"
            result["success"] = True
            result["message"] = f"本地{action}成功，文件路径：{file_path.strip()}" if is_zh else f"Local {('appended' if append else 'written')} successfully, file path: {file_path.strip()}"
        except subprocess.CalledProcessError as e:
            result["message"] = f"本地{action}失败：{e.output.strip()}" if is_zh else f"Local {('append' if append else 'write')} failed: {e.output.strip()}"
        except Exception as e:
            result["message"] = f"本地处理异常：{str(e)}" if is_zh else f"Local processing exception: {str(e)}"
        finally:
            return result

    # 4. 远程执行
    remote_auth = get_remote_auth(target_host)
    if not remote_auth or not (remote_auth["username"] and remote_auth["password"]):
        result["message"] = "远程认证配置缺失" if is_zh else "Remote auth config missing"
        return result

    ssh_conn: Optional[paramiko.SSHClient] = None
    try:
        ssh_conn = paramiko.SSHClient()
        ssh_conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_conn.connect(**remote_auth, timeout=10)
        logger.info(f"已连接远程主机：{target_host}")

        # 执行echo命令
        stdin, stdout, stderr = ssh_conn.exec_command(echo_cmd)
        # 读取错误输出
        stderr_msg = stderr.read().decode("utf-8", errors="replace").strip()

        if stderr_msg:
            action = "追加" if append else "写入"
            result["message"] = f"远程{action}失败：{stderr_msg}" if is_zh else f"Remote {('append' if append else 'write')} failed: {stderr_msg}"
        else:
            action = "追加" if append else "写入"
            result["success"] = True
            result["message"] = f"远程{action}成功（主机：{target_host}），文件路径：{file_path.strip()}" if is_zh else f"Remote {('appended' if append else 'written')} successfully (host: {target_host}), file path: {file_path.strip()}"
    except Exception as e:
        result["message"] = f"远程处理异常：{str(e)}" if is_zh else f"Remote processing exception: {str(e)}"
    finally:
        if ssh_conn:
            transport = ssh_conn.get_transport()
            if transport and transport.is_active():
                ssh_conn.close()
        return result


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='sse')