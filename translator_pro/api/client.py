from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional

import requests


class APIError(RuntimeError):
    pass


@dataclass
class StreamDelta:
    content: str = ""
    reasoning: str = ""
    raw: Optional[Dict[str, Any]] = None


class LLMClient:
    """Small multi-provider adapter.

    Fully supports OpenAI-compatible chat/completions streaming, including
    DeepSeek-style `reasoning_content`. Claude/Gemini have basic adapters so
    the GUI can hold these configurations, but reasoning_content is not exposed
    by those providers.
    """

    def __init__(self, api_config: Dict[str, Any]) -> None:
        self.cfg = dict(api_config or {})
        self.provider = self.cfg.get("provider", "openai_compatible")
        self.timeout = float(self.cfg.get("timeout") or 60)
        self.proxies = self._build_proxies()

    def _build_proxies(self) -> Dict[str, str] | None:
        proxies: Dict[str, str] = {}
        if self.cfg.get("http_proxy"):
            proxies["http"] = self.cfg["http_proxy"]
        if self.cfg.get("https_proxy"):
            proxies["https"] = self.cfg["https_proxy"]
        return proxies or None

    @staticmethod
    def _strip_slash(url: str) -> str:
        return (url or "").rstrip("/")

    def _headers_openai(self) -> Dict[str, str]:
        api_key = self.cfg.get("api_key") or ""
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def _messages(self, system_prompt: str, user_text: str) -> List[Dict[str, str]]:
        return [
            {"role": "system", "content": system_prompt or "You are a professional translator."},
            {"role": "user", "content": user_text or ""},
        ]

    def test_connection(self) -> tuple[bool, str, int]:
        start = time.perf_counter()
        try:
            if self.provider == "anthropic":
                text = self.complete("You are a connection tester.", "Reply OK only.", stream=False, max_tokens=16)
            elif self.provider == "gemini":
                text = self.complete("You are a connection tester.", "Reply OK only.", stream=False, max_tokens=16)
            else:
                text = self.complete("You are a connection tester.", "Reply OK only.", stream=False, max_tokens=16)
            elapsed = int((time.perf_counter() - start) * 1000)
            return True, (text or "OK")[:80], elapsed
        except Exception as exc:
            elapsed = int((time.perf_counter() - start) * 1000)
            return False, str(exc), elapsed

    def complete(
        self,
        system_prompt: str,
        user_text: str,
        stream: bool = False,
        on_delta: Optional[Callable[[StreamDelta], None]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        retry: int = 1,
    ) -> str:
        for attempt in range(max(0, retry) + 1):
            try:
                if self.provider == "anthropic":
                    return self._complete_anthropic(system_prompt, user_text, stream, on_delta, max_tokens, temperature)
                if self.provider == "gemini":
                    return self._complete_gemini(system_prompt, user_text, stream, on_delta, max_tokens, temperature)
                return self._complete_openai_compatible(system_prompt, user_text, stream, on_delta, max_tokens, temperature)
            except Exception:
                if attempt >= retry:
                    raise
                time.sleep(0.8)
        return ""

    def _complete_openai_compatible(
        self,
        system_prompt: str,
        user_text: str,
        stream: bool,
        on_delta: Optional[Callable[[StreamDelta], None]],
        max_tokens: Optional[int],
        temperature: Optional[float],
    ) -> str:
        base_url = self._strip_slash(self.cfg.get("base_url") or "")
        if not base_url:
            raise APIError("Base URL 不能为空。")
        url = f"{base_url}/chat/completions"
        payload = {
            "model": self.cfg.get("model_name"),
            "messages": self._messages(system_prompt, user_text),
            "temperature": float(temperature if temperature is not None else self.cfg.get("temperature", 0.2)),
            "max_tokens": int(max_tokens or self.cfg.get("max_tokens") or 4096),
            "stream": bool(stream),
        }
        response = requests.post(
            url,
            headers=self._headers_openai(),
            json=payload,
            timeout=self.timeout,
            proxies=self.proxies,
            stream=stream,
        )
        if response.status_code >= 400:
            raise APIError(f"API 请求失败：HTTP {response.status_code}，{response.text[:500]}")

        if not stream:
            data = response.json()
            msg = data.get("choices", [{}])[0].get("message", {})
            reasoning = msg.get("reasoning_content") or ""
            content = msg.get("content") or ""
            if on_delta and reasoning:
                on_delta(StreamDelta(reasoning=reasoning, raw=data))
            if on_delta and content:
                on_delta(StreamDelta(content=content, raw=data))
            return content

        final: List[str] = []
        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            if line.startswith("data:"):
                line = line[5:].strip()
            if line == "[DONE]":
                break
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            choices = data.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta") or {}
            reasoning = delta.get("reasoning_content") or delta.get("reasoning") or ""
            content = delta.get("content") or ""
            if content:
                final.append(content)
            if on_delta and (content or reasoning):
                on_delta(StreamDelta(content=content, reasoning=reasoning, raw=data))
        return "".join(final)

    def _complete_anthropic(
        self,
        system_prompt: str,
        user_text: str,
        stream: bool,
        on_delta: Optional[Callable[[StreamDelta], None]],
        max_tokens: Optional[int],
        temperature: Optional[float],
    ) -> str:
        base_url = self._strip_slash(self.cfg.get("base_url") or "https://api.anthropic.com")
        url = f"{base_url}/v1/messages"
        headers = {
            "x-api-key": self.cfg.get("api_key") or "",
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.cfg.get("model_name"),
            "system": system_prompt or "You are a professional translator.",
            "messages": [{"role": "user", "content": user_text or ""}],
            "temperature": float(temperature if temperature is not None else self.cfg.get("temperature", 0.2)),
            "max_tokens": int(max_tokens or self.cfg.get("max_tokens") or 4096),
            "stream": bool(stream),
        }
        response = requests.post(url, headers=headers, json=payload, timeout=self.timeout, proxies=self.proxies, stream=stream)
        if response.status_code >= 400:
            raise APIError(f"Anthropic 请求失败：HTTP {response.status_code}，{response.text[:500]}")
        if not stream:
            data = response.json()
            parts = data.get("content") or []
            content = "".join(p.get("text", "") for p in parts if p.get("type") == "text")
            if on_delta and content:
                on_delta(StreamDelta(content=content, raw=data))
            return content
        final: List[str] = []
        for line in response.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            raw = line[5:].strip()
            if raw == "[DONE]":
                break
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if data.get("type") == "content_block_delta":
                delta = data.get("delta") or {}
                text = delta.get("text") or ""
                if text:
                    final.append(text)
                    if on_delta:
                        on_delta(StreamDelta(content=text, raw=data))
        return "".join(final)

    def _complete_gemini(
        self,
        system_prompt: str,
        user_text: str,
        stream: bool,
        on_delta: Optional[Callable[[StreamDelta], None]],
        max_tokens: Optional[int],
        temperature: Optional[float],
    ) -> str:
        base_url = self._strip_slash(self.cfg.get("base_url") or "https://generativelanguage.googleapis.com/v1beta")
        model = self.cfg.get("model_name") or "gemini-1.5-flash"
        key = self.cfg.get("api_key") or ""
        method = "streamGenerateContent" if stream else "generateContent"
        sep = "&" if "?" in base_url else "?"
        url = f"{base_url}/models/{model}:{method}{sep}key={key}"
        if stream:
            url += "&alt=sse"
        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt or "You are a professional translator."}]},
            "contents": [{"role": "user", "parts": [{"text": user_text or ""}]}],
            "generationConfig": {
                "temperature": float(temperature if temperature is not None else self.cfg.get("temperature", 0.2)),
                "maxOutputTokens": int(max_tokens or self.cfg.get("max_tokens") or 4096),
            },
        }
        response = requests.post(url, json=payload, timeout=self.timeout, proxies=self.proxies, stream=stream)
        if response.status_code >= 400:
            raise APIError(f"Gemini 请求失败：HTTP {response.status_code}，{response.text[:500]}")
        if not stream:
            data = response.json()
            content = self._gemini_text(data)
            if on_delta and content:
                on_delta(StreamDelta(content=content, raw=data))
            return content
        final: List[str] = []
        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            if line.startswith("data:"):
                line = line[5:].strip()
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            text = self._gemini_text(data)
            if text:
                final.append(text)
                if on_delta:
                    on_delta(StreamDelta(content=text, raw=data))
        return "".join(final)

    @staticmethod
    def _gemini_text(data: Dict[str, Any]) -> str:
        texts: List[str] = []
        for cand in data.get("candidates", []) or []:
            content = cand.get("content") or {}
            for part in content.get("parts", []) or []:
                if part.get("text"):
                    texts.append(part["text"])
        return "".join(texts)
