@echo off
REM 地五班项目虚拟环境激活脚本

echo 正在激活Python虚拟环境...
cd /d "d:\Trae\diwuban"
call .venv\Scripts\activate

echo.
echo ===== 地五班项目环境 =====
echo 项目路径: %CD%
python --version
echo 虚拟环境已激活!
echo.
echo 常用命令:
echo   python -m app.cli.main version                    - 检查版本
echo   python -m app.cli.main prepare-dim config/...     - 准备维表
echo   python analyze_db.py                             - 数据库分析
echo   python -m app.cli.main --help                    - 查看帮助
echo ========================
echo.