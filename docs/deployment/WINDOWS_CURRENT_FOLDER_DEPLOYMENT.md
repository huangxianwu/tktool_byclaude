# Windows 当前目录部署指南

## 概述

本指南介绍如何使用 `windows_deploy_current_folder.bat` 脚本在Windows系统上将TK Tool项目部署到当前目录。

## 系统要求

### 必需软件
- **Windows 10/11** 或 Windows Server 2016+
- **Git** 2.0+ (用于代码拉取)
- **Python** 3.8+ (推荐 3.9 或更高版本)
- **pip** (Python包管理器)

### 硬件要求
- **内存**: 最少 2GB RAM
- **存储**: 最少 1GB 可用空间
- **网络**: 稳定的互联网连接

## 快速部署

### 方法一：自动部署（推荐）

1. **创建部署目录**
   ```cmd
   mkdir C:\TKTool
   cd C:\TKTool
   ```

2. **下载部署脚本**
   ```cmd
   curl -O https://raw.githubusercontent.com/huangxianwu/tktool_byclaude/main/scripts/windows_deploy_current_folder.bat
   ```

3. **运行部署脚本**
   ```cmd
   windows_deploy_current_folder.bat
   ```

4. **按照提示操作**
   - 脚本会自动检查环境
   - 拉取最新代码到当前目录
   - 配置数据库
   - 安装依赖
   - 创建启动脚本

### 方法二：手动下载脚本

1. 从GitHub下载 `windows_deploy_current_folder.bat` 脚本
2. 将脚本放置在您希望部署项目的目录中
3. 双击运行脚本或在命令行中执行

## 部署过程详解

### 1. 环境检查
脚本会自动检查：
- Git 安装状态和版本
- Python 安装状态和版本（需要3.8+）
- pip 可用性

### 2. 代码拉取
- **新部署**: 克隆完整仓库到当前目录
- **更新部署**: 检测现有Git仓库并拉取最新代码
- **冲突处理**: 自动暂存本地更改（如有）

### 3. 数据库配置
脚本提供三种数据库配置选项：

#### 选项1：复制现有数据库
```
1. 我已经准备好数据库文件，需要复制到instance目录
```
- 选择此选项后，将数据库文件复制到 `instance\app.db`
- 脚本会等待您完成复制操作

#### 选项2：创建新数据库
```
2. 创建新的空数据库（用于测试）
```
- 脚本会创建一个新的空数据库
- 适用于测试环境或全新安装

#### 选项3：稍后配置
```
3. 退出，稍后手动配置数据库
```
- 退出部署，允许您手动配置数据库

### 4. Python环境设置
- 创建虚拟环境 (`venv`)
- 升级pip到最新版本
- 安装项目依赖包

### 5. 数据库初始化
- 运行数据库初始化脚本
- 验证数据库连接和表结构

### 6. 创建管理脚本
自动创建以下管理脚本：
- `start_server.bat` - 启动服务器
- `stop_server.bat` - 停止服务器

## 使用方法

### 启动应用
```cmd
# 方法1：双击启动脚本
start_server.bat

# 方法2：命令行启动
venv\Scripts\python run.py
```

### 访问应用
打开浏览器访问：
```
http://localhost:5004
```

### 停止应用
```cmd
# 方法1：双击停止脚本
stop_server.bat

# 方法2：在服务器窗口按 Ctrl+C
```

## 目录结构

部署完成后的目录结构：
```
当前目录/
├── app/                    # 应用主目录
├── instance/               # 实例配置目录
│   └── app.db             # SQLite数据库文件
├── venv/                   # Python虚拟环境
├── static/                 # 静态文件
├── templates/              # 模板文件
├── scripts/                # 脚本文件
├── run.py                  # 应用启动文件
├── config.py               # 配置文件
├── requirements.txt        # 依赖列表
├── start_server.bat        # 启动脚本
└── stop_server.bat         # 停止脚本
```

## 配置文件

### 主要配置文件

#### `config.py`
```python
# 数据库配置
SQLALCHEMY_DATABASE_URI = 'sqlite:///instance/app.db'

# 服务器配置
SECRET_KEY = 'your-secret-key'

# API配置
RUNNINGHUB_BASE_URL = 'https://www.runninghub.cn/task/openapi'
RUNNINGHUB_API_KEY = 'your-api-key'
```

#### `run.py`
```python
# 服务器端口配置
app.run(debug=True, host='0.0.0.0', port=5004)
```

## 故障排除

### 常见问题

#### 1. 脚本无法运行
**症状**: 双击脚本无响应
**解决方案**:
- 右键脚本 → "以管理员身份运行"
- 检查脚本编码是否为UTF-8
- 在命令行中运行脚本查看错误信息

#### 2. Git未安装
**症状**: "未找到Git"错误
**解决方案**:
```cmd
# 使用winget安装
winget install --id Git.Git -e

# 或下载安装包
# https://git-scm.com/download/win
```

#### 3. Python版本过低
**症状**: "Python版本不符合要求"
**解决方案**:
```cmd
# 使用winget安装最新Python
winget install --id Python.Python.3 -e

# 或从官网下载
# https://www.python.org/downloads/
```

#### 4. 依赖安装失败
**症状**: pip install 错误
**解决方案**:
```cmd
# 使用国内镜像
venv\Scripts\pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 升级pip
venv\Scripts\python -m pip install --upgrade pip

# 清理缓存
venv\Scripts\pip cache purge
```

#### 5. 数据库连接失败
**症状**: 数据库相关错误
**解决方案**:
- 检查 `instance\app.db` 文件是否存在
- 验证文件权限
- 重新运行数据库初始化：
  ```cmd
  venv\Scripts\python scripts\windows_db_init.py
  ```

#### 6. 端口占用
**症状**: "端口5004已被占用"
**解决方案**:
```cmd
# 查找占用端口的进程
netstat -ano | findstr :5004

# 终止进程（替换PID）
taskkill /PID <PID> /F

# 或修改端口配置
# 编辑 run.py 文件，更改端口号
```

### 日志查看

#### 应用日志
- 启动服务器后，日志会显示在命令行窗口
- 错误信息通常包含详细的堆栈跟踪

#### 系统日志
```cmd
# 查看Windows事件日志
eventvwr.msc
```

## 更新和维护

### 更新代码
```cmd
# 重新运行部署脚本即可更新
windows_deploy_current_folder.bat
```

### 备份数据库
```cmd
# 复制数据库文件
copy instance\app.db instance\app.db.backup.%date%
```

### 清理环境
```cmd
# 删除虚拟环境
rmdir /s venv

# 重新部署
windows_deploy_current_folder.bat
```

## 安全建议

### 生产环境配置
1. **更改默认密钥**
   ```python
   # config.py
   SECRET_KEY = 'your-production-secret-key'
   ```

2. **禁用调试模式**
   ```python
   # run.py
   app.run(debug=False, host='0.0.0.0', port=5004)
   ```

3. **配置防火墙**
   ```cmd
   # 允许端口5004
   netsh advfirewall firewall add rule name="TK Tool" dir=in action=allow protocol=TCP localport=5004
   ```

4. **定期备份**
   - 设置定时任务备份数据库
   - 备份配置文件

### 网络安全
- 仅在受信任的网络环境中运行
- 考虑使用HTTPS（需要额外配置）
- 定期更新依赖包

## 性能优化

### 系统优化
- 确保足够的内存和存储空间
- 定期清理临时文件
- 监控系统资源使用情况

### 应用优化
- 定期清理数据库
- 优化数据库查询
- 监控应用性能

## 技术支持

### 获取帮助
- **项目文档**: 查看项目README和其他文档
- **GitHub Issues**: 提交问题和建议
- **测试工具**: 使用 `test_windows_deploy_current_folder.py` 诊断问题

### 测试部署
```cmd
# 运行测试脚本
python scripts\test_windows_deploy_current_folder.py
```

### 联系方式
- GitHub: [项目仓库](https://github.com/huangxianwu/tktool_byclaude)
- 邮件: 技术支持邮箱

---

**注意**: 本指南基于Windows环境编写，其他操作系统请参考相应的部署文档。