# 任务管理系统 PRD (Product Requirements Document)

## 1. 项目概述
设计并实现一个RunningHub工作流任务管理系统，支持任务的创建、排队、执行和监控功能。

## 2. 核心约束条件
- **并发限制**: RunningHub一次只能处理1个任务（可在config中配置）
- **任务顺序**: 按创建时间先后顺序执行（FIFO）
- **超时机制**: 任务执行超时30分钟自动标记为失败

## 3. 任务状态流转

### 3.1 任务状态定义
```
READY    → 任务创建完成，资源文件已上传，可以启动
PENDING  → 点击启动后，任务进入排队等待状态  
QUEUED   → RunningHub返回状态：任务已接收排队
RUNNING  → RunningHub返回状态：任务正在执行
SUCCESS  → RunningHub返回状态：任务执行成功
FAILED   → 任务执行失败（RunningHub返回或30分钟超时）
STOPPED  → 用户手动停止任务
```

### 3.2 状态流转规则
```
READY → PENDING (用户点击启动)
PENDING → QUEUED/RUNNING (提交到RunningHub)
QUEUED → RUNNING → SUCCESS/FAILED (RunningHub状态更新)
任何状态 → STOPPED (用户点击停止)
FAILED/STOPPED → PENDING (用户点击重新启动)
```

## 4. 功能需求

### 4.1 任务队列管理
- **队列控制**: 同时只有1个任务可以在RunningHub中执行
- **排队逻辑**: PENDING状态任务按created_at时间升序排队
- **自动调度**: 当前任务完成/停止后，自动启动下一个PENDING任务

### 4.2 任务操作功能
- **启动任务**: READY/FAILED/STOPPED状态可启动
- **停止任务**: PENDING/QUEUED/RUNNING状态可停止
- **删除任务**: 任何状态都可删除（需确认）
- **重新启动**: FAILED/STOPPED状态可重新启动

### 4.3 状态监控
- **实时状态**: 定期轮询RunningHub获取最新状态
- **超时处理**: 30分钟无响应自动标记FAILED
- **错误处理**: 网络异常、API错误的处理机制

## 5. UI界面设计

### 5.1 任务列表展示
```
| 选择 | 工作流名称 | 任务ID | 节点数 | 状态 | 创建时间 | 详情 | 操作 |
|-----|----------|--------|-------|------|----------|-----|------|
| □   | 图片合成  | abc123 | 2     | READY| 2025-09-11| 查看 | 启动/删除 |
```

### 5.2 单个任务操作按钮
- **启动按钮**: 仅在 READY/FAILED/STOPPED 状态显示
- **停止按钮**: 仅在 PENDING/QUEUED/RUNNING 状态显示  
- **删除按钮**: 所有状态都显示

### 5.3 批量操作逻辑
批量操作的可选择性与单个任务操作按钮的显示逻辑完全一致：

- **任务选择框显示规则**:
  - 可启动状态任务（READY/FAILED/STOPPED）: 显示选择框
  - 可停止状态任务（PENDING/QUEUED/RUNNING）: 显示选择框
  - 可删除状态任务（所有状态）: 显示选择框

- **批量操作按钮**:
  - **批量启动**: 仅当选中的任务都是 READY/FAILED/STOPPED 状态时可用
  - **批量停止**: 仅当选中的任务都是 PENDING/QUEUED/RUNNING 状态时可用
  - **批量删除**: 选中任何状态的任务都可用（需确认）

- **混合状态处理**:
  - 如果选中任务包含不同状态，则根据选中任务的状态组合动态显示可用的批量操作按钮
  - 例如：选中1个READY和1个RUNNING任务时，只显示批量删除按钮

### 5.4 状态指示器
- **READY**: 绿色 🟢 
- **PENDING**: 黄色 🟡
- **QUEUED**: 蓝色 🔵
- **RUNNING**: 橙色 🟠
- **SUCCESS**: 深绿 🟢
- **FAILED**: 红色 🔴
- **STOPPED**: 灰色 ⚫

## 6. 技术实现要点

### 6.1 配置参数
```python
# config.py 新增
MAX_CONCURRENT_TASKS = 1  # 最大并发任务数
TASK_TIMEOUT_MINUTES = 30  # 任务超时时间
STATUS_CHECK_INTERVAL = 10  # 状态检查间隔（秒）
```

### 6.2 数据库变更
```python
# Task模型需要新增字段
class Task(db.Model):
    # 现有字段保持不变
    timeout_at = db.Column(db.DateTime)  # 超时时间
    started_at = db.Column(db.DateTime)  # 开始执行时间
    completed_at = db.Column(db.DateTime)  # 完成时间
```

### 6.3 核心服务
- **TaskQueueService**: 任务队列管理服务
- **TaskStatusService**: 任务状态监控服务  
- **TaskController**: 任务执行控制器

### 6.4 API接口
```
GET /api/tasks - 获取任务列表
POST /api/tasks/{id}/start - 启动任务
POST /api/tasks/{id}/stop - 停止任务
DELETE /api/tasks/{id} - 删除任务
GET /api/tasks/{id}/status - 获取任务状态
POST /api/tasks/batch/start - 批量启动任务
POST /api/tasks/batch/stop - 批量停止任务
DELETE /api/tasks/batch - 批量删除任务
```

## 7. 用户体验

### 7.1 实时更新
- 任务状态自动刷新（WebSocket或定时轮询）
- 操作结果即时反馈
- 错误提示清晰明确

### 7.2 交互优化
- 危险操作需确认（删除、停止）
- 按钮状态根据任务状态动态显示
- 批量操作按钮根据选中任务状态动态启用/禁用
- 加载状态和进度指示
- 全选/取消全选功能

## 8. 异常处理

### 8.1 常见异常
- RunningHub API不可用
- 任务执行超时
- 网络连接中断
- 文件上传失败
- 批量操作部分失败

### 8.2 处理策略
- 自动重试机制
- 错误日志记录
- 用户友好的错误提示
- 失败任务可重新启动
- 批量操作失败时提供详细的成功/失败报告

---

**此PRD定义了任务管理系统的完整功能规范，确保批量操作与单个操作的逻辑完全一致。**