#!/usr/bin/env python3
"""
LiveTalking App - 修复版 v2.0
修复了WebRTC连接问题，兼容aiortc 1.6.0
增加了详细的日志输出用于调试
"""

import os
import sys
import json
import random
import asyncio
import argparse
import logging
import traceback
from typing import Dict, Optional
from aiohttp import web

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('LiveTalking')

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 全局变量
nerfreals: Dict[int, 'BaseReal'] = {}  # sessionid:BaseReal
opt = None
model = None
avatar = None
pcs = set()

def randN(N) -> int:
    """生成长度为N的随机数"""
    min_val = pow(10, N - 1)
    max_val = pow(10, N)
    return random.randint(min_val, max_val - 1)

def build_nerfreal(sessionid: int):
    """构建数字人渲染器"""
    global opt, model, avatar
    
    logger.info(f"Building nerfreal for session {sessionid}, model={opt.model}")
    
    opt.sessionid = sessionid
    
    try:
        if opt.model == 'wav2lip':
            from lipreal import LipReal
            nerfreal = LipReal(opt, model, avatar)
        elif opt.model == 'musetalk':
            from musereal import MuseReal
            nerfreal = MuseReal(opt, model, avatar)
        elif opt.model == 'ultralight':
            from lightreal import LightReal
            nerfreal = LightReal(opt, model, avatar)
        else:
            raise ValueError(f"Unknown model: {opt.model}")
        
        logger.info(f"Nerfreal built successfully for session {sessionid}")
        return nerfreal
    except Exception as e:
        logger.error(f"Failed to build nerfreal: {e}")
        logger.error(traceback.format_exc())
        raise

async def offer(request):
    """处理WebRTC offer请求"""
    global nerfreals, pcs
    
    try:
        # 延迟导入aiortc，确保在需要时才加载
        from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceServer, RTCConfiguration
        from aiortc.rtcrtpsender import RTCRtpSender
        
        params = await request.json()
        logger.info(f"Received offer: type={params.get('type')}")
        logger.debug(f"SDP: {params.get('sdp', '')[:200]}...")
        
        offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
        
        # 检查会话数限制
        if hasattr(opt, 'max_session') and len(nerfreals) >= opt.max_session:
            logger.warning('Reached max session limit')
            return web.Response(
                content_type="application/json",
                text=json.dumps({"code": -1, "msg": "reach max session"}),
            )
        
        sessionid = randN(6)
        nerfreals[sessionid] = None
        logger.info(f'New session: sessionid={sessionid}, total sessions={len(nerfreals)}')
        
        # 构建数字人渲染器（在线程池中执行）
        loop = asyncio.get_event_loop()
        nerfreal = await loop.run_in_executor(None, build_nerfreal, sessionid)
        nerfreals[sessionid] = nerfreal
        
        # 配置ICE服务器
        ice_servers = [
            RTCIceServer(urls=['stun:stun.l.google.com:19302']),
            RTCIceServer(urls=['stun:stun.miwifi.com:3478']),
        ]
        config = RTCConfiguration(iceServers=ice_servers)
        pc = RTCPeerConnection(configuration=config)
        pcs.add(pc)
        
        logger.info(f"Created RTCPeerConnection for session {sessionid}")
        
        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            logger.info(f"Connection state changed to: {pc.connectionState}")
            if pc.connectionState == "failed":
                logger.error("Connection failed, closing...")
                await pc.close()
                pcs.discard(pc)
                if sessionid in nerfreals:
                    del nerfreals[sessionid]
            elif pc.connectionState == "closed":
                logger.info("Connection closed")
                pcs.discard(pc)
                if sessionid in nerfreals:
                    del nerfreals[sessionid]
            elif pc.connectionState == "connected":
                logger.info(f"Connection established for session {sessionid}")
        
        @pc.on("iceconnectionstatechange")
        async def on_iceconnectionstatechange():
            logger.info(f"ICE connection state: {pc.iceConnectionState}")
        
        @pc.on("icegatheringstatechange")
        async def on_icegatheringstatechange():
            logger.info(f"ICE gathering state: {pc.iceGatheringState}")
        
        # 创建播放器并添加音视频轨道
        try:
            from humanplayer import HumanPlayer
            player = HumanPlayer(nerfreals[sessionid])
            
            logger.info("Adding audio track...")
            pc.addTrack(player.audio)
            
            logger.info("Adding video track...")
            pc.addTrack(player.video)
            
            logger.info("Tracks added successfully")
        except Exception as e:
            logger.error(f"Failed to add tracks: {e}")
            logger.error(traceback.format_exc())
            raise
        
        # 设置视频编码偏好
        try:
            capabilities = RTCRtpSender.getCapabilities("video")
            if capabilities and capabilities.codecs:
                # 优先使用H264，然后是VP8
                preferences = []
                for codec in capabilities.codecs:
                    if codec.mimeType == "video/H264":
                        preferences.append(codec)
                for codec in capabilities.codecs:
                    if codec.mimeType == "video/VP8":
                        preferences.append(codec)
                for codec in capabilities.codecs:
                    if codec.mimeType == "video/rtx":
                        preferences.append(codec)
                
                if preferences:
                    transceivers = pc.getTransceivers()
                    for transceiver in transceivers:
                        if transceiver.kind == "video":
                            transceiver.setCodecPreferences(preferences)
                            logger.info(f"Set codec preferences: {[c.mimeType for c in preferences[:3]]}")
                            break
        except Exception as e:
            logger.warning(f"Failed to set codec preferences: {e}")
        
        # 完成SDP协商
        logger.info("Setting remote description...")
        await pc.setRemoteDescription(offer)
        
        logger.info("Creating answer...")
        answer = await pc.createAnswer()
        
        logger.info("Setting local description...")
        await pc.setLocalDescription(answer)
        
        logger.info(f"SDP negotiation complete for session {sessionid}")
        logger.debug(f"Answer SDP: {pc.localDescription.sdp[:200]}...")
        
        return web.Response(
            content_type="application/json",
            text=json.dumps({
                "sdp": pc.localDescription.sdp,
                "type": pc.localDescription.type,
                "sessionid": sessionid
            }),
        )
    except Exception as e:
        logger.exception('Offer exception:')
        return web.Response(
            content_type="application/json",
            text=json.dumps({"code": -1, "msg": str(e)}),
        )

async def human(request):
    """处理文本输入请求"""
    try:
        params = await request.json()
        sessionid = params.get('sessionid', 0)
        
        logger.info(f"Human request: sessionid={sessionid}, type={params.get('type')}, text={params.get('text', '')[:50]}...")
        
        if sessionid not in nerfreals or nerfreals[sessionid] is None:
            logger.warning(f"Session {sessionid} not found")
            return web.Response(
                content_type="application/json",
                text=json.dumps({"code": -1, "msg": "session not found"}),
            )
        
        if params.get('interrupt'):
            logger.info(f"Interrupting session {sessionid}")
            nerfreals[sessionid].flush_talk()
        
        if params.get('type') == 'echo':
            text = params.get('text', '')
            logger.info(f"Echo text to session {sessionid}: {text[:50]}...")
            nerfreals[sessionid].put_msg_txt(text)
        elif params.get('type') == 'chat':
            text = params.get('text', '')
            logger.info(f"Chat text to session {sessionid}: {text[:50]}...")
            asyncio.get_event_loop().run_in_executor(None, llm_response, text, nerfreals[sessionid])
        
        return web.Response(
            content_type="application/json",
            text=json.dumps({"code": 0, "msg": "ok"}),
        )
    except Exception as e:
        logger.exception('Human exception:')
        return web.Response(
            content_type="application/json",
            text=json.dumps({"code": -1, "msg": str(e)}),
        )

async def interrupt_talk(request):
    """中断当前语音"""
    try:
        params = await request.json()
        sessionid = params.get('sessionid', 0)
        
        logger.info(f"Interrupt request for session {sessionid}")
        
        if sessionid in nerfreals and nerfreals[sessionid] is not None:
            nerfreals[sessionid].flush_talk()
        
        return web.Response(
            content_type="application/json",
            text=json.dumps({"code": 0, "msg": "ok"}),
        )
    except Exception as e:
        logger.exception('Interrupt exception:')
        return web.Response(
            content_type="application/json",
            text=json.dumps({"code": -1, "msg": str(e)}),
        )

async def humanaudio(request):
    """处理音频输入"""
    try:
        form = await request.post()
        sessionid = int(form.get('sessionid', 0))
        fileobj = form.get("file")
        
        logger.info(f"Audio upload for session {sessionid}")
        
        if sessionid not in nerfreals or nerfreals[sessionid] is None:
            return web.Response(
                content_type="application/json",
                text=json.dumps({"code": -1, "msg": "session not found"}),
            )
        
        if fileobj:
            filename = fileobj.filename
            audio_path = f"/tmp/audio/audio_{sessionid}_{filename}"
            
            os.makedirs("/tmp/audio", exist_ok=True)
            with open(audio_path, 'wb') as f:
                f.write(fileobj.file.read())
            
            logger.info(f"Audio saved to {audio_path}")
            nerfreals[sessionid].put_audio_file(audio_path)
        
        return web.Response(
            content_type="application/json",
            text=json.dumps({"code": 0, "msg": "ok"}),
        )
    except Exception as e:
        logger.exception('Humanaudio exception:')
        return web.Response(
            content_type="application/json",
            text=json.dumps({"code": -1, "msg": str(e)}),
        )

async def set_audiotype(request):
    """设置音频类型"""
    try:
        params = await request.json()
        sessionid = params.get('sessionid', 0)
        audiotype = params.get('audiotype', 0)
        
        logger.info(f"Set audiotype for session {sessionid}: {audiotype}")
        
        if sessionid in nerfreals and nerfreals[sessionid] is not None:
            nerfreals[sessionid].set_curr_state(audiotype)
        
        return web.Response(
            content_type="application/json",
            text=json.dumps({"code": 0, "msg": "ok"}),
        )
    except Exception as e:
        logger.exception('Set_audiotype exception:')
        return web.Response(
            content_type="application/json",
            text=json.dumps({"code": -1, "msg": str(e)}),
        )

async def health(request):
    """健康检查"""
    return web.Response(
        content_type="application/json",
        text=json.dumps({
            "status": "healthy",
            "sessions": len(nerfreals),
            "model": opt.model if opt else "unknown"
        }),
    )

async def on_shutdown(app):
    """关闭时清理资源"""
    logger.info("Shutting down, closing all connections...")
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()
    logger.info("All connections closed")

def llm_response(message, nerfreal):
    """LLM响应（占位函数）"""
    logger.info(f"LLM response for: {message[:50]}...")
    nerfreal.put_msg_txt(f"收到: {message}")

def load_models():
    """加载模型"""
    global model, avatar, opt
    
    logger.info(f"Loading model: {opt.model}")
    
    try:
        if opt.model == 'musetalk':
            from musereal import load_model as load_muse_model, load_avatar
            model = load_muse_model()
            avatar = load_avatar(opt.avatar_id)
        elif opt.model == 'wav2lip':
            from lipreal import load_model as load_lip_model, load_avatar
            model = load_lip_model()
            avatar = load_avatar(opt.avatar_id)
        elif opt.model == 'ultralight':
            from lightreal import load_model as load_light_model, load_avatar
            model = load_light_model()
            avatar = load_avatar(opt.avatar_id)
        else:
            raise ValueError(f"Unknown model: {opt.model}")
        
        logger.info("Model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        logger.error(traceback.format_exc())
        raise

def main():
    global opt
    
    parser = argparse.ArgumentParser(description='LiveTalking Server')
    parser.add_argument('--transport', type=str, default='webrtc', help='Transport: webrtc or rtmp')
    parser.add_argument('--model', type=str, default='musetalk', help='Model: musetalk, wav2lip, ultralight')
    parser.add_argument('--tts', type=str, default='xtts', help='TTS engine')
    parser.add_argument('--TTS_SERVER', type=str, default='http://localhost:17860/', help='TTS server URL')
    parser.add_argument('--REF_FILE', type=str, default=None, help='Reference audio file')
    parser.add_argument('--REF_TEXT', type=str, default=None, help='Reference text')
    parser.add_argument('--avatar_id', type=str, default='avator_1', help='Avatar ID')
    parser.add_argument('--max_session', type=int, default=1, help='Max concurrent sessions')
    parser.add_argument('--listenport', type=int, default=8010, help='Listen port')
    parser.add_argument('--fps', type=int, default=50, help='FPS')
    parser.add_argument('--W', type=int, default=450, help='Width')
    parser.add_argument('--H', type=int, default=450, help='Height')
    parser.add_argument('--batch_size', type=int, default=16, help='Batch size')
    parser.add_argument('--l', type=int, default=10)
    parser.add_argument('--m', type=int, default=8)
    parser.add_argument('--r', type=int, default=10)
    parser.add_argument('--customvideo_config', type=str, default='')
    parser.add_argument('--push_url', type=str, default='')
    parser.add_argument('--customopt', type=str, nargs='*', default=[])
    
    opt = parser.parse_args()
    
    logger.info("=" * 50)
    logger.info("LiveTalking Server Starting")
    logger.info("=" * 50)
    logger.info(f"Transport: {opt.transport}")
    logger.info(f"Model: {opt.model}")
    logger.info(f"Avatar: {opt.avatar_id}")
    logger.info(f"Port: {opt.listenport}")
    logger.info(f"Max sessions: {opt.max_session}")
    logger.info("=" * 50)
    
    # 加载模型
    load_models()
    
    # 创建Web应用
    webapp = web.Application()
    webapp.on_shutdown.append(on_shutdown)
    
    # 注册路由
    webapp.router.add_post('/offer', offer)
    webapp.router.add_post('/human', human)
    webapp.router.add_post('/humanaudio', humanaudio)
    webapp.router.add_post('/interrupt', interrupt_talk)
    webapp.router.add_post('/set_audiotype', set_audiotype)
    webapp.router.add_get('/health', health)
    
    # 静态文件
    webapp.router.add_static('/web/', path='web', name='web')
    
    # 根路径重定向
    webapp.router.add_get('/', lambda r: web.HTTPFound('/web/webrtcapi.html'))
    
    # 添加player.html的直接访问路由
    async def serve_player(request):
        return web.FileResponse('web/player.html')
    webapp.router.add_get('/player.html', serve_player)
    
    logger.info(f"Starting server on http://0.0.0.0:{opt.listenport}")
    logger.info(f"WebRTC test page: http://localhost:{opt.listenport}/web/webrtcapi.html")
    logger.info(f"Player page: http://localhost:{opt.listenport}/player.html")
    
    web.run_app(webapp, host='0.0.0.0', port=opt.listenport, access_log=logger)

if __name__ == '__main__':
    main()
