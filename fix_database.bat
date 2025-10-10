@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo 数据库迁移修复工具
echo ========================================
echo.

:: 检查是否在正确的目录
if not exist "fix_database_migration.py" (
    echo 错误: 找不到 fix_database_migration.py 文件
    echo 请确保在项目根目录运行此脚本
    echo.
    pause
    exit /b 1
)

:: 检查 Python 是否可用
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 Python
    echo 请确保已安装 Python 并添加到 PATH 环境变量
    echo.
    pause
    exit /b 1
)

echo 检测到的 Python 版本:
python --version
echo.

:: 显示菜单
:menu
echo 请选择操作:
echo 1. 检查数据库状态
echo 2. 仅备份数据库
echo 3. 自动修复数据库
echo 4. 强制修复数据库
echo 5. 退出
echo.
set /p choice="请输入选项 (1-5): "

if "%choice%"=="1" goto check_only
if "%choice%"=="2" goto backup_only
if "%choice%"=="3" goto auto_fix
if "%choice%"=="4" goto force_fix
if "%choice%"=="5" goto exit
echo 无效选项，请重新选择
echo.
goto menu

:check_only
echo.
echo 正在检查数据库状态...
python fix_database_migration.py --check-only
echo.
pause
goto menu

:backup_only
echo.
echo 正在备份数据库...
python fix_database_migration.py --backup-only
echo.
pause
goto menu

:auto_fix
echo.
echo 正在自动修复数据库...
echo 这将会:
echo 1. 检查数据库状态
echo 2. 自动备份数据库
echo 3. 尝试修复缺失的字段
echo.
set /p confirm="确认继续? (y/N): "
if /i not "%confirm%"=="y" goto menu

python fix_database_migration.py
if errorlevel 1 (
    echo.
    echo 修复失败，请查看上面的错误信息
) else (
    echo.
    echo 修复成功！
)
echo.
pause
goto menu

:force_fix
echo.
echo 正在强制修复数据库...
echo 警告: 这将强制执行修复，即使数据库看起来正常
echo.
set /p confirm="确认继续? (y/N): "
if /i not "%confirm%"=="y" goto menu

python fix_database_migration.py --force
if errorlevel 1 (
    echo.
    echo 强制修复失败，请查看上面的错误信息
) else (
    echo.
    echo 强制修复成功！
)
echo.
pause
goto menu

:exit
echo.
echo 感谢使用数据库迁移修复工具！
echo.
pause
exit /b 0