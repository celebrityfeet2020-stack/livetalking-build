# IndexTTS2 Docker镜像
# 基于PyTorch + CUDA 12.1

FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

LABEL maintainer="Digital Human Project"
LABEL description="IndexTTS2 - High-quality Text-to-Speech Service"
LABEL version="1.0"

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
    && rm -rf /var/lib/apt/lists/*

# 克隆IndexTTS2仓库
RUN git clone https://github.com/index-tts/index-tts.git /app/IndexTTS2

# 安装Python依赖
WORKDIR /app/IndexTTS2
RUN pip install --no-cache-dir -r requirements.txt

# 安装额外依赖
RUN pip install --no-cache-dir \
    flask \
    flask-cors \
    gunicorn \
    soundfile \
    librosa \
    pydub

# 创建模型目录
RUN mkdir -p /app/models/huggingface /app/models/torch /app/voices

# 下载IndexTTS2模型（这一步会在构建时下载模型）
# 注意：模型较大，构建时间会较长
RUN python -c "from indextts import IndexTTS; model = IndexTTS(model_dir='/app/models', device='cpu'); print('Model downloaded successfully')" || echo "Model will be downloaded on first run"

# 创建API服务脚本
COPY api_server.py /app/api_server.py

# 暴露端口
EXPOSE 17860

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:17860/health || exit 1

# 启动命令
CMD ["python", "/app/api_server.py"]
