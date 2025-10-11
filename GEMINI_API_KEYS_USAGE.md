# Gemini API Keys 多密钥管理功能

## 功能概述

本系统支持配置多个 Gemini API keys，当其中一个因为额度问题失效时，会自动切换到另一个可用的 API key，确保服务的连续性。

## 配置方式

### 1. 在 config.py 中直接配置

在 `config.py` 文件中的 `GEMINI_API_KEYS` 列表中添加你的 API keys：

```python
GEMINI_API_KEYS = [
    'AIzaSyDXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX1',  # 主要API key
    'AIzaSyDXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX2',  # 备用API key 1
    'AIzaSyDXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX3',  # 备用API key 2
    # 可以添加更多...
]
```

### 2. 通过环境变量配置

系统也支持通过环境变量配置 API keys，环境变量的优先级高于配置文件：

```bash
export GEMINI_API_KEY="your_primary_key"
export GOOGLE_API_KEY="your_google_key"
export GEMINI_API_KEY_2="your_backup_key_1"
export GEMINI_API_KEY_3="your_backup_key_2"
```

## 自动切换机制

### 触发条件

系统会在以下情况下自动切换到下一个可用的 API key：

1. **配额错误**：当前 key 的配额已用完
2. **认证错误**：当前 key 无效或被禁用
3. **速率限制**：请求频率超过限制

### 错误检测

系统能够识别以下错误类型并触发切换：

- `quota exceeded`
- `rate limit`
- `too many requests`
- `invalid api key`
- `authentication failed`
- `unauthorized`
- HTTP 状态码 `429` (Too Many Requests)
- HTTP 状态码 `401` (Unauthorized)

### 切换策略

- **循环切换**：按顺序切换到下一个 key，到达末尾后回到第一个
- **最小间隔**：两次切换之间至少间隔 60 秒，避免频繁切换
- **自动重试**：每个 key 最多重试 3 次，失败后切换到下一个

## 使用方法

### 在代码中使用

系统已经集成到 AI Editor 中，无需手动调用。当 Gemini API 调用失败时，会自动处理切换逻辑。

### 手动管理（如需要）

```python
from config import Config
from app.utils.gemini_key_manager import gemini_key_manager

# 获取当前 key
current_key = Config.get_current_gemini_key()

# 手动切换到下一个 key
Config.switch_to_next_gemini_key()

# 重置到第一个 key
Config.reset_gemini_key_index()

# 获取所有可用的 keys
all_keys = Config.get_all_gemini_keys()

# 使用管理器执行带重试的函数
result = gemini_key_manager.execute_with_retry(your_function, *args, **kwargs)
```

## 监控和日志

### 切换日志

当发生 key 切换时，系统会输出日志：

```
已切换到备用Gemini API key (索引: 1)
```

### 状态查询

可以查询当前管理器状态：

```python
status = gemini_key_manager.get_status()
print(status)
# 输出：
# {
#     'current_key_index': 0,
#     'total_keys': 3,
#     'available_keys': 3,
#     'failed_keys': [],
#     'last_switch_time': None
# }
```

## 最佳实践

1. **配置多个有效的 API keys**：建议至少配置 2-3 个不同的 API keys
2. **监控配额使用**：定期检查各个 key 的配额使用情况
3. **设置告警**：当所有 keys 都失效时，系统会返回错误，建议设置监控告警
4. **定期轮换**：定期更新和轮换 API keys，确保安全性

## 故障排除

### 所有 keys 都失效

如果所有配置的 API keys 都失效，系统会返回错误信息：

```
所有Gemini API keys都已失效，请检查配额或更新API keys
```

此时需要：
1. 检查各个 key 的配额状态
2. 更新失效的 keys
3. 重启应用以重新加载配置

### 切换过于频繁

如果发现切换过于频繁，可能是：
1. 所有 keys 的配额都接近耗尽
2. 网络问题导致的临时错误被误判

建议检查网络连接和 API key 状态。

## 注意事项

1. **安全性**：不要在代码中硬编码真实的 API keys，示例中的 keys 仅为占位符
2. **配额管理**：合理分配各个 key 的使用，避免同时耗尽所有配额
3. **成本控制**：多个 keys 意味着更多的潜在费用，请注意成本控制
4. **合规性**：确保所有 API keys 的使用符合 Google 的服务条款