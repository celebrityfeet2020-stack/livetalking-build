# LiveTalking + MuseTalk Docker镜像
# 基于官方镜像，解决WebRTC连接问题
# 使用官方镜像可以避免依赖冲突

FROM registry.cn-beijing.aliyuncs.com/codewithgpu2/lipku-metahuman-stream:vjo1Y6NJ3N

LABEL maintainer="Digital Human Project"
LABEL description="LiveTalking with MuseTalk - Digital Human Rendering Service (Based on Official Image)"
LABEL version="2.2"

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# 更新代码到最新版本
WORKDIR /root/metahuman-stream
RUN git pull || true

# 如果需要，降级huggingface_hub以解决cached_download问题
# 官方镜像可能已经有正确的版本，先检测再决定是否降级
RUN pip show huggingface_hub | grep Version || true

# 创建必要目录
RUN mkdir -p /root/metahuman-stream/data/avatars/avator_1/full_imgs \
    /root/metahuman-stream/data/avatars/avator_1/coords \
    /root/metahuman-stream/models/musetalk \
    /root/metahuman-stream/web \
    /tmp/audio

# 复制自定义配置和修复文件
COPY app_fixed.py /root/metahuman-stream/app.py
COPY webrtcapi.html /root/metahuman-stream/web/webrtcapi.html
COPY player.html /root/metahuman-stream/web/player.html

# 创建client.js文件（webrtcapi.html需要）
RUN echo "// Client.js placeholder" > /root/metahuman-stream/web/client.js

# 设置权限
RUN chmod +x /root/metahuman-stream/app.py

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

# 工作目录
WORKDIR /root/metahuman-stream

# 启动命令
CMD ["python", "app.py", "--transport", "webrtc", "--model", "musetalk", "--listenport", "8010", "--avatar_id", "avator_1"]
