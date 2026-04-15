from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    llm_provider: str = "ZhipuAI"
    llm_model: str
    input_mode: str = "Browser SpeechRecognition"
    output_mode: str = "Browser SpeechSynthesis"


class RealtimeConfigResponse(BaseModel):
    websocket_path: str = Field(..., description="WebSocket path for streaming chat")
    llm_provider: str = "ZhipuAI"
    llm_model: str
    input_mode: str = "Browser SpeechRecognition"
    output_mode: str = "Browser SpeechSynthesis"
    notes: list[str]
