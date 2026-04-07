from __future__ import annotations

import json
from typing import Any

import httpx
from openai import OpenAI

from job_agent.config import settings


class ProviderUnavailableError(RuntimeError):
    pass


class LLMRouter:
    def __init__(self) -> None:
        self._openai_client: OpenAI | None = None
        if settings.openai_api_key:
            self._openai_client = OpenAI(api_key=settings.openai_api_key)

    def provider_status(self) -> dict[str, Any]:
        return {
            "lm_studio": {
                "base_url": settings.lm_studio_base_url,
                "small_model_configured": bool(settings.lm_studio_small_model),
                "writer_model_configured": bool(settings.lm_studio_writer_model),
                "reachable": self._lm_studio_reachable(),
            },
            "openai": {
                "review_enabled": settings.use_openai_review,
                "escalation_enabled": settings.use_openai_escalation,
                "api_key_configured": bool(settings.openai_api_key),
                "review_model": settings.openai_review_model,
                "escalation_model": settings.openai_escalation_model,
            },
        }

    def _lm_studio_reachable(self) -> bool:
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{settings.lm_studio_base_url}/models")
                response.raise_for_status()
            return True
        except Exception:
            return False

    def _parse_json_text(self, text: str) -> dict[str, Any]:
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Model did not return valid JSON: {text}") from exc

    def generate_with_lm_studio(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        if not model:
            raise ProviderUnavailableError("LM Studio model is not configured.")

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
        try:
            with httpx.Client(timeout=settings.lm_studio_request_timeout_seconds) as client:
                response = client.post(f"{settings.lm_studio_base_url}/chat/completions", json=payload)
                response.raise_for_status()
            body = response.json()
            message = body["choices"][0]["message"]["content"]
            return self._parse_json_text(message)
        except Exception as exc:
            raise ProviderUnavailableError("LM Studio request failed.") from exc

    def generate_with_openai(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        if self._openai_client is None:
            raise ProviderUnavailableError("OpenAI API key is not configured.")

        response = self._openai_client.responses.create(
            model=model,
            input=[
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": system_prompt}],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": user_prompt}],
                },
            ],
        )
        return self._parse_json_text(response.output_text)
