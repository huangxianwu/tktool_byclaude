#!/usr/bin/env bash
set -euo pipefail

# 配置
USER="huangxianwu"
IMAGE="ghcr.io/${USER}/tktool"
TAG="$(date +%Y%m%d%H%M%S)"

echo "[1/3] 构建镜像: ${IMAGE}:${TAG}"
docker build -t "${IMAGE}:${TAG}" -f Dockerfile .
echo "构建完成，TAG=${TAG}"

echo "[2/3] 登录 GHCR（如未登录）"
echo "提示：请在本终端执行：export CR_PAT='<你的PAT>'"
echo "随后执行：echo \"$CR_PAT\" | docker login ghcr.io -u ${USER} --password-stdin"

echo "[3/3] 推送镜像（手动执行以下命令）"
echo "docker push ${IMAGE}:${TAG}"

echo "完成。Windows 端可使用该 TAG 进行拉取与运行。"