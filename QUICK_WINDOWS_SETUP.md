# 🚀 TK Tool Windows快速部署指南

## 最简单的迁移方法（推荐）

### 第1步：打包Mac环境的项目
```bash
# 在Mac环境中，进入项目目录
cd /path/to/tktool_byclaude

# 创建项目压缩包（包含数据库）
tar -czf tktool_complete.tar.gz \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  .
```

### 第2步：传输到Windows
- 将 `tktool_complete.tar.gz` 复制到Windows环境
- 使用U盘、网络共享、云存储等方式

### 第3步：在Windows中解压和部署
```cmd
# 解压项目文件到目标目录
# 例如：D:\Projects\tktool\

# 进入项目目录
cd D:\Projects\tktool

# 安装Python依赖
pip install -r requirements.txt

# 运行数据库检查脚本
python scripts\windows_db_init.py

# 启动应用
python run.py
```

### 第4步：访问应用
打开浏览器访问：http://localhost:8080

---

## 仅迁移数据库文件的方法

### 如果你只想复制数据库文件：

#### 第1步：从Mac复制数据库
```bash
# 在Mac环境中，复制主数据库文件
cp instance/app.db ~/Desktop/app.db
```

#### 第2步：传输数据库文件到Windows
- 将 `app.db` 文件传输到Windows环境

#### 第3步：在Windows中设置
```cmd
# 在Windows项目目录中创建instance文件夹
mkdir instance

# 将数据库文件复制到正确位置
copy "path\to\app.db" "instance\app.db"

# 运行数据库初始化脚本验证
python scripts\windows_db_init.py
```

---

## windows_db_init.py 脚本说明

### 这个脚本会自动：
1. ✅ 检查Python环境和依赖
2. ✅ 验证项目目录结构
3. ✅ 检查数据库文件是否存在
4. ✅ 测试数据库连接
5. ✅ 显示数据库统计信息
6. ✅ 如果需要，创建新的空数据库

### 运行结果示例：
```
============================================================
Windows环境数据库初始化脚本
============================================================
✓ instance目录已存在
✓ 数据库文件已存在: instance\app.db (710.45 MB)
✓ 数据库连接成功，发现 7 个表:
  - tasks: 262 条记录
  - task_data: 1039 条记录
  - task_logs: 384955 条记录
  - nodes: 78 条记录
  - workflows: 15 条记录
  - task_outputs: 523 条记录
  - alembic_version: 1 条记录

✓ 数据库已就绪，无需初始化
============================================================
```

---

## 常见问题快速解决

### 问题1：端口被占用
```cmd
# 如果8080端口被占用，修改run.py中的端口
# 将 port=8080 改为 port=5001
```

### 问题2：权限错误
```cmd
# 以管理员身份运行命令提示符
# 右键点击"命令提示符" -> "以管理员身份运行"
```

### 问题3：依赖安装失败
```cmd
# 使用国内镜像源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

### 问题4：数据库连接失败
```cmd
# 重新运行初始化脚本
python scripts\windows_db_init.py

# 如果还是失败，删除数据库文件重新创建
del instance\app.db
python scripts\windows_db_init.py
```

---

## 🎯 总结

**最推荐的方法**：直接打包整个项目文件夹（包含数据库），然后在Windows中解压运行 `windows_db_init.py` 验证即可。

**关键文件**：
- 📁 `instance/app.db` - 主数据库文件（约710MB）
- 🔧 `scripts/windows_db_init.py` - 数据库初始化脚本
- 🚀 `run.py` - 应用启动文件

**一行命令启动**：
```cmd
python scripts\windows_db_init.py && python run.py
```