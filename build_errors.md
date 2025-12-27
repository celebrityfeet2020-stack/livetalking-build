# 构建错误记录

## TTS Frontend 构建失败

**错误信息：**
```
ERROR: failed to build: failed to solve: failed to compute cache key: failed to calculate checksum of ref ck5fyevt5wo9bdu0mt1dgrh6::lyetphb9ekhavb8vrrjdaod7: "/static": not found
```

**原因分析：**
Dockerfile中引用了 `COPY static/ /app/static/` 但 static 目录是空的或不存在。

**解决方案：**
创建一个占位文件或空的 .gitkeep 文件在 static 目录中。


## IndexTTS2 构建失败

**错误信息：**
```
ERROR: failed to build: failed to solve: process "/bin/sh -c pip install --no-cache-dir -r requirements.txt" did not complete successfully: exit code: 1
```

**原因分析：**
IndexTTS2仓库的requirements.txt安装失败，可能是因为：
1. 仓库地址错误（github.com/index-tts/index-tts可能不存在）
2. requirements.txt中有无法安装的依赖

**解决方案：**
需要检查并修复IndexTTS2的Dockerfile，确保正确的仓库地址和依赖安装。


## LiveTalking 构建失败

**错误信息：**
```
ERROR: failed to build: failed to solve: process "/bin/sh -c pip install --no-cache-dir aiortc==1.6.0" did not complete successfully: exit code: 1
```

**原因分析：**
aiortc==1.6.0版本安装失败。这可能是因为：
1. 该版本不存在或已被删除
2. 需要特定的系统依赖

**解决方案：**
需要修改Dockerfile，使用正确的aiortc版本（如1.9.0或最新版本）。


## TTS Frontend 构建失败 (第二次)

**错误信息：**
```
ERROR: failed to build: failed to solve: failed to compute cache key: failed to calculate checksum of ref: "/||": not found
```

**原因分析：**
Dockerfile中的 `COPY templates/ /app/templates/` 失败，因为templates目录不存在。

**解决方案：**
需要创建templates目录和基本的模板文件。


## LiveTalking 构建失败 (第二次)

**错误信息：**
```
ERROR: failed to build: failed to solve: process "/bin/sh -c pip install --no-cache-dir av==10.0.0 soundfile==0.12.1 librosa==0.10.1 pydub==0.25.1" did not complete successfully: exit code: 1
```

**原因分析：**
av==10.0.0版本安装失败，可能与其他依赖不兼容。

**解决方案：**
修改av版本为11.0.0或移除版本限制。
