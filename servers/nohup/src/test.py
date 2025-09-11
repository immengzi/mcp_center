#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
nohup工具测试脚本：生成一个持续运行的进程，用于验证后台运行功能
"""
import time
import os
import sys
from datetime import datetime

def main():
    # 打印进程基本信息
    pid = os.getpid()
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"=== 测试进程启动 ===")
    print(f"PID: {pid}")
    print(f"启动时间: {start_time}")
    print(f"工作目录: {os.getcwd()}")
    print(f"输出模式: 每3秒打印一次运行信息")
    print(f"===================")

    try:
        # 持续运行并输出信息（模拟实际工作负载）
        count = 0
        while True:
            count += 1
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{current_time}] 测试进程运行中 - 计数: {count} - PID: {pid}")
            sys.stdout.flush()  # 强制刷新输出，确保日志能实时写入文件
            time.sleep(3)  # 每3秒输出一次

    except KeyboardInterrupt:
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 测试进程被手动中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 测试进程异常: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
