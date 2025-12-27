# LiveTalking + MuseTalk Docker镜像
# 数字人渲染服务 - 完整版
# 解决WebRTC连接问题

FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

LABEL maintainer="Digital Human Project"
LABEL description="LiveTalking with MuseTalk - Digital Human Rendering Service (Full Version)"
LABEL version="2.1"

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV CUDA_HOME=/usr/local/cuda
ENV PATH=${CUDA_HOME}/bin:${PATH}
ENV LD_LIBRARY_PATH=${CUDA_HOME}/lib64:${LD_LIBRARY_PATH}

# 设置工作目录
WORKDIR /app

# 安装系统依赖（包括WebRTC所需的音视频编解码库）
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    wget \
    curl \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libsndfile1 \
    libavcodec-dev \
    libavformat-dev \
    libavutil-dev \
    libswscale-dev \
    libswresample-dev \
    libopus-dev \
    libvpx-dev \
    libx264-dev \
    pkg-config \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# 升级pip
RUN pip install --upgrade pip setuptools wheel

# 克隆LiveTalking仓库
RUN git clone --depth 1 https://github.com/lipku/LiveTalking.git /app/LiveTalking

WORKDIR /app/LiveTalking

# 安装基础Python依赖
RUN pip install --no-cache-dir \
    numpy==1.24.3 \
    opencv-python==4.8.1.78 \
    opencv-python-headless==4.8.1.78 \
    pillow==10.1.0 \
    scipy==1.11.4 \
    tqdm==4.66.1 \
    pyyaml==6.0.1

# 安装PyTorch相关依赖
RUN pip install --no-cache-dir \
    torchvision==0.16.0 \
    torchaudio==2.1.0

# 安装Web框架和异步库
RUN pip install --no-cache-dir \
    flask==3.0.0 \
    flask-cors==4.0.0 \
    aiohttp==3.9.1 \
    aiofiles==23.2.1

# 安装aiortc（使用最新稳定版本1.9.0，避免1.6.0的安装问题）
# 1.9.0是经过测试的稳定版本
RUN pip install --no-cache-dir aiortc==1.9.0

# 安装音视频处理库
RUN pip install --no-cache-dir \
    av \
    soundfile \
    librosa \
    pydub

# 安装MuseTalk依赖
# 注意：huggingface_hub必须使用兼容版本，避免cached_download报错
RUN pip install --no-cache-dir \
    huggingface_hub==0.16.4 \
    diffusers==0.21.0 \
    transformers==4.36.2 \
    accelerate==0.25.0 \
    omegaconf==2.3.0 \
    safetensors==0.4.1

# 安装face detection和处理库
RUN pip install --no-cache-dir \
    face-alignment==1.4.1 \
    mediapipe==0.10.9

# 安装其他依赖
RUN pip install --no-cache-dir \
    requests==2.31.0 \
    websockets==12.0 \
    python-multipart==0.0.6 \
    uvicorn==0.25.0 \
    httpx==0.26.0

# 尝试安装requirements.txt中的其他依赖（忽略错误）
RUN pip install --no-cache-dir -r requirements.txt 2>/dev/null || true

# 创建必要目录
RUN mkdir -p /app/LiveTalking/data/avatars/avator_1/full_imgs \
    /app/LiveTalking/data/avatars/avator_1/coords \
    /app/LiveTalking/models/musetalk \
    /app/LiveTalking/web \
    /tmp/audio

# 跳过构建时的模型下载，模型将在运行时下载
# 这样可以避免HuggingFace访问限制导致的构建失败
RUN echo "MuseTalk model will be downloaded on first run"

# 复制自定义配置和修复文件
COPY app_fixed.py /app/LiveTalking/app.py
COPY webrtcapi.html /app/LiveTalking/web/webrtcapi.html
COPY player.html /app/LiveTalking/web/player.html

# 创建client.js文件（webrtcapi.html需要）
RUN echo "// Client.js placeholder" > /app/LiveTalking/web/client.js

# 设置权限
RUN chmod +x /app/LiveTalking/app.py

# 暴露端口
EXPOSE 8010

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=3 \
    CMD curl -f http://localhost:8010/ || exit 1

# 设置默认环境变量
ENV TTS_SERVER=http://localhost:17860/
ENV AVATAR_ID=avator_1
ENV MODEL=musetalk
ENV TRANSPORT=webrtc
ENV LISTEN_PORT=8010

# 启动命令
CMD ["python", "app.py", "--transport", "webrtc", "--model", "musetalk", "--listenport", "8010", "--avatar_id", "avator_1"]
