from __future__ import annotations

import asyncio
import json
import uuid
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, field

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import STATIC_DIR, settings
from app.schemas import HealthResponse, RealtimeConfigResponse
from app.services.streaming import normalize_text, pull_speakable_segments, trim_history
from app.services.zhipu import ZhipuAPIError, stream_chat_completion


@asynccontextmanager
async def lifespan(_: FastAPI):
    timeout = httpx.Timeout(connect=settings.connect_timeout_s, read=None, write=30.0, pool=30.0)
    client = httpx.AsyncClient(timeout=timeout)
    app.state.http_client = client
    try:
        yield
    finally:
        await client.aclose()


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="FastAPI + ZhipuAI streaming chat service with local browser voice input/output.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@dataclass
class ConversationState:
    history: list[dict[str, str]] = field(default_factory=list)
    send_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    current_task: asyncio.Task | None = None
    current_turn_id: str | None = None


async def send_event(websocket: WebSocket, lock: asyncio.Lock, event_type: str, **payload: object) -> None:
    async with lock:
        await websocket.send_json({"type": event_type, **payload})


async def cancel_current_task(state: ConversationState) -> None:
    if state.current_task and not state.current_task.done():
        state.current_task.cancel()
        with suppress(asyncio.CancelledError):
            await state.current_task


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    return HealthResponse(llm_model=settings.zhipu_model)


@app.get(f"{settings.api_prefix}/realtime/config", response_model=RealtimeConfigResponse, tags=["system"])
async def realtime_config() -> RealtimeConfigResponse:
    return RealtimeConfigResponse(
        websocket_path=f"{settings.api_prefix}/ws/chat",
        llm_model=settings.zhipu_model,
        notes=[
            "浏览器负责本地语音识别和本地语音播报，后端只负责流式对话。",
            "当前实现优先保障秒回和稳定性，不依赖智谱 Realtime/TTS 额度。",
            "推荐使用最新版 Chrome 或 Edge 打开首页。",
        ],
    )


async def process_turn(websocket: WebSocket, state: ConversationState, turn_id: str) -> None:
    if not settings.is_configured:
        await send_event(
            websocket,
            state.send_lock,
            "error",
            turn_id=turn_id,
            message="未检测到 ZHIPU_API_KEY，请先在 .env 中配置。",
        )
        return

    assistant_text_parts: list[str] = []
    speak_buffer = ""
    messages = [{"role": "system", "content": settings.system_prompt}, *state.history]

    await send_event(websocket, state.send_lock, "assistant_started", turn_id=turn_id)

    try:
        async for chunk in stream_chat_completion(
            client=app.state.http_client,
            settings=settings,
            messages=messages,
        ):
            if not chunk.delta:
                continue

            assistant_text_parts.append(chunk.delta)
            speak_buffer += chunk.delta

            await send_event(
                websocket,
                state.send_lock,
                "assistant_delta",
                turn_id=turn_id,
                delta=chunk.delta,
            )

            segments, speak_buffer = pull_speakable_segments(speak_buffer)
            for segment in segments:
                await send_event(
                    websocket,
                    state.send_lock,
                    "assistant_sentence",
                    turn_id=turn_id,
                    text=segment,
                )

        final_segments, _ = pull_speakable_segments(speak_buffer, final=True)
        for segment in final_segments:
            await send_event(
                websocket,
                state.send_lock,
                "assistant_sentence",
                turn_id=turn_id,
                text=segment,
            )

        assistant_text = "".join(assistant_text_parts).strip()
        if assistant_text:
            state.history.append({"role": "assistant", "content": assistant_text})
            state.history = trim_history(state.history, settings.max_history_turns)

        await send_event(
            websocket,
            state.send_lock,
            "assistant_done",
            turn_id=turn_id,
            text=assistant_text,
        )
    except asyncio.CancelledError:
        await send_event(websocket, state.send_lock, "assistant_cancelled", turn_id=turn_id)
        raise
    except ZhipuAPIError as exc:
        await send_event(websocket, state.send_lock, "error", turn_id=turn_id, message=str(exc))
    except Exception as exc:
        await send_event(
            websocket,
            state.send_lock,
            "error",
            turn_id=turn_id,
            message=f"流式对话异常：{exc}",
        )


@app.websocket(f"{settings.api_prefix}/ws/chat")
async def websocket_chat(websocket: WebSocket) -> None:
    await websocket.accept()

    state = ConversationState()
    session_id = uuid.uuid4().hex

    await send_event(
        websocket,
        state.send_lock,
        "ready",
        session_id=session_id,
        llm_model=settings.zhipu_model,
        input_mode="browser_speech_recognition",
        output_mode="browser_speech_synthesis",
    )

    try:
        while True:
            raw_text = await websocket.receive_text()
            try:
                message = json.loads(raw_text)
            except json.JSONDecodeError:
                await send_event(websocket, state.send_lock, "error", message="消息必须是 JSON。")
                continue

            message_type = message.get("type")

            if message_type == "ping":
                await send_event(websocket, state.send_lock, "pong")
                continue

            if message_type == "clear_history":
                await cancel_current_task(state)
                state.history.clear()
                await send_event(websocket, state.send_lock, "history_cleared")
                continue

            if message_type != "user_text":
                await send_event(
                    websocket,
                    state.send_lock,
                    "error",
                    message=f"不支持的消息类型：{message_type}",
                )
                continue

            user_text = normalize_text(str(message.get("text", "")))
            if not user_text:
                await send_event(websocket, state.send_lock, "error", message="text 不能为空。")
                continue

            await cancel_current_task(state)

            turn_id = uuid.uuid4().hex[:12]
            state.current_turn_id = turn_id
            state.history.append({"role": "user", "content": user_text})
            state.history = trim_history(state.history, settings.max_history_turns)

            await send_event(
                websocket,
                state.send_lock,
                "user_text_received",
                turn_id=turn_id,
                text=user_text,
            )

            state.current_task = asyncio.create_task(process_turn(websocket, state, turn_id))
    except WebSocketDisconnect:
        await cancel_current_task(state)
    finally:
        await cancel_current_task(state)
