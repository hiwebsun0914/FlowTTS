# FlowTTS

一个可直接跑的 FastAPI 语音对话 Demo：

- 本地浏览器麦克风输入
- 智谱 AI `glm-4.5-flash` 流式生成回复
- 浏览器原生 TTS 分句播报，尽量做到首字快、首句快
- 自带网页演示、接口说明和 `.gitignore`

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

补充自己的智谱APIkey

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
