@echo off
REM Claude Code CLI 启动脚本（跳过所有权限确认）
REM 使用方法：双击此文件即可启动

echo ====================================
echo  Claude Code CLI (无权限确认模式)
echo ====================================
echo.
echo 正在启动 Claude Code...
echo 工作目录: d:\Augment\diliuban
echo.

cd /d "d:\Augment\diliuban"

REM 使用 --dangerously-skip-permissions 参数跳过所有权限确认
claude-code --dangerously-skip-permissions

pause
