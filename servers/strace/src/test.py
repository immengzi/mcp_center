#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
strace测试进程：模拟各种文件操作，用于验证strace跟踪工具的功能
"""
import os
import time
import sys
from datetime import datetime

def create_test_file(filename: str):
    """创建测试文件并写入内容"""
    with open(filename, 'w') as f:
        f.write(f"测试文件创建于: {datetime.now()}\n")
        f.write(f"进程PID: {os.getpid()}\n")
    print(f"[文件操作] 创建文件: {filename}")

def read_test_file(filename: str):
    """读取文件内容"""
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            content = f.read(100)  # 读取前100字节
        print(f"[文件操作] 读取文件: {filename} (前100字节)")
        return content
    print(f"[文件操作] 读取失败，文件不存在: {filename}")
    return None

def append_to_file(filename: str):
    """向文件追加内容"""
    if os.path.exists(filename):
        with open(filename, 'a') as f:
            f.write(f"追加内容于: {datetime.now()}\n")
        print(f"[文件操作] 追加内容到: {filename}")
    else:
        print(f"[文件操作] 追加失败，文件不存在: {filename}")

def rename_file(old_name: str, new_name: str):
    """重命名文件"""
    if os.path.exists(old_name):
        os.rename(old_name, new_name)
        print(f"[文件操作] 重命名文件: {old_name} -> {new_name}")
    else:
        print(f"[文件操作] 重命名失败，文件不存在: {old_name}")

def delete_file(filename: str):
    """删除文件"""
    if os.path.exists(filename):
        os.remove(filename)
        print(f"[文件操作] 删除文件: {filename}")
    else:
        print(f"[文件操作] 删除失败，文件不存在: {filename}")

def create_directory(dirname: str):
    """创建目录"""
    if not os.path.exists(dirname):
        os.makedirs(dirname, exist_ok=True)
        print(f"[文件操作] 创建目录: {dirname}")
    else:
        print(f"[文件操作] 目录已存在: {dirname}")

def main():
    # 打印进程基本信息
    pid = os.getpid()
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n=== strace测试进程启动 ===")
    print(f"PID: {pid} (用于strace跟踪)")
    print(f"启动时间: {start_time}")
    print(f"工作目录: {os.getcwd()}")
    print(f"功能: 每5秒执行一轮文件操作（创建、读写、重命名、删除）")
    print(f"按 Ctrl+C 终止进程\n")

    # 测试文件和目录名称
    test_dir = "strace_test_dir"
    test_file = "strace_test_file.txt"
    renamed_file = "strace_test_file_renamed.txt"

    try:
        count = 0
        while True:
            count += 1
            print(f"\n=== 第 {count} 轮文件操作 ===")
            
            # 执行一系列文件操作（覆盖strace主要跟踪的类型）
            create_directory(test_dir)                  # 目录创建 (mkdir)
            create_test_file(os.path.join(test_dir, test_file))  # 文件创建 (open+write)
            read_test_file(os.path.join(test_dir, test_file))     # 文件读取 (open+read)
            append_to_file(os.path.join(test_dir, test_file))     # 文件追加 (open+write)
            rename_file(                                  # 文件重命名 (rename)
                os.path.join(test_dir, test_file),
                os.path.join(test_dir, renamed_file)
            )
            read_test_file(os.path.join(test_dir, renamed_file))   # 读取重命名后的文件
            delete_file(os.path.join(test_dir, renamed_file))      # 文件删除 (unlink)
            
            time.sleep(5)  # 每5秒一轮操作

    except KeyboardInterrupt:
        print(f"\n=== 测试进程被手动终止 (PID: {pid}) ===")
        # 清理测试目录
        if os.path.exists(test_dir):
            for root, dirs, files in os.walk(test_dir, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(test_dir)
            print(f"已清理测试目录: {test_dir}")
        sys.exit(0)
    except Exception as e:
        print(f"\n=== 测试进程异常终止: {str(e)} ===")
        sys.exit(1)

if __name__ == "__main__":
    main()
