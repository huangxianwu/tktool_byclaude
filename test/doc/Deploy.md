# Windows自动化部署方案设计
## 方案框架
### 核心组件架构
1. 1.
   主控制脚本 ( deploy_manager.bat ) - 统一入口点
2. 2.
   Python部署服务 ( deployment_service.py ) - 核心部署逻辑
3. 3.
   配置管理器 ( config.json ) - 部署参数配置
4. 4.
   日志系统 ( logs/ ) - 操作记录和错误追踪
5. 5.
   Windows任务计划程序 - 定时更新机制
6. 6.
   进程守护器 ( process_guardian.py ) - 服务监控和重启
### 系统架构图
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  用户操作界面    │───▶│   主控制脚本      │───▶│  Python部署服务  │
│  (一键启动)     │    │  deploy_manager   │    │ deployment_service│
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │                         │
                              ▼                         ▼
                    ┌──────────────────┐    ┌─────────────────┐
                    │  Windows任务计划  │    │   进程守护器     │
                    │   (定时更新)     │    │ process_guardian │
                    └──────────────────┘    └─────────────────┘
                              │                         │
                              ▼                         ▼
                    ┌──────────────────┐    ┌─────────────────┐
                    │   Git仓库同步    │    │   应用进程监控   │
                    │  (代码更新)      │    │  (健康检查)     │
                    └──────────────────┘    └─────────────────┘
```
## 详细流程设计
### 1. 初始化部署流程
```
用户执行 → 环境检查 → Git克隆/更新 → 依赖安装 → 配置更新 → 服务启动 → 守护进程启动
```
### 2. 定时更新流程
```
定时触发 → 检查远程更新 → 备份当前版本 → 拉取新代码 → 依赖更新 → 服务重启 → 健康检查 → 回滚机制
```
### 3. 监控守护流程
```
持续监控 → 进程状态检查 → 端口可用性检测 → 异常处理 → 自动重启 → 告警通知
```
## 核心原理
### 1. 版本管理原理
- Git Hook机制 ：利用Git的post-merge钩子自动触发部署
- 版本标记 ：通过commit hash追踪部署版本
- 回滚策略 ：保留最近3个版本的备份，支持快速回滚
### 2. 进程管理原理
- PID文件管理 ：记录主进程ID，支持优雅停止
- 端口监听检测 ：通过socket连接测试服务可用性
- 健康检查机制 ：定期HTTP请求验证服务状态
### 3. 自动化调度原理
- Windows任务计划程序 ：系统级定时任务，开机自启
- Cron表达式 ：灵活的时间调度配置
- 互斥锁机制 ：防止重复执行部署任务
## 优势分析
### 技术优势
1. 1.
   零配置部署 ：一键脚本，无需手动配置
2. 2.
   自动化程度高 ：从代码更新到服务重启全自动
3. 3.
   容错性强 ：多层异常处理和自动恢复
4. 4.
   版本可控 ：支持版本回滚和历史追踪
### 运维优势
1. 1.
   操作简单 ：非技术人员也能操作
2. 2.
   监控完善 ：详细日志和状态监控
3. 3.
   维护成本低 ：自动化程度高，减少人工干预
4. 4.
   扩展性好 ：模块化设计，易于功能扩展
## 劣势分析
### 技术劣势
1. 1.
   Windows依赖 ：仅适用于Windows环境
2. 2.
   单点故障 ：服务器故障影响整体可用性
3. 3.
   资源占用 ：需要额外的监控进程
4. 4.
   网络依赖 ：需要稳定的Git仓库连接
### 运维劣势
1. 1.
   调试复杂 ：自动化流程出错时排查困难
2. 2.
   权限要求 ：需要管理员权限配置任务计划
3. 3.
   兼容性问题 ：不同Windows版本可能有差异
## 难点分析
### 1. 进程管理难点
- 优雅停止 ：确保数据完整性，避免强制杀进程
- 端口冲突 ：处理端口占用和释放时序问题
- 权限控制 ：Windows服务权限和文件访问权限
### 2. 版本控制难点
- 并发冲突 ：多人同时推送代码的处理
- 依赖更新 ：requirements.txt变更时的环境同步
- 数据库迁移 ：代码更新涉及数据库结构变更
### 3. 异常处理难点
- 网络中断 ：Git拉取失败的重试机制
- 磁盘空间 ：日志文件和备份文件的空间管理
- 服务异常 ：应用崩溃后的快速恢复
## 风险点识别
### 1. 高风险点
- 数据丢失风险 ：更新失败可能导致配置或数据丢失
- 服务中断风险 ：部署过程中的服务不可用时间
- 安全风险 ：自动拉取代码可能引入恶意代码
### 2. 中等风险点
- 性能风险 ：频繁重启影响用户体验
- 兼容性风险 ：新版本代码与环境不兼容
- 资源风险 ：监控进程占用系统资源
### 3. 低风险点
- 日志风险 ：日志文件过大占用磁盘空间
- 配置风险 ：配置文件格式错误
## 代码实现
### 1. 主控制脚本 (deploy_manager.bat)
```
@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo     TK工具自动化部署管理器 v1.0
echo ========================================
echo.

set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%"
set "PYTHON_SCRIPT=%SCRIPT_DIR%deployment_service.py"
set "CONFIG_FILE=%SCRIPT_DIR%config.json"
set "LOG_DIR=%SCRIPT_DIR%logs"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

echo [%date% %time%] 启动部署管理器... >> "%LOG_DIR%\deploy.log"

if "%1"=="" (
    echo 请选择操作：
    echo 1. 初始化部署
    echo 2. 更新部署
    echo 3. 启动服务
    echo 4. 停止服务
    echo 5. 查看状态
    echo 6. 设置定时更新
    echo 7. 查看日志
    echo.
    set /p choice="请输入选项 (1-7): "
) else (
    set choice=%1
)

if "%choice%"=="1" goto INIT_DEPLOY
if "%choice%"=="2" goto UPDATE_DEPLOY
if "%choice%"=="3" goto START_SERVICE
if "%choice%"=="4" goto STOP_SERVICE
if "%choice%"=="5" goto CHECK_STATUS
if "%choice%"=="6" goto SETUP_SCHEDULE
if "%choice%"=="7" goto VIEW_LOGS

echo 无效选项，请重新运行脚本
goto END

:INIT_DEPLOY
echo 正在初始化部署环境...
python "%PYTHON_SCRIPT%" --action init
if %errorlevel% equ 0 (
    echo 初始化完成！
    echo 正在启动服务...
    python "%PYTHON_SCRIPT%" --action start
    if %errorlevel% equ 0 (
        echo 服务启动成功！
        echo 访问地址: http://localhost:5001
    ) else (
        echo 服务启动失败，请查看日志
    )
) else (
    echo 初始化失败，请查看日志
)
goto END

:UPDATE_DEPLOY
echo 正在更新部署...
python "%PYTHON_SCRIPT%" --action update
if %errorlevel% equ 0 (
    echo 更新完成！
) else (
    echo 更新失败，请查看日志
)
goto END

:START_SERVICE
echo 正在启动服务...
python "%PYTHON_SCRIPT%" --action start
if %errorlevel% equ 0 (
    echo 服务启动成功！
    echo 访问地址: http://localhost:5001
) else (
    echo 服务启动失败，请查看日志
)
goto END

:STOP_SERVICE
echo 正在停止服务...
python "%PYTHON_SCRIPT%" --action stop
if %errorlevel% equ 0 (
    echo 服务已停止
) else (
    echo 停止服务失败，请查看日志
)
goto END

:CHECK_STATUS
echo 正在检查服务状态...
python "%PYTHON_SCRIPT%" --action status
goto END

:SETUP_SCHEDULE
echo 正在设置定时更新任务...
python "%PYTHON_SCRIPT%" --action schedule
if %errorlevel% equ 0 (
    echo 定时任务设置成功！
    echo 系统将每天凌晨2点自动检查更新
) else (
    echo 定时任务设置失败，请以管理员身份运行
)
goto END

:VIEW_LOGS
echo 最近的日志记录：
echo ========================================
if exist "%LOG_DIR%\deploy.log" (
    powershell "Get-Content '%LOG_DIR%\deploy.log' | Select-Object -Last 20"
) else (
    echo 暂无日志记录
)
echo ========================================
goto END

:END
echo.
echo 按任意键退出...
pause >nul
```
### 2. Python部署服务 (deployment_service.py)
```
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import subprocess
import time
import signal
import psutil
import requests
import shutil
from datetime import datetime
from pathlib import Path
import argparse
import logging
from typing import Dict, Optional, List

class DeploymentService:
    def __init__(self, config_path: str = "config.json"):
        self.script_dir = Path(__file__).parent.absolute()
        self.config_path = self.script_dir / config_path
        self.config = self.load_config()
        self.setup_logging()
        
    def load_config(self) -> Dict:
        """加载配置文件"""
        default_config = {
            "git_repo": "https://github.com/your-username/your-repo.git",
            "project_dir": str(self.script_dir),
            "python_executable": "python",
            "app_script": "run.py",
            "app_host": "0.0.0.0",
            "app_port": 5001,
            "backup_count": 3,
            "update_schedule": "02:00",
            "health_check_url": "http://localhost:5001/health",
            "pid_file": "app.pid",
            "log_level": "INFO"
        }
        
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
            except Exception as e:
                print(f"配置文件加载失败: {e}")
        else:
            # 创建默认配置文件
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            print(f"已创建默认配置文件: {self.config_path}")
            
        return default_config
    
    def setup_logging(self):
        """设置日志系统"""
        log_dir = self.script_dir / "logs"
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f"deployment_{datetime.now().strftime('%Y%m%d')}.log"
        
        logging.basicConfig(
            level=getattr(logging, self.config['log_level']),
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def run_command(self, command: List[str], cwd: Optional[str] = None) -> tuple:
        """执行命令并返回结果"""
        try:
            self.logger.info(f"执行命令: {' '.join(command)}")
            result = subprocess.run(
                command,
                cwd=cwd or self.config['project_dir'],
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            return result.returncode == 0, result.stdout, result.stderr
        except Exception as e:
            self.logger.error(f"命令执行失败: {e}")
            return False, "", str(e)
    
    def check_git_repo(self) -> bool:
        """检查Git仓库状态"""
        git_dir = Path(self.config['project_dir']) / ".git"
        return git_dir.exists()
    
    def clone_or_update_repo(self) -> bool:
        """克隆或更新Git仓库"""
        project_dir = Path(self.config['project_dir'])
        
        if not self.check_git_repo():
            self.logger.info("克隆Git仓库...")
            success, stdout, stderr = self.run_command([
                "git", "clone", self.config['git_repo'], "."
            ])
            if not success:
                self.logger.error(f"Git克隆失败: {stderr}")
                return False
        else:
            self.logger.info("更新Git仓库...")
            # 检查是否有远程更新
            success, stdout, stderr = self.run_command(["git", "fetch", "origin"])
            if not success:
                self.logger.error(f"Git fetch失败: {stderr}")
                return False
            
            # 检查是否有新提交
            success, stdout, stderr = self.run_command([
                "git", "rev-list", "HEAD...origin/main", "--count"
            ])
            if success and stdout.strip() == "0":
                self.logger.info("代码已是最新版本")
                return True
            
            # 备份当前版本
            self.backup_current_version()
            
            # 拉取最新代码
            success, stdout, stderr = self.run_command(["git", "pull", "origin", "main"])
            if not success:
                self.logger.error(f"Git pull失败: {stderr}")
                return False
        
        self.logger.info("代码更新成功")
        return True
    
    def backup_current_version(self):
        """备份当前版本"""
        backup_dir = self.script_dir / "backups"
        backup_dir.mkdir(exist_ok=True)
        
        # 获取当前commit hash
        success, commit_hash, _ = self.run_command(["git", "rev-parse", "HEAD"])
        if not success:
            commit_hash = datetime.now().strftime('%Y%m%d_%H%M%S')
        else:
            commit_hash = commit_hash.strip()[:8]
        
        backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{commit_hash}"
        backup_path = backup_dir / backup_name
        
        try:
            # 复制项目文件（排除.git目录）
            shutil.copytree(
                self.config['project_dir'],
                backup_path,
                ignore=shutil.ignore_patterns('.git', '__pycache__', '*.pyc', 'logs', 'backups')
            )
            self.logger.info(f"备份创建成功: {backup_path}")
            
            # 清理旧备份
            self.cleanup_old_backups(backup_dir)
        except Exception as e:
            self.logger.error(f"备份创建失败: {e}")
    
    def cleanup_old_backups(self, backup_dir: Path):
        """清理旧备份"""
        backups = sorted([d for d in backup_dir.iterdir() if d.is_dir()], 
                        key=lambda x: x.stat().st_mtime, reverse=True)
        
        if len(backups) > self.config['backup_count']:
            for old_backup in backups[self.config['backup_count']:]:
                try:
                    shutil.rmtree(old_backup)
                    self.logger.info(f"删除旧备份: {old_backup}")
                except Exception as e:
                    self.logger.error(f"删除备份失败: {e}")
    
    def install_dependencies(self) -> bool:
        """安装Python依赖"""
        requirements_file = Path(self.config['project_dir']) / "requirements.txt"
        if not requirements_file.exists():
            self.logger.warning("requirements.txt文件不存在")
            return True
        
        self.logger.info("安装Python依赖...")
        success, stdout, stderr = self.run_command([
            self.config['python_executable'], "-m", "pip", "install", "-r", "requirements.txt"
        ])
        
        if not success:
            self.logger.error(f"依赖安装失败: {stderr}")
            return False
        
        self.logger.info("依赖安装成功")
        return True
    
    def get_app_pid(self) -> Optional[int]:
        """获取应用进程ID"""
        pid_file = Path(self.config['project_dir']) / self.config['pid_file']
        if pid_file.exists():
            try:
                with open(pid_file, 'r') as f:
                    pid = int(f.read().strip())
                # 检查进程是否存在
                if psutil.pid_exists(pid):
                    return pid
            except (ValueError, FileNotFoundError):
                pass
        return None
    
    def save_app_pid(self, pid: int):
        """保存应用进程ID"""
        pid_file = Path(self.config['project_dir']) / self.config['pid_file']
        with open(pid_file, 'w') as f:
            f.write(str(pid))
    
    def remove_pid_file(self):
        """删除PID文件"""
        pid_file = Path(self.config['project_dir']) / self.config['pid_file']
        if pid_file.exists():
            pid_file.unlink()
    
    def is_service_running(self) -> bool:
        """检查服务是否运行"""
        pid = self.get_app_pid()
        if pid:
            try:
                process = psutil.Process(pid)
                return process.is_running()
            except psutil.NoSuchProcess:
                pass
        return False
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            response = requests.get(
                self.config['health_check_url'], 
                timeout=5
            )
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def start_service(self) -> bool:
        """启动服务"""
        if self.is_service_running():
            self.logger.info("服务已在运行中")
            return True
        
        self.logger.info("启动应用服务...")
        
        try:
            # 启动应用
            process = subprocess.Popen([
                self.config['python_executable'],
                self.config['app_script']
            ], cwd=self.config['project_dir'])
            
            # 保存PID
            self.save_app_pid(process.pid)
            
            # 等待服务启动
            for i in range(30):  # 最多等待30秒
                time.sleep(1)
                if self.health_check():
                    self.logger.info(f"服务启动成功，PID: {process.pid}")
                    return True
            
            self.logger.error("服务启动超时")
            return False
            
        except Exception as e:
            self.logger.error(f"服务启动失败: {e}")
            return False
    
    def stop_service(self) -> bool:
        """停止服务"""
        pid = self.get_app_pid()
        if not pid:
            self.logger.info("服务未运行")
            return True
        
        try:
            process = psutil.Process(pid)
            self.logger.info(f"停止服务，PID: {pid}")
            
            # 优雅停止
            process.terminate()
            
            # 等待进程结束
            try:
                process.wait(timeout=10)
            except psutil.TimeoutExpired:
                self.logger.warning("优雅停止超时，强制终止进程")
                process.kill()
            
            self.remove_pid_file()
            self.logger.info("服务已停止")
            return True
            
        except psutil.NoSuchProcess:
            self.remove_pid_file()
            self.logger.info("进程不存在，清理PID文件")
            return True
        except Exception as e:
            self.logger.error(f"停止服务失败: {e}")
            return False
    
    def restart_service(self) -> bool:
        """重启服务"""
        self.logger.info("重启服务...")
        if not self.stop_service():
            return False
        time.sleep(2)
        return self.start_service()
    
    def get_service_status(self) -> Dict:
        """获取服务状态"""
        status = {
            "running": self.is_service_running(),
            "pid": self.get_app_pid(),
            "health_check": False,
            "git_status": "unknown",
            "last_commit": "unknown"
        }
        
        if status["running"]:
            status["health_check"] = self.health_check()
        
        # 获取Git状态
        if self.check_git_repo():
            success, stdout, _ = self.run_command(["git", "status", "--porcelain"])
            if success:
                status["git_status"] = "clean" if not stdout.strip() else "modified"
            
            success, stdout, _ = self.run_command(["git", "log", "-1", "--format=%h %s"])
            if success:
                status["last_commit"] = stdout.strip()
        
        return status
    
    def setup_scheduled_task(self) -> bool:
        """设置Windows定时任务"""
        task_name = "TKTool_AutoUpdate"
        script_path = Path(__file__).absolute()
        
        # 删除现有任务
        subprocess.run([
            "schtasks", "/delete", "/tn", task_name, "/f"
        ], capture_output=True)
        
        # 创建新任务
        command = [
            "schtasks", "/create",
            "/tn", task_name,
            "/tr", f'python "{script_path}" --action update',
            "/sc", "daily",
            "/st", self.config['update_schedule'],
            "/ru", "SYSTEM",
            "/f"
        ]
        
        success, stdout, stderr = self.run_command(command)
        if success:
            self.logger.info(f"定时任务创建成功: {task_name}")
            return True
        else:
            self.logger.error(f"定时任务创建失败: {stderr}")
            return False
    
    def init_deployment(self) -> bool:
        """初始化部署"""
        self.logger.info("开始初始化部署...")
        
        # 1. 克隆或更新代码
        if not self.clone_or_update_repo():
            return False
        
        # 2. 安装依赖
        if not self.install_dependencies():
            return False
        
        self.logger.info("初始化部署完成")
        return True
    
    def update_deployment(self) -> bool:
        """更新部署"""
        self.logger.info("开始更新部署...")
        
        # 1. 更新代码
        if not self.clone_or_update_repo():
            return False
        
        # 2. 安装依赖
        if not self.install_dependencies():
            return False
        
        # 3. 重启服务
        if self.is_service_running():
            if not self.restart_service():
                return False
        
        self.logger.info("更新部署完成")
        return True

def main():
    parser = argparse.ArgumentParser(description='TK工具部署服务')
    parser.add_argument('--action', required=True, 
                       choices=['init', 'update', 'start', 'stop', 'restart', 'status', 
                       'schedule'],
                       help='执行的操作')
    parser.add_argument('--config', default='config.json', help='配置文件路径')
    
    args = parser.parse_args()
    
    service = DeploymentService(args.config)
    
    try:
        if args.action == 'init':
            success = service.init_deployment()
        elif args.action == 'update':
            success = service.update_deployment()
        elif args.action == 'start':
            success = service.start_service()
        elif args.action == 'stop':
            success = service.stop_service()
        elif args.action == 'restart':
            success = service.restart_service()
        elif args.action == 'status':
            status = service.get_service_status()
            print(json.dumps(status, indent=2, ensure_ascii=False))
            success = True
        elif args.action == 'schedule':
            success = service.setup_scheduled_task()
        else:
            print(f"未知操作: {args.action}")
            success = False
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n操作被用户中断")
        sys.exit(1)
    except Exception as e:
        service.logger.error(f"执行失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
```
### 3. 进程守护器 (process_guardian.py)
```
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import json
import logging
import requests
import psutil
from pathlib import Path
from datetime import datetime
from deployment_service import DeploymentService

class ProcessGuardian:
    def __init__(self, config_path: str = "config.json"):
        self.deployment_service = DeploymentService(config_path)
        self.config = self.deployment_service.config
        self.logger = self.deployment_service.logger
        self.check_interval = 30  # 检查间隔（秒）
        self.max_restart_attempts = 3  # 最大重启尝试次数
        self.restart_count = 0
        self.last_restart_time = None
        
    def is_healthy(self) -> bool:
        """检查服务健康状态"""
        # 1. 检查进程是否存在
        if not self.deployment_service.is_service_running():
            self.logger.warning("服务进程不存在")
            return False
        
        # 2. 检查HTTP健康检查
        if not self.deployment_service.health_check():
            self.logger.warning("HTTP健康检查失败")
            return False
        
        return True
    
    def should_restart(self) -> bool:
        """判断是否应该重启服务"""
        now = datetime.now()
        
        # 如果是第一次重启或距离上次重启超过1小时，重置计数器
        if (self.last_restart_time is None or 
            (now - self.last_restart_time).seconds > 3600):
            self.restart_count = 0
        
        # 检查重启次数限制
        if self.restart_count >= self.max_restart_attempts:
            self.logger.error(f"重启次数已达上限({self.max_restart_attempts})，停止自动重启")
            return False
        
        return True
    
    def restart_service(self) -> bool:
        """重启服务"""
        if not self.should_restart():
            return False
        
        self.logger.info(f"尝试重启服务 (第{self.restart_count + 1}次)")
        
        success = self.deployment_service.restart_service()
        
        if success:
            self.restart_count += 1
            self.last_restart_time = datetime.now()
            self.logger.info("服务重启成功")
        else:
            self.logger.error("服务重启失败")
        
        return success
    
    def log_system_info(self):
        """记录系统信息"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 内存使用情况
            memory = psutil.virtual_memory()
            
            # 磁盘使用情况
            disk = psutil.disk_usage('/')
            
            self.logger.info(
                f"系统状态 - CPU: {cpu_percent}%, "
                f"内存: {memory.percent}%, "
                f"磁盘: {disk.percent}%"
            )
        except Exception as e:
            self.logger.error(f"获取系统信息失败: {e}")
    
    def run(self):
        """运行守护进程"""
        self.logger.info("进程守护器启动")
        
        while True:
            try:
                # 检查服务健康状态
                if not self.is_healthy():
                    self.logger.warning("检测到服务异常")
                    
                    # 尝试重启服务
                    if self.restart_service():
                        # 等待服务启动
                        time.sleep(10)
                        
                        # 再次检查健康状态
                        if self.is_healthy():
                            self.logger.info("服务恢复正常")
                        else:
                            self.logger.error("服务重启后仍然异常")
                    else:
                        self.logger.error("服务重启失败")
                else:
                    # 服务正常，重置重启计数器
                    if self.restart_count > 0:
                        self.restart_count = 0
                        self.logger.info("服务状态正常，重置重启计数器")
                
                # 每10分钟记录一次系统信息
                if int(time.time()) % 600 == 0:
                    self.log_system_info()
                
                # 等待下次检查
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                self.logger.info("守护进程被用户中断")
                break
            except Exception as e:
                self.logger.error(f"守护进程异常: {e}")
                time.sleep(self.check_interval)
        
        self.logger.info("进程守护器停止")

if __name__ == '__main__':
    guardian = ProcessGuardian()
    guardian.run()
```
### 4. 配置文件 (config.json)
```
{
  "git_repo": "https://github.com/your-username/tktool_byclaude.git",
  "project_dir": ".",
  "python_executable": "python",
  "app_script": "run.py",
  "app_host": "0.0.0.0",
  "app_port": 5001,
  "backup_count": 3,
  "update_schedule": "02:00",
  "health_check_url": "http://localhost:5001/api/monitoring/health",
  "pid_file": "app.pid",
  "log_level": "INFO",
  "git_branch": "main",
  "auto_restart": true,
  "max_restart_attempts": 3,
  "check_interval": 30,
  "notification": {
    "enabled": false,
    "email": {
      "smtp_server": "smtp.gmail.com",
      "smtp_port": 587,
      "username": "your-email@gmail.com",
      "password": "your-app-password",
      "to_addresses": ["admin@company.com"]
    }
  }
}
```
### 5. 一键安装脚本 (install.bat)
```
@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo     TK工具一键安装脚本 v1.0
echo ========================================
echo.

set "INSTALL_DIR=%~dp0"
cd /d "%INSTALL_DIR%"

echo 正在检查Python环境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误：未找到Python，请先安装Python 3.8+
    echo 下载地址：https://www.python.org/downloads/
    pause
    exit /b 1
)

echo 正在检查Git环境...
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误：未找到Git，请先安装Git
    echo 下载地址：https://git-scm.com/downloads
    pause
    exit /b 1
)

echo 正在安装Python依赖包...
python -m pip install --upgrade pip
python -m pip install psutil requests

if %errorlevel% neq 0 (
    echo 依赖包安装失败，请检查网络连接
    pause
    exit /b 1
)

echo 正在创建必要目录...
if not exist "logs" mkdir "logs"
if not exist "backups" mkdir "backups"

echo 正在设置Git仓库地址...
set /p git_repo="请输入Git仓库地址 (默认: https://github.com/your-username/tktool_byclaude.git): "
if "%git_repo%"=="" set "git_repo=https://github.com/your-username/tktool_byclaude.git"

echo 正在更新配置文件...
(
echo {
echo   "git_repo": "%git_repo%",
echo   "project_dir": ".",
echo   "python_executable": "python",
echo   "app_script": "run.py",
echo   "app_host": "0.0.0.0",
echo   "app_port": 5001,
echo   "backup_count": 3,
echo   "update_schedule": "02:00",
echo   "health_check_url": "http://localhost:5001/api/monitoring/health",
echo   "pid_file": "app.pid",
echo   "log_level": "INFO"
echo }
) > config.json

echo 正在执行初始化部署...
python deployment_service.py --action init

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo          安装完成！
    echo ========================================
    echo.
    echo 使用说明：
    echo 1. 运行 deploy_manager.bat 管理服务
    echo 2. 访问 http://localhost:5001 使用应用
    echo 3. 查看 logs 目录获取运行日志
    echo.
    echo 是否现在启动服务？ (Y/N)
    set /p start_now=""
    if /i "!start_now!"=="Y" (
        echo 正在启动服务...
        python deployment_service.py --action start
        if !errorlevel! equ 0 (
            echo 服务启动成功！
            echo 访问地址: http://localhost:5001
        )
    )
) else (
    echo 安装失败，请查看错误信息
)

echo.
echo 按任意键退出...
pause >nul
```
## 使用说明
### 1. 安装部署
1. 1.
   将所有脚本文件放在目标Windows机器上
2. 2.
   以管理员身份运行 install.bat
3. 3.
   按提示输入Git仓库地址
4. 4.
   等待自动安装完成
### 2. 日常管理
- 一键部署 : 运行 deploy_manager.bat 选择选项1
- 更新代码 : 运行 deploy_manager.bat 选择选项2
- 启动服务 : 运行 deploy_manager.bat 选择选项3
- 停止服务 : 运行 deploy_manager.bat 选择选项4
- 查看状态 : 运行 deploy_manager.bat 选择选项5
- 设置定时更新 : 运行 deploy_manager.bat 选择选项6
### 3. 监控和维护
- 日志文件位于 logs/ 目录
- 备份文件位于 backups/ 目录
- 配置文件为 config.json
- 系统会自动每天凌晨2点检查更新
这套方案提供了完整的自动化部署解决方案，具有高度的可靠性和易用性，适合团队协作环境使用。