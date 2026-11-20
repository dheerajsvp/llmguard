"""Gemini provider. Needs the optional extra: pip install -e ".[gemini]"."""

import os


class GeminiProvider:
    def __init__(self, api_key: str | None = None, model: str = "gemini-2.5-flash") -> None:
        # Imported here so the core library and CI work without the SDK installed.
        from google import genai

        key = api_key or os.environ.get("GEMINI_API_KEY")
        if not key:
            raise ValueError("Set GEMINI_API_KEY or pass api_key")
        self._client = genai.Client(api_key=key)
        self._model = model

    def generate(self, prompt: str, system: str | None = None) -> str:
        from google.genai import types

        config = types.GenerateContentConfig(system_instruction=system) if system else None
        response = self._client.models.generate_content(
            model=self._model, contents=prompt, config=config
        )
        return response.text or ""
