
# 🧭 Project Rules — AI 辅助开发与文档同步流程规范

> 版本：v1.0  
> 目标：确保 AI 开发、人工确认、文档更新、版本追溯四者一致。

---

## 🎯 核心目标

1. **保证一致性**：代码改动、PRD、README、CHANGELOG 必须保持一致。  
2. **人工主导确认**：人类确认是唯一的“生效触发点”。  
3. **可追溯性**：每个功能任务对应独立节点，可快速回滚与重构。  
4. **可维护性**：通过自动化同步脚本 / 智能体确保更新闭环。

---

## 🧩 整体流程概览

```
需求提出 → AI生成方案/代码 → 人类审查 → 确认/拒绝 → 自动文档同步/忽略 → 调整与回滚机制
```

---

## 🧱 流程分解

### 🔹 步骤1：任务创建

- 所有新功能、Bug 修复、调试任务，都应以以下形式记录：
  - `TASKS.md` / `TODO.md` 中创建条目；
  - 或通过 PR/Issue 标注 `task:<编号>`；
  - 每个任务应包含：
    - 描述（Description）
    - 目标（Goal）
    - 预期行为（Acceptance Criteria）
    - 关联文件（Scope）
    - 优先级（Priority）

> 💡 建议任务命名规范：`TASK-YYYYMMDD-XX`  
> 例如：`TASK-20250929-01: 支持用户画像接口优化`

---

### 🔹 步骤2：AI 执行与结果审查

- 当 AI IDE 根据任务要求生成或修改代码后，会触发**人工审查阶段**：
  - 系统提示：“是否接受此次修改？”
  - 用户需明确选择：
    - ✅ **确认修改**：表示代码逻辑已认可；
    - ❌ **拒绝修改**：表示代码不合格或不符合需求。

> 💡 **仅当确认修改后，才会进入文档同步流程。**

---

### 🔹 步骤3：确认修改后，触发文档同步

当用户点击「确认修改文件」后，自动执行以下操作：

1. **提取任务上下文**（AI 任务描述、提交摘要、改动文件范围）；
2. **同步更新以下文档**：
   - `docs/PRD.md`：更新需求变更记录；
   - `README.md`：更新 Features / Usage；
   - `CHANGELOG.md`：增加 “Added / Changed”；
   - `docs/adr/`：若涉及架构决策，生成 ADR；
3. **写入任务完成记录**：
   - 在 `TASKS.md` 中标记状态为 ✅ Done；
   - 追加完成时间与提交哈希；
4. **自动提交日志**：
   ```bash
   git commit -m "docs: sync PRD & README for TASK-20250929-01"
   ```

---

### 🔹 步骤4：拒绝修改时的行为

- 若用户选择 **拒绝修改文件**：
  - 系统记录状态：`TASK.status = Rejected`
  - **不触发文档同步**
  - **不更改 PRD / README / CHANGELOG**
  - **不影响当前版本号**

> ⚠️ 拒绝后，AI IDE 不得自动更新任何文档，以防造成文档污染。

---

### 🔹 步骤5：任务后续调整

- 若在后续开发中，**调整了已确认的任务逻辑**，应立即同步文档：
  1. 在对应任务记录中追加修订标记：
     ```md
     ✅ TASK-20250929-01 - 修订于 2025-10-02（新增接口参数 userType）
     ```
  2. 触发 **PRD / README / CHANGELOG 更新流程**
  3. 自动生成 `docs/adr/ADR-20251002-task-20250929-01.md` 记录设计变更
  4. 提交：
     ```bash
     git commit -m "docs: update PRD/README for TASK-20250929-01 revision"
     ```

---

### 🔹 步骤6：功能回滚与同步

- 若需回滚到某一功能版本：
  1. 查找任务节点：可通过 `TASKS.md` 或 `git log` 查询：
     ```bash
     git log --grep "TASK-20250929-01"
     ```
  2. 回滚对应提交：
     ```bash
     git revert <commit-id> 或 git checkout <tag-version>
     ```
  3. 同步文档：
     - 在 `PRD.md`、`README.md`、`CHANGELOG.md` 中标记：
       ```md
       ❌ [Rollback] TASK-20250929-01 功能回滚于 2025-10-03
       ```
  4. 提交记录：
     ```bash
     git commit -m "docs: mark rollback for TASK-20250929-01"
     ```

> 💡 可启用脚本自动执行：
> `npm run sync:rollback TASK-20250929-01`

---

### 🔹 步骤7：文档与代码一致性校验

每次提交或构建前，运行自动检查：

```bash
npm run docs:check-sync
```

该命令验证以下一致性：

| 检查项 | 说明 |
|--------|------|
| TASKS.md 状态 vs 代码改动 | 所有 Done 的任务应在 PRD / README 中反映 |
| PRD.md vs CHANGELOG.md | 每个变更在两者中都有记录 |
| README.md Features vs 实现 | 新特性对应代码提交存在 |
| ADR vs 代码结构 | 架构决策文件与目录结构对应 |

如发现不一致，阻断提交（通过 pre-commit hook / CI 检查）。

---

## 🔁 自动化命令建议

| 命令 | 功能说明 |
|------|----------|
| `npm run task:new` | 创建新任务模板 |
| `npm run task:done TASK-ID` | 标记任务完成并触发文档同步 |
| `npm run task:reject TASK-ID` | 标记任务拒绝 |
| `npm run task:revise TASK-ID` | 更新任务与文档 |
| `npm run task:rollback TASK-ID` | 回滚功能与文档 |
| `npm run docs:check-sync` | 检查文档一致性 |

---

## ✅ 最佳实践

- 每次 AI 修改都应关联任务编号；
- 不接受“无任务编号”的提交；
- 确认修改后立即同步文档；
- 回滚时同步标注，避免“幽灵功能”；
- PRD 永远是“当前产品状态”的单一真相源。

---

## 📚 附录：示例提交记录

```bash
feat(api): 支持用户画像接口优化 - TASK-20250929-01
docs(prd): 更新 PRD.md & README.md
fix(api): 修复用户画像返回数据 - TASK-20251001-02
docs: update CHANGELOG.md
rollback(task): 回滚用户画像优化 TASK-20250929-01
docs: mark rollback in PRD.md
```
