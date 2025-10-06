# TK Tool Windows 部署指南

本指南将帮助您在Windows环境中快速部署TK Tool项目。

## 📋 系统要求

### 必需软件
- **Python 3.8+** - [下载地址](https://www.python.org/downloads/)
- **Git** - [下载地址](https://git-scm.com/download/win)
- **Windows 10/11** 或 **Windows Server 2016+**

### 硬件要求
- **内存**: 最少 2GB RAM，推荐 4GB+
- **存储**: 最少 1GB 可用空间
- **网络**: 互联网连接（用于下载依赖）

## 🚀 快速部署

### 方法一：自动部署（推荐）

1. **下载项目代码**
   ```cmd
   git clone https://github.com/huangxianwu/tktool_byclaude.git
   cd tktool_byclaude
   ```

2. **运行自动部署脚本**
   ```cmd
   scripts\windows_auto_deploy.bat
   ```

3. **按照提示操作**
   - 脚本会自动检查环境
   - 安装Python依赖
   - 配置数据库
   - 创建启动脚本

### 方法二：手动部署

如果自动部署遇到问题，可以按以下步骤手动部署：

1. **克隆项目**
   ```cmd
   git clone https://github.com/huangxianwu/tktool_byclaude.git
   cd tktool_byclaude
   ```

2. **安装依赖**
   ```cmd
   pip install -r requirements.txt
   ```

3. **配置数据库**
   ```cmd
   mkdir instance
   # 将您的app.db文件复制到instance目录
   python scripts\windows_db_init.py
   ```

4. **启动应用**
   ```cmd
   python run.py
   ```

## 📁 数据库配置

### 使用现有数据库

如果您已有数据库文件：

1. **复制数据库文件**
   ```cmd
   # 将您的app.db文件复制到以下位置
   copy "您的数据库路径\app.db" "项目目录\instance\app.db"
   ```

2. **验证数据库**
   ```cmd
   python scripts\windows_db_init.py
   ```

### 创建新数据库

如果需要创建新的空数据库：

1. **运行初始化脚本**
   ```cmd
   python scripts\windows_db_init.py
   ```

2. **选择创建新数据库选项**

## 🔧 启动和管理

### 启动应用

部署完成后，您可以使用以下方式启动应用：

```cmd
# 方式1：使用生成的启动脚本
start_tktool.bat

# 方式2：直接运行Python
python run.py
```

### 停止应用

```cmd
# 使用生成的停止脚本
stop_tktool.bat

# 或者在命令行中按 Ctrl+C
```

### 重启应用

```cmd
restart_tktool.bat
```

## 🌐 访问应用

应用启动后，在浏览器中访问：

- **本地访问**: http://localhost:5000
- **局域网访问**: http://您的IP地址:5000

## 🛠️ 故障排除

### 常见问题

#### 1. Python版本问题
```
错误: Python版本过低
解决: 安装Python 3.8或更高版本
```

#### 2. 依赖安装失败
```
错误: pip install失败
解决方案:
1. 升级pip: python -m pip install --upgrade pip
2. 使用国内镜像: pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
3. 检查网络连接
```

#### 3. 数据库连接失败
```
错误: 数据库连接失败
解决方案:
1. 检查instance\app.db文件是否存在
2. 检查文件权限
3. 重新运行: python scripts\windows_db_init.py
```

#### 4. 端口占用
```
错误: Address already in use
解决方案:
1. 更改端口: 编辑config.py中的PORT设置
2. 或者停止占用端口的程序
```

### 日志查看

应用运行时的日志信息会显示在命令行窗口中。如需保存日志：

```cmd
python run.py > app.log 2>&1
```

### 测试部署

运行测试脚本验证部署：

```cmd
python scripts\test_windows_deploy.py
```

## 📝 配置文件

### config.py

主要配置项：

```python
# 数据库配置
SQLALCHEMY_DATABASE_URI = 'sqlite:///instance/app.db'

# 应用配置
SECRET_KEY = '您的密钥'
DEBUG = False  # 生产环境设为False

# 服务器配置
HOST = '0.0.0.0'  # 允许外部访问
PORT = 5000       # 端口号
```

### requirements.txt

包含所有必需的Python依赖包。如需添加新依赖：

```cmd
pip install 新包名
pip freeze > requirements.txt
```

## 🔄 更新部署

### 更新代码

```cmd
# 拉取最新代码
git pull origin main

# 更新依赖
pip install -r requirements.txt

# 重启应用
restart_tktool.bat
```

### 数据库迁移

如果有数据库结构更新：

```cmd
python scripts\migrate_database.py
```

## 🔒 安全建议

1. **更改默认密钥**
   - 修改config.py中的SECRET_KEY

2. **防火墙配置**
   - 仅开放必要端口（如5000）

3. **定期备份**
   - 备份instance\app.db数据库文件

4. **更新依赖**
   - 定期更新Python包以获取安全补丁

## 📞 技术支持

如果遇到问题：

1. **查看日志**: 检查应用运行日志
2. **运行测试**: 使用test_windows_deploy.py诊断
3. **检查文档**: 参考本文档的故障排除部分
4. **提交Issue**: 在GitHub仓库提交问题报告

## 📚 相关文档

- [项目架构文档](../architecture/ARCHITECTURE.md)
- [API文档](../api/API.md)
- [开发指南](../development/DEVELOPMENT.md)
- [Docker部署](DOCKER_DEPLOYMENT.md)

---

**注意**: 本指南适用于Windows环境。Linux/macOS用户请参考相应的部署文档。