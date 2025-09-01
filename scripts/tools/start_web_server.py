#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web服务启动脚本
用于稳定启动和管理泵站优化系统的Web服务
"""

import sys
import subprocess
import time
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def start_server(host="127.0.0.1", port=8000, reload=True, background=False):
    """
    启动Web服务

    Args:
        host (str): 服务器主机地址
        port (int): 服务器端口
        reload (bool): 是否启用热重载
    """
    print("🚀 正在启动Web服务...")
    print(f"📍 地址: http://{host}:{port}")
    print(f"🔄 热重载: {'启用' if reload else '禁用'}")

    # 构建命令
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        host,
        "--port",
        str(port),
    ]

    if reload:
        cmd.append("--reload")

    print(f"📋 启动命令: {' '.join(cmd)}")

    if background:
        # 后台运行服务
        process = subprocess.Popen(
            cmd,
            cwd=str(project_root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        print(f"✅ Web服务已在后台启动 (PID: {process.pid})")
        print(f"📍 访问地址: http://{host}:{port}")
        return 0
    else:
        try:
            # 启动服务
            process = subprocess.Popen(
                cmd,
                cwd=str(project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
            )

            print(f"✅ Web服务已启动 (PID: {process.pid})")
            print("💡 按 Ctrl+C 停止服务")

            # 实时输出日志
            while True:
                output = process.stdout.readline()
                if output:
                    print(output.strip())

                # 检查进程是否还在运行
                if process.poll() is not None:
                    break

            # 获取退出码
            exit_code = process.poll()
            print(f"⏹️  Web服务已停止 (退出码: {exit_code})")
            return exit_code

        except KeyboardInterrupt:
            print("\n⚠️  收到停止信号，正在关闭服务...")
            if "process" in locals():
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
            print("✅ 服务已停止")
            return 0
        except Exception as e:
            print(f"❌ 启动服务时出错: {e}")
            return 1


def check_port_availability(port):
    """
    检查端口是否可用

    Args:
        port (int): 要检查的端口

    Returns:
        bool: 端口是否可用
    """
    import socket

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", port))
        sock.close()
        return True
    except OSError:
        return False


def kill_port_process(port):
    """
    结束占用指定端口的进程

    Args:
        port (int): 端口
    """
    import subprocess

    try:
        # 查找占用端口的进程
        result = subprocess.run(
            ["netstat", "-ano", "|", "findstr", f":{port}"],
            capture_output=True,
            text=True,
            shell=True,
        )

        if result.returncode == 0 and result.stdout:
            lines = result.stdout.strip().split("\n")
            pids = set()
            for line in lines:
                if "LISTENING" in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        pid = parts[-1]
                        if pid.isdigit():
                            pids.add(pid)

            # 结束进程
            for pid in pids:
                try:
                    subprocess.run(
                        ["taskkill", "/PID", pid, "/F"], capture_output=True, check=True
                    )
                    print(f"✅ 已结束进程 PID {pid}")
                except subprocess.CalledProcessError:
                    print(f"⚠️  无法结束进程 PID {pid}")

        return len(pids) > 0
    except Exception as e:
        print(f"⚠️  检查端口占用时出错: {e}")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="启动泵站优化系统Web服务")
    parser.add_argument("--host", default="127.0.0.1", help="服务器主机地址")
    parser.add_argument("--port", type=int, default=8000, help="服务器端口")
    parser.add_argument("--no-reload", action="store_true", help="禁用热重载")
    parser.add_argument(
        "--force", action="store_true", help="强制启动，自动结束占用端口的进程"
    )
    parser.add_argument("--background", action="store_true", help="后台运行服务")

    args = parser.parse_args()

    # 检查端口可用性
    if not check_port_availability(args.port):
        print(f"⚠️  端口 {args.port} 已被占用")
        if args.force:
            print("🔧 正在尝试结束占用端口的进程...")
            if kill_port_process(args.port):
                # 等待一会儿让系统释放端口
                time.sleep(2)

                # 再次检查端口
                if not check_port_availability(args.port):
                    print(f"⚠️  端口 {args.port} 仍然不可用")
                    return 1
        else:
            print("💡 使用 --force 参数自动结束占用端口的进程")
            return 1

    # 启动服务
    reload = not args.no_reload
    background = hasattr(args, "background") and args.background
    return start_server(args.host, args.port, reload, background)


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
