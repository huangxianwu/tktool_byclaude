GHCR 端到端部署指南（Mac 构建 → GHCR 推送 → Windows 拉取运行）

适用范围
- 面向在同一局域网内使用的 2 人团队。
- 目标是快速、稳定地部署，不做过度设计或复杂编排。

总体流程
- Mac 构建容器镜像并推送到 GitHub Container Registry (GHCR)
- Windows 登录 GHCR、拉取镜像并运行服务

前置准备
- Mac 端：
  - 已安装 `Docker Desktop`
  - GitHub 账号与可用的 Personal Access Token (PAT)
  - PAT 需要至少 `write:packages` 权限（推送镜像）
  - 能访问外网（用于拉取基础镜像与推送 GHCR）
- Windows 端：
  - 已安装 `Docker Desktop`（建议启用 WSL2 后端）
  - GitHub 账号与 PAT（`read:packages` 权限即可）
  - Windows 防火墙允许入站访问部署端口（默认 5000）

镜像命名约定
- 统一使用：`ghcr.io/<github_user_or_org>/tktool:<tag>`
- 版本策略：
  - 稳定版：`vYYYYMMDD`（如：`v20251001`）
  - 开发版：`dev` / `latest`（只用于临时验证，不用于正式共享）

推荐 Dockerfile（示例，不必须修改现有代码）
```dockerfile
# 文件：Dockerfile（示例）
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai

WORKDIR /app

# 如有国内网络环境，可切换 pip 源（示例，按需开启）
# RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

# 可选：暴露端口（默认应用监听 5000）
EXPOSE 5000

# 最简启动命令（依据项目入口调整）
CMD ["python", "run.py"]
```

Mac 端：构建与推送 GHCR
1) 登录 GHCR
- 创建 GitHub PAT（Settings → Developer settings → Personal access tokens），Scopes 至少包含：`write:packages`。
- 登录：
  - zsh/bash：
    - `export CR_PAT="<你的PAT>"`
    - `echo "$CR_PAT" | docker login ghcr.io -u <你的GitHub用户名> --password-stdin`

2) 构建镜像
- 在项目根目录执行：
  - `docker build -t ghcr.io/<你的GitHub用户名>/tktool:v20251001 -f Dockerfile .`
  - （可选）标记 `latest`：`docker tag ghcr.io/<你>/tktool:v20251001 ghcr.io/<你>/tktool:latest`

3) 推送镜像
- `docker push ghcr.io/<你>/tktool:v20251001`
- （可选）`docker push ghcr.io/<你>/tktool:latest`

Windows 端：拉取与运行
1) 登录 GHCR
- 打开 PowerShell 或 CMD：
  - `docker login ghcr.io`
  - 按提示输入 GitHub 用户名与 PAT（权限至少 `read:packages`）

2) 拉取镜像
- `docker pull ghcr.io/<你>/tktool:v20251001`

3) 运行容器（最简）
- 单机运行并映射端口：
  - `docker run -d --name tktool -p 5000:5000 --restart unless-stopped ghcr.io/<你>/tktool:v20251001`
- 在同一局域网的另一台机器上访问：`http://<Windows机器IP>:5000`

4) 数据持久化（按需）
- 为避免容器重建后数据丢失，建议挂载主机目录：
  - 新建数据目录：`C:\tktool_data`（Windows）
  - 绑定挂载（示例）：
    - `docker run -d --name tktool -p 5000:5000 -v C:\tktool_data\data:/app/data --restart unless-stopped ghcr.io/<你>/tktool:v20251001`
- 说明：
  - `/app/data` 用作应用的持久化目录（日志、导出文件等）。
  - 如需持久化数据库或特定文件，请将其路径改为 `/app/data/...` 并在应用中读取该目录（保持简单即可）。

更新与回滚
- 发布新版本（Mac）：
  - 构建并推送新 tag：`v20251002`
- 更新运行（Windows）：
  - 拉取新版本：`docker pull ghcr.io/<你>/tktool:v20251002`
  - 停止旧容器：`docker stop tktool && docker rm tktool`
  - 启动新容器（同样的 `docker run` 命令，改用新 tag）
- 回滚：
  - 直接使用旧 tag（例如 `v20251001`）重新 `docker run` 即可。

常见问题与解决
- 无法登录 GHCR：
  - 检查 PAT 权限是否包含 `write:packages`（Mac 推送）或 `read:packages`（Windows 拉取）。
  - 组织仓库需在组织设置中允许 GHCR 包访问（Package settings）。
- 端口无法访问：
  - 检查 Windows 防火墙是否允许入站访问 `5000`。
  - 端口冲突时更换映射：例如 `-p 8080:5000`，然后访问 `http://<IP>:8080`。
- 镜像体积过大/构建慢：
  - 使用 `python:3.10-slim` 等精简基础镜像。
  - 开启国内镜像源（参考 Dockerfile 示例中的 pip 源配置）。
- 时区不正确：
  - 在 Dockerfile 中设置 `TZ` 环境变量；或在 `docker run` 中指定 `-e TZ=Asia/Shanghai`。

安全与权限建议（简化版）
- PAT 最小权限原则：Mac 端 `write:packages`，Windows 端 `read:packages`。
- GHCR 包可设置为私有，仅授权成员可拉取。
- 避免将敏感配置写入镜像，使用 `--env` 或 `--env-file` 在运行时注入。

极简运维清单
- 每次发布：
  - Mac：`docker build` → `docker push`
  - Windows：`docker pull` → `docker run`
- 出问题时：
  - 看容器日志：`docker logs -f tktool`
  - 端口策略与防火墙：开放并确认端口
  - 快速回滚到旧 tag

附录：示例运行命令集合
- Mac 构建与推送：
  - `export CR_PAT="<PAT>"`
  - `echo "$CR_PAT" | docker login ghcr.io -u <user> --password-stdin`
  - `docker build -t ghcr.io/<user>/tktool:v20251001 -f Dockerfile .`
  - `docker push ghcr.io/<user>/tktool:v20251001`
- Windows 拉取与运行：
  - `docker login ghcr.io`
  - `docker pull ghcr.io/<user>/tktool:v20251001`
  - `docker run -d --name tktool -p 5000:5000 --restart unless-stopped ghcr.io/<user>/tktool:v20251001`

说明
- 本方案刻意保持最小化与直观，适合在局域网内 2 人使用。
- 若后续需要拓展（如反向代理、HTTPS、集中日志），可在此基础上逐步迭代，不建议一次性复杂化。