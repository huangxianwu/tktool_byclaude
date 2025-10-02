# TK Tool 项目清理确认清单

## 清理概述

本次清理共识别出 **30个文件**，总大小约 **103.14 MB**，已按照清理建议分类归档到 `archive_for_cleanup/` 目录。

### 清理统计
- ✅ **确定删除**: 8个文件 (系统文件、空文件)
- ⚠️ **建议删除**: 10个文件 (临时文件、日志、备份)
- 🔍 **需要审核**: 12个文件 (可能包含重要数据)

---

## 📁 确定删除的文件 (definitely_remove/)

这些文件可以**安全删除**，不会影响项目功能：

### 系统生成文件
- `.DS_Store` (6KB) - macOS系统文件
- `.sync-meta.json` (265B) - 同步元数据文件
- `temp/.DS_Store` (6KB) - 临时目录系统文件
- `static/outputs/videos/.DS_Store` (8KB) - 输出目录系统文件

### 空文件
- `app.db` (0B) - 空数据库文件，实际数据在 `instance/app.db`
- `task_manager.db` (0B) - 空数据库文件
- `tasks.db` (0B) - 空数据库文件
- `debug_source_display.js` (0B) - 空的调试JS文件

**建议操作**: 直接删除 `archive_for_cleanup/definitely_remove/` 目录

---

## ⚠️ 建议删除的文件 (probably_remove/)

这些文件**建议删除**，但请先确认：

### 临时文件 (temp/doc/)
- `TEMP_PROJECT_RULES.md` (5.4KB) - 临时项目规则文档
- `遮罩编辑器.md` (6.8KB) - 遮罩编辑器说明文档
- `黑帽男+1&2.mp4` (9.8MB) - 测试视频文件
- `9月10日-煤气罐-片段集-3.mp4` (11.9MB) - 测试视频文件
- `26125534357-1-192.mp4` (31.7MB) - 测试视频文件

### 调试文件
- `tests/debug_runninghub_fieldname_1972135780502159362.py` (5.6KB) - 调试脚本

### 日志文件
- `app.log` (51.9KB) - 应用日志
- `scripts/deploy_test.log` (1.3KB) - 部署测试日志

### 备份文件
- `archive/deprecated/task_create.html.backup` (35.9KB) - HTML模板备份

**建议操作**: 
1. 检查视频文件是否还需要用于测试
2. 确认日志文件不包含重要调试信息
3. 确认后删除 `archive_for_cleanup/probably_remove/` 目录

---

## 🔍 需要审核的文件 (review_required/)

这些文件**需要仔细审核**后决定是否删除：

### 图片素材 (temp/doc/)
- `产品图.png` (118B) - 产品图片
- `大妈-白色tshirt.png` (1MB) - 测试图片素材
- `产品1.png` (811KB) - 产品图片
- `橄榄绿.png` (2.7MB) - 颜色样本图片
- `模特1.png` - 模特图片
- `模特图.png` - 模特图片

### 工作流配置 (temp/doc/)
- `WanVACE衣服替换_正式版_api.json` (13.3KB) - 衣服替换工作流API配置
- `正式版 _ InfiniteTalk视频+音频对口型OK（优化版）_api.json` (11.6KB) - 对口型工作流API配置
- `正式版 _ InfiniteTalk视频+音频对口型OK（优化版）.json` - 对口型工作流配置
- `1962342403615166465-背景替换工作流.json` - 背景替换工作流配置

**审核要点**:
1. **图片素材**: 是否还需要用于测试或演示？
2. **工作流配置**: 是否包含重要的配置参数或模板？
3. **API配置**: 是否包含生产环境的配置信息？

**建议操作**: 
1. 逐个检查文件内容
2. 重要的工作流配置可以移动到 `docs/examples/` 目录
3. 不再需要的测试素材可以删除

---

## 🔧 清理操作步骤

### 第一步：删除确定文件
```bash
# 删除确定可以删除的文件
rm -rf archive_for_cleanup/definitely_remove/
```

### 第二步：审核建议删除文件
```bash
# 查看建议删除的文件
ls -la archive_for_cleanup/probably_remove/
# 确认后删除
rm -rf archive_for_cleanup/probably_remove/
```

### 第三步：审核需要确认的文件
```bash
# 逐个检查需要审核的文件
find archive_for_cleanup/review_required/ -type f -exec ls -lh {} \;
# 选择性保留或删除
```

### 第四步：清理归档目录
```bash
# 完成清理后删除归档目录
rm -rf archive_for_cleanup/
```

---

## 📊 清理效果

### 预期清理效果
- **释放空间**: 约103MB
- **减少文件数**: 30个文件
- **提升项目整洁度**: 移除临时文件、系统文件、空文件

### 保留的重要文件
- 所有源代码文件
- 正常的输出文件 (`static/outputs/`)
- 实际使用的数据库 (`instance/app.db`)
- 项目配置和文档

---

## ⚠️ 注意事项

1. **备份重要数据**: 清理前确保重要数据已备份
2. **测试功能**: 清理后测试主要功能是否正常
3. **恢复机制**: 如需恢复文件，可从 `archive_for_cleanup/move_record.json` 查看原始路径
4. **分批清理**: 建议先清理确定删除的文件，再逐步处理其他文件

---

## 📝 清理记录

- **分析日期**: 2025-10-02
- **归档位置**: `archive_for_cleanup/`
- **移动记录**: `archive_for_cleanup/move_record.json`
- **详细分析**: `cleanup_plan.json`

完成清理后，请更新此清单并记录实际清理的文件。