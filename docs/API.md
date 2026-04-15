# FlowTTS 接口说明

## 1. 健康检查

- 方法：`GET /health`
- 说明：检查服务是否启动成功。

示例响应：

```json
{
  "status": "ok",
  "llm_provider": "ZhipuAI",
  "llm_model": "glm-4.5-flash",
  "input_mode": "Browser SpeechRecognition",
  "output_mode": "Browser SpeechSynthesis"
}
```

## 2. 运行配置

- 方法：`GET /api/v1/realtime/config`
- 说明：返回当前前后端语音对话模式和 WebSocket 地址。

示例响应：

```json
{
  "websocket_path": "/api/v1/ws/chat",
  "llm_provider": "ZhipuAI",
  "llm_model": "glm-4.5-flash",
  "input_mode": "Browser SpeechRecognition",
  "output_mode": "Browser SpeechSynthesis",
  "notes": [
    "浏览器负责本地语音识别和本地语音播报，后端只负责流式对话。",
    "当前实现优先保障秒回和稳定性，不依赖智谱 Realtime/TTS 额度。",
    "推荐使用最新版 Chrome 或 Edge 打开首页。"
  ]
}
```

## 3. 流式对话 WebSocket

- 地址：`/api/v1/ws/chat`
- 协议：WebSocket
- 方向：浏览器发送文本，后端返回流式文本事件；浏览器收到分句事件后立即语音播报。

### 3.1 客户端发送消息

发送用户文本：

```json
{
  "type": "user_text",
  "text": "帮我规划一个杭州周末两日游"
}
```

清空上下文：

```json
{
  "type": "clear_history"
}
```

心跳：

```json
{
  "type": "ping"
}
```

### 3.2 服务端事件

连接建立：

```json
{
  "type": "ready",
  "session_id": "2c3f8c2a...",
  "llm_model": "glm-4.5-flash",
  "input_mode": "browser_speech_recognition",
  "output_mode": "browser_speech_synthesis"
}
```

收到用户文本：

```json
{
  "type": "user_text_received",
  "turn_id": "f9da5db5c163",
  "text": "帮我规划一个杭州周末两日游"
}
```

文本增量：

```json
{
  "type": "assistant_delta",
  "turn_id": "f9da5db5c163",
  "delta": "可以，"
}
```

可播报分句：

```json
{
  "type": "assistant_sentence",
  "turn_id": "f9da5db5c163",
  "text": "可以，先把西湖和河坊街放在第一天。"
}
```

回复完成：

```json
{
  "type": "assistant_done",
  "turn_id": "f9da5db5c163",
  "text": "可以，先把西湖和河坊街放在第一天。第二天去灵隐寺和龙井村。"
}
```

异常：

```json
{
  "type": "error",
  "turn_id": "f9da5db5c163",
  "message": "流式对话异常：..."
}
```

## 4. 首页演示

- 地址：`GET /`
- 说明：内置浏览器语音对话页面。
- 建议：桌面版 Chrome / Edge，首次点击“开始说话”时允许麦克风权限。
