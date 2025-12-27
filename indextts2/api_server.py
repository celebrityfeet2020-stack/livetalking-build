#!/usr/bin/env python3
"""
IndexTTS2 API Server
提供TTS语音合成服务，兼容LiveTalking调用
"""

import os
import sys
import io
import time
import logging
import tempfile
from pathlib import Path

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# 全局变量
model = None
MODEL_DIR = os.environ.get('MODEL_DIR', '/app/models')
VOICES_DIR = os.environ.get('VOICES_DIR', '/app/voices')
DEVICE = os.environ.get('DEVICE', 'cuda')

def load_model():
    """加载IndexTTS2模型"""
    global model
    if model is None:
        logger.info("Loading IndexTTS2 model...")
        try:
            # 添加IndexTTS2路径
            sys.path.insert(0, '/app/IndexTTS2')
            from indextts import IndexTTS
            model = IndexTTS(model_dir=MODEL_DIR, device=DEVICE)
            logger.info("IndexTTS2 model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    return model

@app.route('/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({
        'status': 'healthy',
        'model_loaded': model is not None,
        'timestamp': time.time()
    })

@app.route('/tts', methods=['POST'])
def tts():
    """
    TTS合成接口
    支持form-data和json两种格式
    """
    try:
        # 获取参数
        if request.content_type and 'multipart/form-data' in request.content_type:
            text = request.form.get('text', '')
            voice_id = request.form.get('voice_id', 'default')
            voice_file = request.files.get('voice')
        else:
            data = request.get_json() or {}
            text = data.get('text', '')
            voice_id = data.get('voice_id', 'default')
            voice_file = None
        
        if not text:
            return jsonify({'error': 'text is required'}), 400
        
        logger.info(f"TTS request: text='{text[:50]}...', voice_id={voice_id}")
        
        # 加载模型
        tts_model = load_model()
        
        # 获取参考音频
        ref_audio_path = None
        if voice_file:
            # 使用上传的音频文件
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                voice_file.save(f.name)
                ref_audio_path = f.name
        elif voice_id and voice_id != 'default':
            # 使用预设音色
            voice_path = os.path.join(VOICES_DIR, f"{voice_id}.wav")
            if os.path.exists(voice_path):
                ref_audio_path = voice_path
        
        # 生成音频
        start_time = time.time()
        
        if ref_audio_path:
            audio_data = tts_model.tts(text, ref_audio_path)
        else:
            # 使用默认音色
            default_voice = os.path.join(VOICES_DIR, 'default.wav')
            if os.path.exists(default_voice):
                audio_data = tts_model.tts(text, default_voice)
            else:
                audio_data = tts_model.tts(text)
        
        elapsed = time.time() - start_time
        logger.info(f"TTS completed in {elapsed:.2f}s")
        
        # 返回音频
        audio_io = io.BytesIO()
        import soundfile as sf
        sf.write(audio_io, audio_data, 24000, format='WAV')
        audio_io.seek(0)
        
        return send_file(
            audio_io,
            mimetype='audio/wav',
            as_attachment=True,
            download_name='output.wav'
        )
        
    except Exception as e:
        logger.error(f"TTS error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/voices', methods=['GET'])
def list_voices():
    """列出可用音色"""
    voices = []
    if os.path.exists(VOICES_DIR):
        for f in os.listdir(VOICES_DIR):
            if f.endswith('.wav'):
                voices.append({
                    'id': f.replace('.wav', ''),
                    'name': f.replace('.wav', ''),
                    'path': os.path.join(VOICES_DIR, f)
                })
    return jsonify({'voices': voices})

@app.route('/voices', methods=['POST'])
def upload_voice():
    """上传新音色"""
    try:
        voice_id = request.form.get('voice_id')
        voice_file = request.files.get('file')
        
        if not voice_id or not voice_file:
            return jsonify({'error': 'voice_id and file are required'}), 400
        
        # 保存音色文件
        os.makedirs(VOICES_DIR, exist_ok=True)
        voice_path = os.path.join(VOICES_DIR, f"{voice_id}.wav")
        voice_file.save(voice_path)
        
        logger.info(f"Voice uploaded: {voice_id}")
        return jsonify({'success': True, 'voice_id': voice_id})
        
    except Exception as e:
        logger.error(f"Upload voice error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # 预加载模型
    try:
        load_model()
    except Exception as e:
        logger.warning(f"Model preload failed: {e}")
    
    # 启动服务
    port = int(os.environ.get('PORT', 17860))
    logger.info(f"Starting IndexTTS2 API server on port {port}")
    app.run(host='0.0.0.0', port=port, threaded=True)
