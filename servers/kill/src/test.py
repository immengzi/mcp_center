import time
import os
import sys

def main():
    # 打印进程信息，方便获取PID
    pid = os.getpid()
    print(f"测试进程已启动，PID: {pid}")
    print(f"进程描述: 每2秒打印一次信息，可通过 kill {pid} 或暂停工具关闭")
    print("按 Ctrl+C 可直接终止进程")
    
    try:
        # 持续运行，模拟一个工作进程
        count = 0
        while True:
            count += 1
            print(f"进程运行中... (计数: {count}) - PID: {pid}")
            time.sleep(2)  # 每2秒输出一次
    except KeyboardInterrupt:
        print("\n收到终止信号，进程即将退出")
        sys.exit(0)

if __name__ == "__main__":
    main()
