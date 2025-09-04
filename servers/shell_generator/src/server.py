from typing import Union, List, Dict
import platform
import os
import paramiko
import yaml
import datetime
import subprocess
from typing import Any, Dict
import psutil
import socket
from datetime import datetime
from mcp.server import FastMCP
import telnetlib
from mcp_center.config.public.base_config_loader import LanguageEnum
from config.private.cmd_generator.config_loader import CMDGeneratorConfig
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
import re


class LLM:
    def __init__(self, model_name, openai_api_base, openai_api_key, request_timeout, max_tokens, temperature):
        self.client = ChatOpenAI(model_name=model_name,
                                 openai_api_base=openai_api_base,
                                 openai_api_key=openai_api_key,
                                 request_timeout=request_timeout,
                                 max_tokens=max_tokens,
                                 temperature=temperature)

    def assemble_chat(self, system_call, user_call):
        chat = []
        chat.append(SystemMessage(content=system_call))
        chat.append(HumanMessage(content=user_call))
        return chat

    async def chat_with_model(self, system_call, user_call):
        chat = self.assemble_chat(system_call, user_call)
        response = await self.client.ainvoke(chat)
        return response.content


mcp = FastMCP("CMD MCP Server", host="0.0.0.0", port=CMDGeneratorConfig().get_config().private_config.port)


@mcp.tool(
    name="cmd_generator_tool"
    if CMDGeneratorConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "cmd_generator_tool",
    description='''
    根据用户的需求，生成相应的shell命令
    1. 输入值如下：
        - host:远程主机名称或IP地址，若不提供则表示获取本机
        - goal:用户的需求，必须提供
    '''
    if CMDGeneratorConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    '''
    Generate corresponding shell commands based on user needs
    1. The input values are as follows:
        - host: Remote host name or IP address, if not provided, it means to get
            the local machine
        - goal: User's needs, must be provided
    '''
)
async def cmd_generator_tool(host: Union[str, None] = None, goal: str = "") -> str:
    """
    根据用户的需求，生成相应的shell命令
    1. 输入值如下：
        - host:远程主机名称或IP地址，若不提供则表示获取本机
        - goal:用户的需求，必须提供
    """
    if not goal:
        return "请提供用户需求"
    if host:
        host_config = None
        for remote in CMDGeneratorConfig().get_config().public_config.remote_hosts:
            if remote.name == host or remote.host == host:
                host_config = remote
                break
        if not host_config:
            return f"未找到远程主机{host}的信息，请检查配置文件"
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=host_config.host,
            port=host_config.port,
            username=host_config.username,
            password=host_config.password
        )
        stdin, stdout, stderr = ssh.exec_command("uname -a")
        remote_os_info = stdout.read().decode().strip()
        stdin, stdout, stderr = ssh.exec_command("cat /etc/os-release")
        remote_os_release = stdout.read().decode().strip()
        remote_os_name = ""
        for line in remote_os_release.split("\n"):
            if line.startswith("PRETTY_NAME"):
                remote_os_name = line.split("=")[1].strip().strip('"')
                break
        stdin, stdout, stderr = ssh.exec_command("uptime -p")
        remote_uptime = stdout.read().decode().strip()
        stdin, stdout, stderr = ssh.exec_command("who")
        remote_users = stdout.read().decode().strip()
        stdin, stdout, stderr = ssh.exec_command("df -h /")
        remote_disk = stdout.read().decode().strip()
        stdin, stdout, stderr = ssh.exec_command("free -h")
        remote_memory = stdout.read().decode().strip()
        stdin, stdout, stderr = ssh.exec_command("ps -eo pid,ppid,cmd,%mem,%cpu --sort=-%mem | head -n 6")
        remote_processes = stdout.read().decode().strip()
        ssh.close()
        system_call = f"""
        你是一个Linux系统管理员，当前远程主机的系统信息如下：
        系统信息: {remote_os_info}
        系统发行版: {remote_os_name}
        运行时间: {remote_uptime}
        当前登录用户: {remote_users}
        根分区使用情况: {remote_disk}
        内存使用情况: {remote_memory}
        内存使用率最高的前5个进程: {remote_processes}
        请根据用户的需求，生成相应的shell命令，注意：
        1. 只返回命令，不要任何解释
        命令按照以下形式返回：
        ```bash
        {{
            "command": "命令字符串"
        }}
        ```
        """
        user_call = f"用户的需求：{goal}，请给出相应的shell命令"
    else:
        system_call = f"""
        你是一个Linux系统管理员，当前主机的系统信息如下：
        系统信息: {platform.uname()}
        系统发行版: {platform.platform()}
        运行时间: {datetime.now() - datetime.fromtimestamp(psutil.boot_time())}
        当前登录用户: {', '.join([user.name for user in psutil.users()])}
        根分区使用情况: {subprocess.getoutput('df -h /')}
        内存使用情况: {subprocess.getoutput('free -h')}
        内存使用率最高的前5个进程: {subprocess.getoutput('ps -eo pid,ppid,cmd,%mem,%cpu --sort=-%mem | head -n 6')}
        请根据用户的需求，生成相应的shell命令，注意：
        1. 只返回命令，不要任何解释
        命令按照以下形式返回：
        ```bash
        {{
            "command": "命令字符串"
        }}
        ```
        """
        user_call = f"用户的需求：{goal}，请给出相应的shell命令"
    llm = LLM(
        model_name=CMDGeneratorConfig().get_config().public_config.llm_model,
        openai_api_base=CMDGeneratorConfig().get_config().public_config.llm_remote,
        openai_api_key=CMDGeneratorConfig().get_config().public_config.llm_api_key,
        request_timeout=60,
        max_tokens=CMDGeneratorConfig().get_config().public_config.max_tokens,
        temperature=CMDGeneratorConfig().get_config().public_config.temperature,
    )
    result = await llm.chat_with_model(system_call, user_call)
    # 提取代码块中的内容
    code_block_pattern = r"```bash(.*?)```"
    match = re.search(code_block_pattern, result, re.DOTALL)
    if match:
        code_block = match.group(1).strip()
        try:
            command_dict = yaml.safe_load(code_block)
            if isinstance(command_dict, dict) and "command" in command_dict:
                return command_dict["command"]
            else:
                return "未能提取到有效的命令，请检查需求描述是否清晰。"
        except yaml.YAMLError:
            return "解析命令时出错，请检查需求描述是否清晰。"


@mcp.tool(
    name="cmd_executor_tool"
    if CMDGeneratorConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    "cmd_executor_tool",
    description='''
    在远程主机上执行shell命令
    1. 输入值如下：
        - host:远程主机名称或IP地址，若不提供则表示获取
        - command:需要执行的shell命令，必须提供
    '''
    if CMDGeneratorConfig().get_config().public_config.language == LanguageEnum.ZH
    else
    '''
    Execute shell commands on a remote host
    1. The input values are as follows:
        - host: Remote host name or IP address, if not provided, it means to get
            the local machine
        - command: The shell command to be executed, must be provided
    '''
)
async def cmd_executor_tool(host: Union[str, None] = None, command: str = "") -> str:
    if not command:
        return "请提供需要执行的命令"
    if host:
        host_config = None
        for remote in CMDGeneratorConfig().get_config().public_config.remote_hosts:
            if remote.name == host or remote.host == host:
                host_config = remote
                break
        if not host_config:
            return f"未找到远程主机{host}的信息，请检查配置文件"
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=host_config.host,
            port=host_config.port,
            username=host_config.username,
            password=host_config.password
        )
        stdin, stdout, stderr = ssh.exec_command(command)
        result = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        ssh.close()
        if error:
            return f"命令执行出错：{error}"
        return result
    else:
        try:
            result = subprocess.getoutput(command)
            return result
        except Exception as e:
            return f"命令执行出错：{str(e)}"
if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='sse')
