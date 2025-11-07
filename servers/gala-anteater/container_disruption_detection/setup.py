from glob import glob

from setuptools import setup, find_packages
import os 

# ser = "/usr/lib/systemd/system/systrac-mcpserver.service"
ser = "/usr/lib/systemd/system/container-disruption-detection-mcpserver.service"
if os.path.isfile(ser):
    os.remove(ser)
setup(
    name="container_disruption_detection_mcp",
    version="1.0.0",
    author="zimeng li",
    author_email="lizimeng9@huawei.com",
    description="MCP Server for Container Disruption Detection for AI Model Training and Inference",
    url="https://gitee.com/openeuler/gala-anteater",
    keywords=["Container Disruption Detection", "Group Compare", "AI Model", "MCP Server"],
    packages=find_packages(where=".", exclude=("tests", "tests.*")),
    data_files=[
        ('/etc/anteater/config/', glob('config/ftp_config.json')),
        ('/usr/lib/systemd/system/', glob('service/*')),
    ],
    install_requires=[
        "anteater",
        "paramiko",
        "fastapi"
    ],
    entry_points={
        "console_scripts": [
            "container-disruption-detection-mcp=container_disruption_detection_mcp.mcp_server:main"
        ]
    }
)