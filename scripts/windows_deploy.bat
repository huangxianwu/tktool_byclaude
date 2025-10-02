@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ================================================================
echo TK Tool Windows 一键部署脚本
echo ================================================================
echo.

:: 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo ✗ 错误: 未找到Python，请先安装Python 3.8+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✓ Python 已安装
python --version

:: 检查pip是否可用
pip --version >nul 2>&1
if errorlevel 1 (
    echo ✗ 错误: pip 不可用
    pause
    exit /b 1
)

echo ✓ pip 已安装
echo.

:: 检查是否在正确的目录
if not exist "config.py" (
    echo ✗ 错误: 请在项目根目录运行此脚本
    echo 当前目录: %CD%
    pause
    exit /b 1
)

echo ✓ 项目目录检查通过
echo 当前目录: %CD%
echo.

:: 安装依赖
echo ================================================================
echo 安装Python依赖包...
echo ================================================================
echo.

pip install -r requirements.txt
if errorlevel 1 (
    echo ✗ 依赖安装失败
    pause
    exit /b 1
)

echo ✓ 依赖安装完成
echo.

:: 初始化数据库
echo ================================================================
echo 初始化数据库...
echo ================================================================
echo.

python scripts/windows_db_init.py
if errorlevel 1 (
    echo ✗ 数据库初始化失败
    pause
    exit /b 1
)

echo ✓ 数据库初始化完成
echo.

:: 询问是否需要迁移现有数据库
echo ================================================================
echo 数据库迁移选项
echo ================================================================
echo.
echo 如果您有现有的数据库文件需要迁移，请选择 Y
echo 如果这是全新安装，请选择 N
echo.
set /p migrate_choice="是否需要迁移现有数据库? (Y/N): "

if /i "!migrate_choice!"=="Y" (
    echo.
    echo 开始数据库迁移...
    python scripts/migrate_database.py
    if errorlevel 1 (
        echo ✗ 数据库迁移失败
        pause
        exit /b 1
    )
    echo ✓ 数据库迁移完成
)

echo.

:: 创建启动脚本
echo ================================================================
echo 创建启动脚本...
echo ================================================================

echo @echo off > start_server.bat
echo chcp 65001 ^>nul >> start_server.bat
echo echo TK Tool 服务器启动中... >> start_server.bat
echo echo. >> start_server.bat
echo echo 服务器地址: http://localhost:8080 >> start_server.bat
echo echo 按 Ctrl+C 停止服务器 >> start_server.bat
echo echo. >> start_server.bat
echo python run.py >> start_server.bat
echo pause >> start_server.bat

echo ✓ 启动脚本已创建: start_server.bat
echo.

:: 创建停止脚本
echo @echo off > stop_server.bat
echo echo 正在停止 TK Tool 服务器... >> stop_server.bat
echo taskkill /f /im python.exe 2^>nul >> stop_server.bat
echo echo 服务器已停止 >> stop_server.bat
echo pause >> stop_server.bat

echo ✓ 停止脚本已创建: stop_server.bat
echo.

:: 部署完成
echo ================================================================
echo 部署完成!
echo ================================================================
echo.
echo 使用方法:
echo 1. 启动服务器: 双击 start_server.bat 或运行 python run.py
echo 2. 访问应用: http://localhost:5000
echo 3. 停止服务器: 双击 stop_server.bat 或按 Ctrl+C
echo.
echo 重要文件:
echo - 数据库: instance/app.db
echo - 配置: config.py
echo - 日志: 控制台输出
echo.
echo 故障排除:
echo - 如果端口5000被占用，请修改 run.py 中的端口号
echo - 如果数据库错误，请运行: python scripts/windows_db_init.py
echo - 如果依赖错误，请运行: pip install -r requirements.txt
echo.

:: 询问是否立即启动
set /p start_choice="是否立即启动服务器? (Y/N): "
if /i "!start_choice!"=="Y" (
    echo.
    echo 启动服务器...
    echo 按 Ctrl+C 停止服务器
    echo.
    python run.py
)

echo.
echo 部署脚本执行完成
pause