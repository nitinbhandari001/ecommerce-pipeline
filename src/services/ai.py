"""Multi-provider LLM service (Groq → Gemini → OpenRouter cascade)."""
from __future__ import annotations

from dataclasses import dataclass

import structlog
from openai import AsyncOpenAI

from ..config import Settings
from ..exceptions import AIServiceError

log = structlog.get_logger(__name__)


@dataclass
class LLMProvider:
    name: str
    api_key: str
    base_url: str
    model: str

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)


class AIService:
    def __init__(self, providers: list[LLMProvider]) -> None:
        self._providers = [p for p in providers if p.is_configured]
        self._clients: list[tuple[LLMProvider, AsyncOpenAI]] = [
            (p, AsyncOpenAI(api_key=p.api_key, base_url=p.base_url))
            for p in self._providers
        ]

    @classmethod
    def from_settings(cls, settings: "Settings") -> "AIService":
        return cls(
            [
                LLMProvider(
                    name="groq",
                    api_key=settings.groq_api_key,
                    base_url="https://api.groq.com/openai/v1",
                    model="llama-3.1-8b-instant",
                ),
                LLMProvider(
                    name="gemini",
                    api_key=settings.gemini_api_key,
                    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                    model="gemini-2.0-flash",
                ),
                LLMProvider(
                    name="openrouter",
                    api_key=settings.openrouter_api_key,
                    base_url="https://openrouter.ai/api/v1",
                    model="meta-llama/llama-3.1-8b-instruct:free",
                ),
            ]
        )

    async def call_llm(self, system: str, user: str) -> str | None:
        """Try providers in cascade order. Returns text or None if all fail."""
        for provider, client in self._clients:
            try:
                response = await client.chat.completions.create(
                    model=provider.model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    max_tokens=1024,
                )
                return response.choices[0].message.content
            except Exception as exc:
                log.warning("llm_provider_failed", provider=provider.name, error=str(exc))
        return None

    @property
    def has_providers(self) -> bool:
        return bool(self._providers)
