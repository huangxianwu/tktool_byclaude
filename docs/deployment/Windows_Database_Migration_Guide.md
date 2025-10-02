# Windows数据库迁移详细指南

## 概述

本指南详细说明如何将TK Tool的SQLite数据库从Mac/Linux环境迁移到Windows环境。

## 准备工作

### 在Mac/Linux环境中

1. **确认数据库文件位置**
   ```bash
   # 查看主数据库文件
   ls -la instance/app.db
   
   # 查看所有数据库文件
   find . -name "*.db" -type f
   ```

2. **创建数据库备份**
   ```bash
   # 创建备份目录
   mkdir -p backups
   
   # 备份主数据库
   cp instance/app.db backups/app_backup_$(date +%Y%m%d_%H%M%S).db
   ```

3. **压缩项目文件（推荐）**
   ```bash
   # 创建完整项目压缩包
   tar -czf tktool_project.tar.gz \
     --exclude='.git' \
     --exclude='__pycache__' \
     --exclude='*.pyc' \
     --exclude='.DS_Store' \
     .
   ```

## Windows环境部署步骤

### 方法一：完整项目迁移（推荐）

#### 1. 传输项目文件

**选项A：使用压缩包**
```cmd
# 在Windows中解压项目文件到目标目录
# 例如：D:\Projects\tktool\
```

**选项B：直接复制文件夹**
- 将整个项目文件夹复制到Windows环境
- 确保包含 `instance/app.db` 文件

#### 2. 验证文件完整性

```cmd
# 进入项目目录
cd D:\Projects\tktool

# 检查关键文件是否存在
dir instance\app.db
dir requirements.txt
dir run.py
dir scripts\windows_db_init.py
```

#### 3. 运行数据库初始化脚本

```cmd
# 安装Python依赖
pip install -r requirements.txt

# 运行数据库初始化检查
python scripts\windows_db_init.py
```

**预期输出：**
```
============================================================
Windows环境数据库初始化脚本
============================================================
当前工作目录: D:\Projects\tktool
✓ instance目录已存在: D:\Projects\tktool\instance
✓ 数据库文件已存在: D:\Projects\tktool\instance\app.db (710.45 MB)
✓ 数据库连接成功，发现 7 个表:
  - nodes: 78 条记录
  - task_data: 1039 条记录
  - task_logs: 384955 条记录
  - alembic_version: 1 条记录
  - tasks: 262 条记录
  ... 还有 2 个表

✓ 数据库已就绪，无需初始化
```

### 方法二：仅数据库文件迁移

#### 1. 准备Windows环境

```cmd
# 创建项目目录
mkdir D:\Projects\tktool
cd D:\Projects\tktool

# 下载或复制项目代码（不包含数据库）
# git clone <repository-url> .
# 或复制除了instance目录外的所有文件
```

#### 2. 传输数据库文件

**选项A：直接复制**
```cmd
# 创建instance目录
mkdir instance

# 将Mac环境的app.db文件复制到Windows的instance目录
# 例如通过U盘、网络共享、云存储等方式
copy "source_path\app.db" "instance\app.db"
```

**选项B：使用迁移脚本**
```cmd
# 将数据库文件放在项目根目录或任意位置
# 运行迁移脚本
python scripts\migrate_database.py
```

#### 3. 验证数据库

```cmd
# 运行数据库初始化脚本验证
python scripts\windows_db_init.py
```

## 使用windows_db_init.py脚本

### 脚本功能

`windows_db_init.py` 脚本的主要功能：

1. **环境检查**：验证Python环境和依赖
2. **目录检查**：确保`instance`目录存在
3. **数据库检查**：验证数据库文件是否存在和可访问
4. **连接测试**：测试数据库连接和表结构
5. **初始化**：如果需要，创建新的空数据库

### 使用场景

#### 场景1：已有数据库文件
```cmd
# 当instance/app.db已存在时
python scripts\windows_db_init.py

# 输出：检查现有数据库，显示表和记录统计
```

#### 场景2：需要创建新数据库
```cmd
# 当没有数据库文件时
python scripts\windows_db_init.py

# 输出：创建新的空数据库和表结构
```

#### 场景3：数据库损坏或无法访问
```cmd
# 脚本会尝试修复或重新创建
python scripts\windows_db_init.py
```

### 脚本输出说明

**成功情况：**
```
✓ instance目录已存在
✓ 数据库文件已存在: path\to\app.db (size)
✓ 数据库连接成功，发现 X 个表
✓ 数据库已就绪，无需初始化
```

**需要初始化：**
```
⚠ 数据库文件不存在，将创建新数据库
✓ 创建instance目录
✓ 初始化数据库表结构
✓ 数据库初始化完成
```

**错误情况：**
```
✗ 数据库连接失败: [错误信息]
✗ 权限不足: [错误信息]
```

## 故障排除

### 常见问题

#### 1. 数据库文件权限问题

**问题：** `PermissionError: [Errno 13] Permission denied`

**解决方案：**
```cmd
# 以管理员身份运行命令提示符
# 或修改文件夹权限
icacls "D:\Projects\tktool" /grant Users:F /T
```

#### 2. 数据库文件路径问题

**问题：** `sqlite3.OperationalError: unable to open database file`

**解决方案：**
```cmd
# 检查文件是否存在
dir instance\app.db

# 检查路径是否正确
echo %CD%
```

#### 3. Python依赖问题

**问题：** `ModuleNotFoundError: No module named 'xxx'`

**解决方案：**
```cmd
# 重新安装依赖
pip install -r requirements.txt

# 或单独安装缺失的包
pip install flask sqlalchemy flask-migrate
```

#### 4. 数据库版本不兼容

**问题：** 数据库迁移版本冲突

**解决方案：**
```cmd
# 运行数据库迁移
python -m flask db upgrade

# 或重置迁移
python -m flask db stamp head
```

## 验证部署成功

### 1. 启动应用

```cmd
# 启动TK Tool
python run.py
```

**预期输出：**
```
* Serving Flask app 'app'
* Debug mode: on
* Running on http://127.0.0.1:8080
* Running on http://[your-ip]:8080
```

### 2. 访问Web界面

- 打开浏览器访问：http://localhost:8080
- 检查是否能看到任务列表和工作流
- 验证数据是否正确迁移

### 3. 功能测试

```cmd
# 检查数据库表
python scripts\check_database.py

# 查看任务状态
python scripts\check_task_status.py
```

## 最佳实践

### 1. 备份策略

```cmd
# 定期备份数据库
copy "instance\app.db" "backups\app_backup_%date:~0,4%%date:~5,2%%date:~8,2%.db"

# 自动备份脚本
python scripts\backup_database.py
```

### 2. 性能优化

```cmd
# 清理日志
python scripts\cleanup_orphan_tasks.py

# 优化数据库
python scripts\optimize_database.py
```

### 3. 安全设置

- 设置适当的文件权限
- 配置防火墙规则
- 使用HTTPS（生产环境）

## 总结

通过以上步骤，您可以成功将TK Tool从Mac环境迁移到Windows环境：

1. **准备阶段**：备份Mac环境的数据库文件
2. **传输阶段**：将项目文件和数据库复制到Windows
3. **初始化阶段**：使用`windows_db_init.py`验证和初始化
4. **验证阶段**：启动应用并测试功能

`windows_db_init.py`脚本是整个迁移过程的关键工具，它能自动检测环境状态并执行相应的初始化操作。