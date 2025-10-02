
# TK工具项目整理 + 文档同步自动化方案

> 针对 TK工具（Flask任务管理系统）的项目整理和文档同步自动化解决方案

---

# 任务：自动整理TK工具项目结构 + Git备份前文档同步

## 目标
- 规范化 Flask 项目目录结构，提升代码可维护性
- 在每次 Git 提交/PR 前，自动同步**已完成功能**到 **PRD** / **README** / **CHANGELOG** 等核心文档
- 确保文档与代码实现保持一致，支持 Dry-Run 预览和安全回滚

## 项目上下文
- **项目类型**：Flask Web 应用 + RunningHub API 集成
- **技术栈**：Python 3.8+, Flask 2.3.3, SQLAlchemy, SQLite
- **源码目录**：`app/` (models, api, services, managers)
- **测试目录**：`test/`
- **构建/包管理**：pip + requirements.txt
- **部署方式**：本地开发服务器 (端口5003)
- **关键文档路径**：
  - PRD：`PRD.md` (已存在)
  - README：`README.md` (已存在)
  - CHANGELOG：`CHANGELOG.md` (需创建)
  - 技术文档：`test/doc/` 目录  

---

## 标准化目录结构

### 当前项目结构
```
tktool_byclaude/
├── app/                    # 核心应用代码
│   ├── models/            # 数据模型 (Task, Workflow, TaskOutput等)
│   ├── api/               # REST API端点
│   ├── services/          # 业务服务 (RunningHub集成等)
│   ├── managers/          # 任务管理器
│   └── utils/             # 工具函数
├── templates/             # Jinja2模板
├── static/               # 静态资源 (CSS, JS, 输出文件)
├── migrations/           # 数据库迁移
├── test/                 # 测试和文档
└── instance/             # SQLite数据库实例
```

### 建议的规范化结构
```
tktool_byclaude/
├── app/                  # 保持现有结构
├── docs/                 # 📁 新增：统一文档目录
│   ├── api/             # API文档
│   ├── deployment/      # 部署文档
│   └── architecture/    # 架构设计文档
├── scripts/             # 📁 新增：工具脚本
├── tests/               # 📁 重命名：标准化测试目录
├── archive/             # 📁 新增：归档目录
│   ├── deprecated/      # 废弃代码/文档
│   └── process/         # 过程性文档
└── .github/             # 📁 新增：GitHub工作流
```

---

## 分类与处理规则

### 1. 保留文件
- **核心代码**：`app/`, `templates/`, `static/`, `migrations/`
- **配置文件**：`config.py`, `run.py`, `requirements*.txt`
- **项目文档**：`README.md`, `PRD*.md`, `.gitignore`
- **数据库**：`instance/app.db` (开发环境)

### 2. 需要整理的文件
- **工具脚本** → `scripts/`：
  - `check_*.py`, `clean_*.py`, `fix_*.py`
  - `batch_download_files.py`, `data_*.py`
- **测试文档** → `docs/` 或 `archive/process/`：
  - `test/doc/` 下的技术文档
  - 临时调试文件
- **废弃文件** → `archive/deprecated/`：
  - `.backup` 文件
  - 过时的配置文件

### 3. 可安全删除
- **构建产物**：`__pycache__/`, `*.pyc`
- **日志文件**：`*.log`, `app.log`
- **临时文件**：`.DS_Store`, 临时JSON文件
- **上传缓存**：`uploads/` (如果存在)

---

## Git备份前文档同步流程

### A. 收集已完成任务
**数据源优先级**：
1. **Git提交记录**：分析 `feat:`, `fix:`, `refactor:` 类型的提交
2. **代码变更**：检测新增的API端点、模型字段、服务功能
3. **PRD更新**：对比PRD.md中的需求完成状态
4. **测试文档**：`test/doc/` 中的功能验证记录

**时间窗口**：从上次文档同步标记到当前HEAD

**输出格式**：
```json
{
  "id": "TASK-2024-01-15-001",
  "title": "新增TaskOutput模型支持本地文件存储",
  "summary": "实现任务输出文件的本地存储和9:16缩略图生成",
  "scope": "app/models/TaskOutput.py, app/services/file_manager.py",
  "type": "feat",
  "breaking": false,
  "impacts": ["数据库schema变更", "新增API端点 /api/outputs"],
  "test_coverage": "手动测试通过，覆盖文件上传下载流程"
}
```

### B. 更新PRD文档
- **目标文件**：`PRD.md`
- **更新策略**：
  - 在"变更记录"章节顶部插入新完成的功能
  - 更新"核心模块结构"中的实现状态标记 (✅/🚧/❌)
  - 同步API接口文档和数据模型变更

### C. 更新README文档
- **核心功能**章节：突出新增/改进的用户价值
- **项目结构**：反映最新的目录组织
- **安装部署**：更新依赖和配置要求
- **API使用**：补充新增端点的示例

### D. 生成CHANGELOG
- **格式**：遵循 [Keep a Changelog](https://keepachangelog.com/) 标准
- **版本策略**：
  - `feat` → Minor版本 (0.x.0)
  - `fix` → Patch版本 (0.0.x)
  - Breaking changes → Major版本 (x.0.0)

### E. 技术文档整理
- **API文档**：从Flask路由自动生成OpenAPI规范
- **数据库文档**：从SQLAlchemy模型生成ER图
- **部署文档**：整合`test/doc/Deploy.md`到标准位置

---

## 执行步骤

### 1. 项目分析阶段
```bash
# 扫描项目结构
find . -type f -name "*.py" | head -20
find . -type f -name "*.md" | grep -v node_modules

# 分析Git历史
git log --oneline --since="2024-01-01" --grep="feat\|fix\|refactor"

# 检查数据库模型
python -c "from app.models import *; print([cls.__name__ for cls in db.Model.__subclasses__()])"
```

### 2. Dry-Run预览
输出内容：
- **📋 目录重组计划**：文件移动/重命名清单
- **📝 文档更新预览**：PRD/README/CHANGELOG的具体变更
- **🔍 风险评估**：潜在的导入路径变更和链接失效
- **🧪 测试建议**：需要验证的功能点

### 3. 文档同步执行
```bash
# 1. 创建文档同步分支
git checkout -b docs/sync-$(date +%Y%m%d)

# 2. 执行文档更新
python scripts/sync_docs.py --dry-run=false

# 3. 提交文档变更
git add PRD.md README.md CHANGELOG.md docs/
git commit -m "docs: sync completed features to project docs

- Update PRD with TaskOutput model implementation
- Refresh README core features section  
- Generate CHANGELOG entries since last sync"

# 4. 合并到主分支
git checkout main && git merge docs/sync-$(date +%Y%m%d)
```

### 4. 项目重构执行
```bash
# 1. 创建重构分支
git checkout -b refactor/restructure-$(date +%Y%m%d)

# 2. 执行目录整理
python scripts/restructure_project.py

# 3. 修复导入路径
python scripts/fix_imports.py

# 4. 运行测试验证
python -m pytest tests/ || python run.py --test-mode

# 5. 提交重构变更
git add -A
git commit -m "refactor: standardize project structure

- Move utility scripts to scripts/ directory
- Reorganize documentation under docs/
- Archive deprecated files to archive/
- Update import paths and references"
```

---

## Flask项目特定配置

### 环境变量管理
```bash
# .env 文件示例
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///instance/app.db
RUNNINGHUB_API_KEY=your-api-key
```

### 数据库迁移处理
```bash
# 备份当前数据库
cp instance/app.db instance/app.db.backup

# 检查迁移状态
flask db current

# 如有schema变更，生成新迁移
flask db migrate -m "Add new fields for project restructure"
flask db upgrade
```

### 静态文件路径更新
- 检查 `templates/` 中的静态资源引用
- 更新 `static/` 目录下的相对路径
- 验证 `app/routes.py` 中的文件服务路由

---

## MCP/AI IDE 建议指令与参数（示例）
- 配置项（可通过环境或命令参数传入）：
  ```ini
  non_interactive=false
  allow_version_bump=true
  force=false
  prd_path=docs/PRD.md
  readme_path=README.md
  changelog_path=CHANGELOG.md
  adr_dir=docs/adr
  meta_path=.sync-meta.json
  from_ref=<last_tag_or_meta>
  to_ref=HEAD
  ```
- 伪指令序列（MCP 工具可映射到具体能力）：
  ```python
  repo.detect_stack()
  docs.scan_tasks(sources=[TASKS.md, TODO.md, github.issues, git.commits(from_ref,to_ref), github.prs(from_ref,to_ref)])
  docs.normalize_tasks()
  docs.preview_updates(targets=[PRD.md, README.md, CHANGELOG.md], adr_dir)
  lint.markdown(); test.run(); build.run()
  if checks_passed and docs.diff_exists:
      git.add([PRD.md, README.md, CHANGELOG.md, ADR/*])
      git.commit("docs: sync completed tasks to PRD/README/CHANGELOG")
  else:
      abort("Docs preflight failed or no-op")
  # 然后再进入清理/归档分支工作流…
  git.checkout_new("chore/restructure-<date>")
  refactor.apply_moves()
  links.fix_imports_and_docs()
  qa.run_all()
  version.bump_if_needed()
  git.commit("chore: restructure repository")
  github.create_pr(base=main, head=current_branch, title, body)
  ```

---

## 安全与边界
- **绝不读取或输出密钥/凭据内容**；仅定位路径并提示整改  
- 不改业务逻辑；对大型仓库分批  
- 提交原子化，信息遵循 Conventional Commits  
- 构建/测试失败则阻断后续 Git 操作（除非 `--force`）

---

## 开始执行
请立即：
1) 识别项目与目录结构  
2) 输出**分析阶段**与**Dry-Run 阶段**报告（含“Preflight 文档同步计划”预览）  
3) 等我确认或加 `--yes` 后再进行执行阶段与 PR 创建

---

> 小贴士：把本提示保存为 “**项目整理 + 备份前文档同步（安全版）**”。每次仓库复用时，仅需更新“项目上下文/路径/参数”几处即可。
