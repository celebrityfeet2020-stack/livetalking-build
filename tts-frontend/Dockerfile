# TTS前端 Docker镜像
# 多通道语音合成与数字人控制系统

FROM python:3.11-slim

LABEL maintainer="Digital Human Project"
LABEL description="TTS Frontend - Multi-channel Voice Synthesis Control System"
LABEL version="1.1"

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt /app/

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY server.py /app/
COPY templates/ /app/templates/

# 创建static目录（即使为空也需要创建）
RUN mkdir -p /app/static /app/voices /app/logs

# 如果有static文件则复制
COPY static/ /app/static/ 2>/dev/null || true

# 暴露端口
EXPOSE 17202

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:17202/health || exit 1

# 启动命令
CMD ["python", "server.py"]
