# Git认证配置指南

## 概述

本指南详细介绍如何在Windows系统上配置Git认证，支持GitHub Personal Access Token和传统用户名密码两种方式。

## 方法一：GitHub Personal Access Token（推荐）

### 为什么推荐使用Token？
- ✅ 更安全：可以设置特定权限和过期时间
- ✅ 更稳定：不受密码更改影响
- ✅ 更灵活：可以为不同项目创建不同Token
- ✅ 必需：GitHub已停止支持密码认证

### 步骤1：创建GitHub Personal Access Token

#### 1.1 登录GitHub
```
访问：https://github.com
使用您的GitHub账户登录
```

#### 1.2 进入Token设置页面
```
方法1：直接访问
https://github.com/settings/tokens

方法2：通过菜单导航
右上角头像 → Settings → Developer settings → Personal access tokens → Tokens (classic)
```

#### 1.3 生成新Token
```
1. 点击 "Generate new token" 按钮
2. 选择 "Generate new token (classic)"
3. 填写Token信息：
   - Note: TKTool Deployment（或其他描述）
   - Expiration: 建议选择 90 days 或 No expiration
   - Select scopes: 勾选以下权限
```

#### 1.4 选择Token权限
```
必需权限：
✅ repo
  ✅ repo:status
  ✅ repo_deployment
  ✅ public_repo
  ✅ repo:invite
  ✅ security_events

可选权限（根据需要）：
□ workflow（如果使用GitHub Actions）
□ write:packages（如果使用GitHub Packages）
□ read:org（如果是组织仓库）
```

#### 1.5 生成并保存Token
```
1. 点击 "Generate token" 按钮
2. 立即复制Token（格式：ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx）
3. 保存到安全位置（密码管理器或安全文档）

⚠️ 重要提醒：
- Token只显示一次，页面刷新后无法再次查看
- 如果丢失Token，需要重新生成
- 不要在代码中硬编码Token
```

### 步骤2：配置Git使用Token

#### 2.1 方法A：通过部署脚本配置（推荐）
```cmd
1. 运行部署脚本：
   windows_deploy_current_folder.bat

2. 选择认证方式：
   选择 "1. 使用GitHub Personal Access Token（推荐）"

3. 输入信息：
   GitHub用户名：your_username
   Personal Access Token：ghp_your_token_here

4. 脚本会自动配置Git认证
```

#### 2.2 方法B：手动命令行配置
```cmd
# 设置用户信息
git config --global user.name "your_username"
git config --global user.email "your_email@example.com"

# 设置凭据存储
git config --global credential.helper store

# 克隆仓库（首次会提示输入凭据）
git clone https://github.com/huangxianwu/tktool_byclaude.git

# 输入用户名：your_username
# 输入密码：ghp_your_token_here（不是GitHub密码）
```

#### 2.3 方法C：URL中包含Token
```cmd
# 直接在URL中使用Token
git clone https://ghp_your_token_here@github.com/huangxianwu/tktool_byclaude.git

# 或设置现有仓库的远程URL
git remote set-url origin https://ghp_your_token_here@github.com/huangxianwu/tktool_byclaude.git
```

#### 2.4 方法D：Windows凭据管理器
```cmd
1. 打开Windows凭据管理器：
   控制面板 → 凭据管理器 → Windows凭据

2. 点击 "添加普通凭据"

3. 填写信息：
   网络地址：git:https://github.com
   用户名：your_username
   密码：ghp_your_token_here

4. 点击 "确定" 保存
```

## 方法二：传统用户名密码认证

### 注意事项
```
⚠️ GitHub已于2021年8月停止支持密码认证
⚠️ 必须使用Personal Access Token替代密码
⚠️ 以下步骤中的"密码"实际指Token
```

### 步骤1：配置Git用户信息

#### 1.1 通过部署脚本配置
```cmd
1. 运行部署脚本：
   windows_deploy_current_folder.bat

2. 选择认证方式：
   选择 "2. 配置用户名和邮箱（首次使用）"

3. 输入信息：
   Git用户名：your_username
   Git邮箱：your_email@example.com

4. 脚本会自动配置Git用户信息
```

#### 1.2 手动命令行配置
```cmd
# 设置全局用户名
git config --global user.name "your_username"

# 设置全局邮箱
git config --global user.email "your_email@example.com"

# 设置凭据管理器
git config --global credential.helper manager-core

# 查看配置
git config --global --list
```

### 步骤2：首次认证
```cmd
# 克隆仓库时会提示输入凭据
git clone https://github.com/huangxianwu/tktool_byclaude.git

# 输入GitHub用户名
# 输入Personal Access Token（不是GitHub密码）
```

## 验证配置

### 检查Git配置
```cmd
# 查看用户配置
git config --global user.name
git config --global user.email

# 查看所有全局配置
git config --global --list

# 查看凭据助手配置
git config --global credential.helper
```

### 测试Git操作
```cmd
# 测试克隆
git clone https://github.com/huangxianwu/tktool_byclaude.git test_clone

# 测试拉取
cd test_clone
git pull origin main

# 清理测试
cd ..
rmdir /s test_clone
```

## 常见问题解决

### 问题1：认证失败
```
错误信息：Authentication failed
解决方案：
1. 检查用户名是否正确
2. 确认使用Token而不是密码
3. 验证Token权限是否足够
4. 检查Token是否已过期
```

### 问题2：Token权限不足
```
错误信息：Permission denied
解决方案：
1. 重新生成Token并选择正确权限
2. 确保勾选了 "repo" 权限
3. 如果是私有仓库，确保有访问权限
```

### 问题3：凭据存储问题
```
错误信息：每次都要求输入密码
解决方案：
1. 配置凭据助手：
   git config --global credential.helper store
   
2. 或使用Windows凭据管理器：
   git config --global credential.helper manager-core
```

### 问题4：URL格式错误
```
错误信息：Repository not found
解决方案：
1. 检查仓库URL是否正确
2. 确认仓库是否存在且有访问权限
3. 验证URL格式：
   https://github.com/username/repository.git
```

## 安全最佳实践

### Token安全
```
✅ 定期轮换Token（建议每90天）
✅ 使用最小权限原则
✅ 不要在代码中硬编码Token
✅ 使用环境变量或配置文件存储Token
✅ 定期检查Token使用情况
```

### 凭据管理
```
✅ 使用系统凭据管理器
✅ 不要在脚本中明文存储密码
✅ 定期清理无用的凭据
✅ 使用不同Token用于不同项目
```

### 网络安全
```
✅ 仅在安全网络环境中配置认证
✅ 避免在公共计算机上保存凭据
✅ 使用HTTPS而不是HTTP
✅ 定期检查Git配置
```

## 故障排除命令

### 清理Git配置
```cmd
# 清除全局用户配置
git config --global --unset user.name
git config --global --unset user.email

# 清除凭据助手
git config --global --unset credential.helper

# 清除存储的凭据
git config --global --unset-all credential.helper
```

### 重置凭据存储
```cmd
# Windows凭据管理器
# 手动删除 github.com 相关凭据

# 或使用命令行
cmdkey /delete:git:https://github.com
```

### 调试Git操作
```cmd
# 启用详细输出
git config --global credential.helper "store --file=.git-credentials"

# 查看详细日志
git clone https://github.com/username/repo.git --verbose

# 测试凭据
git credential fill
protocol=https
host=github.com
```

## 总结

1. **推荐使用GitHub Personal Access Token**，更安全可靠
2. **通过部署脚本配置**，自动化程度高，减少错误
3. **定期更新Token**，保持安全性
4. **妥善保管凭据**，避免泄露风险

如需更多帮助，请参考：
- [GitHub官方文档](https://docs.github.com/en/authentication)
- [Git官方文档](https://git-scm.com/docs)
- 项目部署指南