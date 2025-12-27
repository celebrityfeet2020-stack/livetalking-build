# IndexTTS2 Docker镜像
# 基于PyTorch + CUDA 12.1

FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

LABEL maintainer="Digital Human Project"
LABEL description="IndexTTS2 - High-quality Text-to-Speech Service"
LABEL version="1.1"

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV HF_HOME=/app/models/huggingface
ENV TORCH_HOME=/app/models/torch

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    wget \
    curl \
    ffmpeg \
    libsndfile1 \
    libsox-dev \
    sox \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 升级pip
RUN pip install --upgrade pip setuptools wheel

# 克隆IndexTTS仓库（使用正确的仓库地址）
RUN git clone --depth 1 https://github.com/indexTeam/IndexTTS.git /app/IndexTTS2 || \
    git clone --depth 1 https://github.com/index-tts/IndexTTS.git /app/IndexTTS2 || \
    echo "Repository clone failed, will create minimal setup"

# 安装基础Python依赖
WORKDIR /app/IndexTTS2
RUN pip install --no-cache-dir \
    torch \
    torchaudio \
    numpy \
    scipy \
    soundfile \
    librosa \
    pydub \
    transformers \
    huggingface_hub \
    flask \
    flask-cors \
    gunicorn

# 尝试安装requirements.txt（如果存在）
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt || true; fi

# 创建模型目录
RUN mkdir -p /app/models/huggingface /app/models/torch /app/voices

# 复制API服务脚本
COPY api_server.py /app/api_server.py

# 暴露端口
EXPOSE 17860

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:17860/health || exit 1

# 启动命令
CMD ["python", "/app/api_server.py"]
