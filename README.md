# RunningHub 工作流自动化平台

基于 Flask 构建的工作流自动化执行平台，集成 RunningHub AI 服务。

## 功能特性

- 📋 可视化工作流模板管理
- 📤 文件上传与预处理
- 🤖 AI 任务自动化执行
- 📊 实时日志追踪（含完整 API 参数）
- 🎯 结果文件预览（图片/视频）
- 🔄 SSE 实时日志流

## 技术栈

- **后端**: Flask + SQLAlchemy + SQLite
- **前端**: 原生 JavaScript + HTML5 + CSS3
- **API**: RunningHub OpenAPI
- **实时通信**: Server-Sent Events (SSE)

## 安装运行

1. 安装依赖:
```bash
pip install -r requirements.txt
```

2. 运行应用:
```bash
python run.py
```

3. 访问应用:
打开浏览器访问 `http://localhost:5000`

## API 配置

应用使用以下 RunningHub 配置（可在 `config.py` 中修改）:

```python
RUNNINGHUB_BASE_URL = 'https://www.runninghub.cn/task/openapi'
RUNNINGHUB_WEBAPP_ID = '1877265245566922753'
RUNNINGHUB_API_KEY = 'd4b17e6ea9474695965f3f3c9dd53c1d'
```

## 使用流程

1. **创建工作流模板**: 定义输入字段（文本、数字、图片、视频）
2. **创建任务**: 根据模板填写表单，上传文件
3. **执行任务**: 自动调用 RunningHub AI 服务
4. **监控进度**: 实时查看执行日志和状态
5. **查看结果**: 预览生成的图片/视频文件

## 项目结构

```
├── app/
│   ├── models/          # 数据模型
│   ├── managers/        # 任务管理
│   ├── services/        # 外部服务
│   ├── api/            # API 端点
│   └── __init__.py     # 应用工厂
├── templates/          # HTML 模板
├── static/            # 静态资源
├── config.py          # 配置文件
├── run.py            # 启动脚本
└── requirements.txt   # 依赖列表
```

## 核心功能

### 文件上传
- 支持图片、视频、音频、压缩包
- 自动上传至 RunningHub
- 获取 fileName 用于后续处理

### 任务执行
- 异步任务队列管理
- 状态轮询（每10秒）
- 完整的错误处理

### 日志系统
- 实时日志流（SSE）
- 包含完整 API 请求参数
- 时间轴式执行记录

### 结果预览
- 图片直接显示
- 视频在线播放
- 文件下载链接