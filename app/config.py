from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT_DIR / "app" / "static"

load_dotenv(ROOT_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "FlowTTS Voice Chat")
    api_prefix: str = "/api/v1"
    zhipu_api_key: str = os.getenv("ZHIPU_API_KEY", "")
    zhipu_base_url: str = os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
    zhipu_model: str = os.getenv("ZHIPU_MODEL", "glm-4.5-flash")
    system_prompt: str = os.getenv(
        "SYSTEM_PROMPT",
        "你是一个中文语音助手。请用自然、口语化、简洁的中文回答，优先给出直接答案，避免冗长铺垫。",
    )
    max_history_turns: int = int(os.getenv("MAX_HISTORY_TURNS", "6"))
    connect_timeout_s: float = float(os.getenv("CONNECT_TIMEOUT_S", "20"))

    @property
    def chat_completions_url(self) -> str:
        return f"{self.zhipu_base_url}/chat/completions"

    @property
    def is_configured(self) -> bool:
        return bool(self.zhipu_api_key.strip())


settings = Settings()
