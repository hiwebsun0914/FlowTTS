# FlowTTS

一个可直接跑的 FastAPI 语音对话 Demo：

- 本地浏览器麦克风输入
- 智谱 AI `glm-4.5-flash` 流式生成回复
- 浏览器原生 TTS 分句播报，尽量做到首字快、首句快
- 自带网页演示、接口说明和 `.gitignore`

## 为什么这样实现

我在 2026-04-15 实测了你提供的 Key：

- `chat/completions` 可正常流式返回
- `audio/speech` 返回余额或资源包不足
- `GLM-Realtime` 会话建立后返回欠费错误

所以这一版采用了最稳妥、也最容易做到“秒回”的组合：

- 大模型仍然使用智谱 AI
- 本地语音识别使用浏览器 `SpeechRecognition`
- 本地语音播报使用浏览器 `SpeechSynthesis`

这样你马上就能跑起来，不需要额外购买智谱语音额度。

## 目录结构

```text
.
├─ app
│  ├─ main.py
│  ├─ config.py
│  ├─ schemas.py
│  ├─ services
│  │  ├─ streaming.py
│  │  └─ zhipu.py
│  └─ static
│     ├─ index.html
│     ├─ app.js
│     └─ style.css
├─ docs
│  └─ API.md
├─ .env
├─ .env.example
├─ .gitignore
└─ requirements.txt
```

## 安装与启动

### 1. 安装依赖

```powershell
pip install -r requirements.txt
```

### 2. 启动服务

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. 打开页面

浏览器访问：

```text
http://127.0.0.1:8000
```

Swagger 接口文档：

```text
http://127.0.0.1:8000/docs
```

## 接口概览

- `GET /health`
- `GET /api/v1/realtime/config`
- `WS /api/v1/ws/chat`
- `GET /`

详细协议见 [docs/API.md](./docs/API.md)。

## 秒回优化点

- 智谱使用 `glm-4.5-flash`，优先低时延
- 后端启用真正的 SSE 流式读取
- 文字一边生成一边推送给前端
- 前端按中文标点和长度分句，拿到一小句就立即播报
- 新一轮提问会自动打断上一轮播报，减少等待

## 浏览器要求

- 推荐：Chrome / Edge 最新版
- 需要允许麦克风权限
- 如果浏览器不支持语音识别，仍然可以用页面里的文本输入框测试流式回复

## 后续可升级方向

- 接入智谱 Realtime，做真正的双向音频流
- 替换浏览器 ASR 为服务端 ASR
- 替换浏览器 TTS 为服务端流式音频回传
- 增加会话持久化、身份鉴权、限流和日志追踪
