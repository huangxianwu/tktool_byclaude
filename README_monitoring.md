# 数据一致性监控系统

## 概述

本监控系统专门用于解决9月15日后出现的TaskOutput数据保存问题，提供全面的数据一致性检查、自动告警和数据修复功能。

## 功能特性

### 1. 数据完整性检查
- **缺失TaskOutput检测**: 自动检测SUCCESS任务但缺失TaskOutput记录的情况
- **创建延迟监控**: 监控TaskOutput创建时间是否异常延迟
- **数据趋势分析**: 分析数据完整性的历史趋势变化
- **数据库性能监控**: 检测异常的数据量和性能问题

### 2. 自动告警机制
- **多级告警**: 支持低、中、高、严重四个告警级别
- **实时通知**: 严重问题立即通知（支持扩展邮件、钉钉等）
- **告警历史**: 完整的告警记录和历史追踪
- **智能过滤**: 避免重复告警和噪音

### 3. 数据修复功能
- **自动补偿**: 自动为缺失TaskOutput的任务创建记录
- **批量修复**: 支持批量处理历史数据问题
- **安全检查**: 修复前进行数据完整性验证
- **回滚机制**: 支持修复操作的回滚

### 4. 监控调度
- **定时检查**: 支持快速检查(15分钟)、完整检查(1小时)、深度检查(每日)
- **手动触发**: 支持通过API手动触发各种类型的检查
- **状态监控**: 实时监控系统运行状态

## 文件结构

```
├── app/
│   ├── services/
│   │   └── data_monitor.py          # 数据监控核心服务
│   ├── utils/
│   │   └── timezone_helper.py       # 时区处理工具
│   └── api/
│       └── monitoring.py            # 监控API接口（已扩展）
├── data_integrity_check.py          # 数据完整性检查脚本
├── data_compensation.py             # 数据补偿修复脚本
├── monitoring_scheduler.py          # 监控调度器
├── requirements_monitoring.txt      # 监控系统依赖
└── README_monitoring.md            # 本文档
```

## 安装和配置

### 1. 安装依赖
```bash
pip install -r requirements_monitoring.txt
```

### 2. 创建日志目录
```bash
mkdir -p logs/alerts logs/monitoring_results logs/errors
```

### 3. 配置数据库
确保数据库连接配置正确，监控系统会使用现有的数据库连接。

## 使用方法

### 1. 数据完整性检查

#### 手动执行检查脚本
```bash
# 检查9月15日前后的数据差异
python data_integrity_check.py

# 检查特定日期范围
python data_integrity_check.py --start-date 2024-09-10 --end-date 2024-09-20

# 生成详细报告
python data_integrity_check.py --detailed-report
```

#### 通过API触发检查
```bash
# 快速检查（检查过去1小时）
curl -X POST http://localhost:5000/api/monitoring/data-consistency/check \
  -H "Content-Type: application/json" \
  -d '{"type": "quick"}'

# 完整检查（检查过去24小时）
curl -X POST http://localhost:5000/api/monitoring/data-consistency/check \
  -H "Content-Type: application/json" \
  -d '{"type": "full"}'

# 深度检查（包含趋势分析）
curl -X POST http://localhost:5000/api/monitoring/data-consistency/check \
  -H "Content-Type: application/json" \
  -d '{"type": "deep"}'
```

### 2. 数据修复

#### 自动补偿缺失数据
```bash
# 补偿9月15日后的缺失数据
python data_compensation.py --start-date 2024-09-15

# 补偿特定任务
python data_compensation.py --task-ids task_id_1,task_id_2,task_id_3

# 批量补偿（限制数量）
python data_compensation.py --batch-size 100 --max-tasks 1000

# 预览模式（不实际修复）
python data_compensation.py --dry-run
```

### 3. 启动监控调度器

#### 后台运行监控调度器
```bash
# 启动监控调度器
python monitoring_scheduler.py

# 后台运行
nohup python monitoring_scheduler.py > logs/scheduler.log 2>&1 &
```

#### 监控调度器功能
- **快速检查**: 每15分钟检查过去1小时的数据
- **完整检查**: 每小时检查过去24小时的数据
- **深度检查**: 每天凌晨2点检查过去2周的趋势

### 4. API接口使用

#### 获取数据一致性指标
```bash
curl http://localhost:5000/api/monitoring/data-consistency/metrics
```

#### 获取系统健康状态
```bash
curl http://localhost:5000/api/monitoring/health
```

#### 获取告警历史
```bash
curl http://localhost:5000/api/monitoring/alerts?limit=50
```

## 监控指标说明

### 数据完整性指标
- **completion_rate**: TaskOutput完整率（SUCCESS任务中有TaskOutput记录的比例）
- **tasks_with_outputs**: 有TaskOutput记录的任务数量
- **avg_outputs_per_task**: 每个任务平均的TaskOutput数量

### 健康状态判断
- **healthy**: 完整率 >= 95%
- **degraded**: 完整率 80-95%
- **unhealthy**: 完整率 < 80%

### 告警级别
- **low**: 轻微问题，完整率 95-100%
- **medium**: 中等问题，完整率 80-95%
- **high**: 严重问题，完整率 50-80%
- **critical**: 紧急问题，完整率 < 50%

## 日志和文件说明

### 日志文件
- `logs/monitoring.log`: 监控系统运行日志
- `logs/scheduler.log`: 调度器运行日志
- `logs/alerts/`: 严重告警详细信息
- `logs/monitoring_results/`: 每日监控结果
- `logs/errors/`: 监控系统错误日志

### 监控结果文件
- 按日期组织: `monitoring_YYYYMMDD.jsonl`
- 每行一个JSON记录，包含完整的监控结果
- 可用于历史数据分析和趋势追踪

## 故障排除

### 常见问题

1. **数据库连接失败**
   - 检查数据库配置
   - 确认数据库服务正常运行
   - 检查网络连接

2. **监控调度器无法启动**
   - 检查Python环境和依赖包
   - 确认日志目录权限
   - 查看错误日志

3. **告警通知不工作**
   - 检查通知配置（邮件、钉钉等）
   - 确认网络连接
   - 查看告警日志

4. **数据修复失败**
   - 检查任务状态和RunningHub连接
   - 确认数据库写入权限
   - 使用预览模式测试

### 调试模式

启用详细日志：
```bash
export LOG_LEVEL=DEBUG
python monitoring_scheduler.py
```

## 扩展和定制

### 添加新的监控检查
在 `app/services/data_monitor.py` 中添加新的检查方法：

```python
def check_custom_metric(self) -> List[DataConsistencyAlert]:
    """自定义监控检查"""
    alerts = []
    # 实现检查逻辑
    return alerts
```

### 集成通知系统
在 `monitoring_scheduler.py` 中扩展通知方法：

```python
def _send_email_notification(self, alerts):
    """发送邮件通知"""
    # 实现邮件发送逻辑
    pass

def _send_dingtalk_notification(self, alerts):
    """发送钉钉通知"""
    # 实现钉钉机器人通知逻辑
    pass
```

## 性能优化建议

1. **数据库查询优化**
   - 为 `Task.completed_at` 和 `TaskOutput.created_at` 添加索引
   - 使用分页查询处理大量数据

2. **监控频率调整**
   - 根据系统负载调整检查频率
   - 在业务低峰期执行深度检查

3. **日志管理**
   - 定期清理旧的日志文件
   - 使用日志轮转避免文件过大

## 联系和支持

如有问题或需要支持，请查看：
1. 系统日志文件
2. 监控结果文件
3. 告警历史记录

建议定期检查监控系统状态，确保数据一致性问题得到及时发现和处理。