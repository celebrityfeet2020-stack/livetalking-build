#!/usr/bin/env python3
"""
TTS前端服务 - IndexTTS2 控制台
多通道语音合成与数字人控制系统
"""

import os
import sys
import json
import time
import logging
import threading
import queue
from pathlib import Path
from typing import Dict, Optional, Any

from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
import requests

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# ==================== 配置 ====================
# IndexTTS2服务地址
INDEXTTS2_API_URL = os.environ.get('INDEXTTS2_API_URL', 'http://localhost:17860')
# LiveTalking服务地址
LIVETALKING_API_URL = os.environ.get('LIVETALKING_API_URL', 'http://localhost:17310/human')
# 音色文件目录
VOICES_DIR = os.environ.get('VOICES_DIR', '/app/voices')
# 数字人通道ID
DIGITAL_HUMAN_CHANNEL_ID = 100

# ==================== 全局状态 ====================
# 数字人连接状态
digital_human_connected = False
digital_human_sessionid = 0

# 音色模板
voice_templates: Dict[str, dict] = {}

# 消息队列（用于数字人通道）
message_queues: Dict[int, queue.Queue] = {}

# ==================== 辅助函数 ====================
def load_voice_templates():
    """加载音色模板"""
    global voice_templates
    voice_templates = {}
    
    if not os.path.exists(VOICES_DIR):
        os.makedirs(VOICES_DIR, exist_ok=True)
        return
    
    for f in os.listdir(VOICES_DIR):
        if f.endswith('.wav'):
            voice_id = f.replace('.wav', '')
            voice_templates[voice_id] = {
                'id': voice_id,
                'name': voice_id,
                'path': os.path.join(VOICES_DIR, f),
                'description': ''
            }
    
    logger.info(f"Loaded {len(voice_templates)} voice templates")

def check_indextts2_health() -> bool:
    """检查IndexTTS2服务健康状态"""
    try:
        resp = requests.get(f"{INDEXTTS2_API_URL}/health", timeout=5)
        return resp.status_code == 200
    except:
        return False

def send_to_livetalking(text: str, sessionid: int = 0) -> bool:
    """发送文本到LiveTalking"""
    try:
        resp = requests.post(
            LIVETALKING_API_URL,
            json={
                'type': 'echo',
                'text': text,
                'sessionid': sessionid
            },
            timeout=10
        )
        return resp.status_code == 200
    except Exception as e:
        logger.error(f"Send to LiveTalking failed: {e}")
        return False

def tts_and_send(text: str, voice_id: str = 'default'):
    """TTS合成并发送到数字人"""
    global digital_human_sessionid
    
    try:
        # 调用IndexTTS2合成语音
        voice_path = None
        if voice_id and voice_id != 'default' and voice_id in voice_templates:
            voice_path = voice_templates[voice_id]['path']
        
        # 直接发送文本到LiveTalking（LiveTalking会调用TTS）
        # 或者先合成再发送音频
        if send_to_livetalking(text, digital_human_sessionid):
            logger.info(f"Sent to LiveTalking: {text[:50]}...")
            return True
        else:
            logger.error("Failed to send to LiveTalking")
            return False
            
    except Exception as e:
        logger.error(f"TTS and send failed: {e}")
        return False

# ==================== API路由 ====================
@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({
        'status': 'healthy',
        'model_loaded': check_indextts2_health(),
        'digital_human_connected': digital_human_connected,
        'templates_count': len(voice_templates),
        'timestamp': time.time()
    })

@app.route('/digital-human/status', methods=['GET', 'POST'])
def digital_human_status():
    """数字人连接状态"""
    global digital_human_connected, digital_human_sessionid
    
    if request.method == 'POST':
        data = request.get_json() or {}
        digital_human_connected = data.get('connected', False)
        digital_human_sessionid = data.get('sessionid', 0)
        logger.info(f"Digital human status updated: connected={digital_human_connected}, sessionid={digital_human_sessionid}")
        return jsonify({'success': True})
    
    return jsonify({
        'connected': digital_human_connected,
        'sessionid': digital_human_sessionid
    })

@app.route('/tts', methods=['POST'])
def tts():
    """TTS合成接口"""
    try:
        # 支持form-data和json
        if request.content_type and 'multipart/form-data' in request.content_type:
            text = request.form.get('text', '')
            voice_id = request.form.get('voice_id', 'default')
            channel_id = int(request.form.get('channel_id', DIGITAL_HUMAN_CHANNEL_ID))
        else:
            data = request.get_json() or {}
            text = data.get('text', '')
            voice_id = data.get('voice_id', 'default')
            channel_id = data.get('channel_id', DIGITAL_HUMAN_CHANNEL_ID)
        
        if not text:
            return jsonify({'error': 'text is required'}), 400
        
        logger.info(f"TTS request: text='{text[:50]}...', voice_id={voice_id}, channel_id={channel_id}")
        
        # 发送到数字人
        if channel_id == DIGITAL_HUMAN_CHANNEL_ID:
            success = tts_and_send(text, voice_id)
            if success:
                return jsonify({'success': True, 'message': 'Sent to digital human'})
            else:
                return jsonify({'error': 'Failed to send to digital human'}), 500
        else:
            # 其他通道：直接调用IndexTTS2
            return jsonify({'error': 'Channel not supported'}), 400
            
    except Exception as e:
        logger.error(f"TTS error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/voices', methods=['GET'])
def list_voices():
    """列出音色"""
    return jsonify({
        'voices': list(voice_templates.values())
    })

@app.route('/voices', methods=['POST'])
def upload_voice():
    """上传音色"""
    try:
        voice_id = request.form.get('voice_id')
        description = request.form.get('description', '')
        voice_file = request.files.get('file')
        
        if not voice_id:
            return jsonify({'error': 'voice_id is required'}), 400
        if not voice_file:
            return jsonify({'error': 'file is required'}), 400
        
        # 保存音色文件
        os.makedirs(VOICES_DIR, exist_ok=True)
        voice_path = os.path.join(VOICES_DIR, f"{voice_id}.wav")
        voice_file.save(voice_path)
        
        # 更新模板
        voice_templates[voice_id] = {
            'id': voice_id,
            'name': voice_id,
            'path': voice_path,
            'description': description
        }
        
        logger.info(f"Voice uploaded: {voice_id}")
        return jsonify({'success': True, 'voice_id': voice_id})
        
    except Exception as e:
        logger.error(f"Upload voice error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/voices/<voice_id>', methods=['DELETE'])
def delete_voice(voice_id):
    """删除音色"""
    try:
        if voice_id not in voice_templates:
            return jsonify({'error': 'Voice not found'}), 404
        
        voice_path = voice_templates[voice_id]['path']
        if os.path.exists(voice_path):
            os.remove(voice_path)
        
        del voice_templates[voice_id]
        
        logger.info(f"Voice deleted: {voice_id}")
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Delete voice error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/channels', methods=['GET'])
def list_channels():
    """列出通道"""
    return jsonify({
        'channels': [
            {
                'id': DIGITAL_HUMAN_CHANNEL_ID,
                'name': '数字人通道',
                'type': 'digital_human',
                'connected': digital_human_connected
            }
        ]
    })

# ==================== 静态文件 ====================
@app.route('/api-docs')
def api_docs():
    """API文档"""
    return render_template('api_docs.html')

@app.route('/swagger')
def swagger():
    """Swagger UI"""
    return render_template('swagger.html')

# ==================== 启动 ====================
if __name__ == '__main__':
    # 加载音色模板
    load_voice_templates()
    
    # 启动服务
    port = int(os.environ.get('PORT', 17202))
    logger.info(f"Starting TTS Frontend on port {port}")
    logger.info(f"IndexTTS2 API: {INDEXTTS2_API_URL}")
    logger.info(f"LiveTalking API: {LIVETALKING_API_URL}")
    
    app.run(host='0.0.0.0', port=port, threaded=True, debug=False)
