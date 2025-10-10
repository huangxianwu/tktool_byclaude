# 数据库迁移修复指南

## 问题描述

在其他设备上运行项目时，可能会遇到以下错误：

```
sqlite3.OperationalError: no such column: workflows.pinned
```

这个错误表明数据库中缺少 `workflows` 表的 `pinned` 和 `pinned_at` 字段，导致工作流和输出页面为空。

## 问题原因

1. **数据库迁移未同步**: 在开发过程中添加了新的数据库字段，但迁移文件未在其他设备上执行
2. **数据库版本不一致**: 不同设备上的数据库模式版本不同
3. **迁移文件缺失**: 可能缺少 `a3c7b9d1f2e0_add_pinned_fields_to_workflows.py` 迁移文件

## 解决方案

### 方案一：自动修复脚本（推荐）

#### Windows 用户

1. **使用批处理文件（最简单）**：
   ```cmd
   # 双击运行或在命令行执行
   fix_database.bat
   ```

2. **使用命令行**：
   ```cmd
   # 检查数据库状态
   python fix_database_migration.py --check-only
   
   # 自动修复
   python fix_database_migration.py
   
   # 强制修复
   python fix_database_migration.py --force
   ```

#### macOS/Linux 用户

```bash
# 检查数据库状态
python3 fix_database_migration.py --check-only

# 自动修复
python3 fix_database_migration.py

# 强制修复
python3 fix_database_migration.py --force
```

### 方案二：手动 SQL 修复

如果自动脚本失败，可以手动执行 SQL 命令：

```sql
-- 添加 pinned 字段
ALTER TABLE workflows ADD COLUMN pinned BOOLEAN NOT NULL DEFAULT 0;

-- 添加 pinned_at 字段
ALTER TABLE workflows ADD COLUMN pinned_at DATETIME;
```

#### 执行步骤：

1. **找到数据库文件**：
   - 通常位于 `instance/database.db`
   - 或者 `database.db`、`app.db`

2. **使用 SQLite 命令行工具**：
   ```bash
   sqlite3 instance/database.db
   ```

3. **执行 SQL 命令**：
   ```sql
   ALTER TABLE workflows ADD COLUMN pinned BOOLEAN NOT NULL DEFAULT 0;
   ALTER TABLE workflows ADD COLUMN pinned_at DATETIME;
   .quit
   ```

### 方案三：Flask-Migrate 修复

```bash
# 确保在项目根目录
cd /path/to/your/project

# 运行迁移
flask db upgrade

# 或者使用 Python
python -c "from app import create_app, db; from flask_migrate import upgrade; app = create_app(); app.app_context().push(); upgrade()"
```

## 验证修复

修复完成后，验证是否成功：

1. **检查数据库模式**：
   ```bash
   python fix_database_migration.py --check-only
   ```

2. **启动应用**：
   ```bash
   python run.py
   ```

3. **访问页面**：
   - 打开 `http://localhost:8080/workflows`
   - 确认工作流列表正常显示
   - 打开 `http://localhost:8080/outputs`
   - 确认输出列表正常显示

## 预防措施

### 1. 同步迁移文件

确保所有设备都有最新的迁移文件：

```bash
# 检查迁移文件
ls migrations/versions/

# 应该包含：
# a3c7b9d1f2e0_add_pinned_fields_to_workflows.py
```

### 2. 定期运行迁移

在拉取代码后，始终运行迁移：

```bash
git pull
flask db upgrade
```

### 3. 备份数据库

在进行迁移前，始终备份数据库：

```bash
# 自动备份（脚本会自动创建）
python fix_database_migration.py --backup-only

# 手动备份
cp instance/database.db backups/database_backup_$(date +%Y%m%d_%H%M%S).db
```

## 故障排除

### 问题1：Python 模块导入错误

```
ImportError: No module named 'flask'
```

**解决方案**：
```bash
pip install -r requirements.txt
```

### 问题2：数据库文件不存在

```
数据库文件不存在: instance/database.db
```

**解决方案**：
1. 检查数据库文件位置
2. 运行初始化脚本：
   ```bash
   python windows_db_init.py  # Windows
   python run.py              # 其他系统
   ```

### 问题3：权限错误

```
PermissionError: [Errno 13] Permission denied
```

**解决方案**：
1. 确保有数据库文件的写权限
2. 以管理员身份运行（Windows）
3. 使用 `sudo`（Linux/macOS）

### 问题4：迁移文件冲突

```
Multiple heads in the database
```

**解决方案**：
```bash
flask db merge heads
flask db upgrade
```

## 脚本功能说明

### fix_database_migration.py

- **自动检测**: 检查数据库模式和缺失字段
- **智能备份**: 自动创建带时间戳的备份文件
- **多种修复方式**: Flask-Migrate 和手动 SQL 两种方式
- **详细日志**: 提供详细的操作日志和错误信息
- **安全性**: 修复前自动备份，支持回滚

### fix_database.bat

- **用户友好**: 提供交互式菜单界面
- **多种选项**: 检查、备份、修复、强制修复
- **错误处理**: 检查 Python 环境和文件存在性
- **中文支持**: 完整的中文界面和提示

## 技术细节

### 添加的字段

```sql
-- 置顶标记字段
pinned BOOLEAN NOT NULL DEFAULT 0

-- 置顶时间字段
pinned_at DATETIME
```

### 迁移文件内容

```python
# migrations/versions/a3c7b9d1f2e0_add_pinned_fields_to_workflows.py

def upgrade():
    op.add_column('workflows', sa.Column('pinned', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('workflows', sa.Column('pinned_at', sa.DateTime(), nullable=True))

def downgrade():
    op.drop_column('workflows', 'pinned_at')
    op.drop_column('workflows', 'pinned')
```

## 联系支持

如果遇到无法解决的问题，请提供以下信息：

1. 操作系统版本
2. Python 版本
3. 错误日志的完整输出
4. 数据库文件大小和位置
5. 执行的具体命令

---

**注意**: 在生产环境中执行数据库迁移前，请务必备份数据库文件。