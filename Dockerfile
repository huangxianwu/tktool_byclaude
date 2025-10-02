# 使用 Ubuntu 基础镜像并手动安装 Python（绕过 Docker Hub Python 镜像拉取问题）
FROM ubuntu:22.04

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# 安装 Python 和必要工具
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-venv \
    python3-pip \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s /usr/bin/python3.10 /usr/bin/python

# 升级 pip 并配置国内镜像源
RUN python -m pip install --upgrade pip \
    && pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

EXPOSE 5000

CMD ["python", "run.py"]