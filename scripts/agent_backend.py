"""Backends de agente usados pelo orquestrador.

Deliberadamente sem a dependência pip `anthropic`: a chamada à API da
Claude é feita via `urllib.request` da biblioteca padrão. Isso mantém a
história de reprodutibilidade deste repositório (versões fixadas, sem
"latest" silencioso — mesmo espírito da Seção 9.3 do paper, que fixa
versão do verificador/solucionador) sem adicionar uma dependência externa
só para uma chamada HTTP simples.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


class AgentBackend:
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError


class MockBackend(AgentBackend):
    """Sem chamadas de rede. Devolve uma sequência roteirizada e fixa de
    respostas, usada para testar o próprio orquestrador (não é uma
    execução experimental — ver docs/orchestration.md, seção "Modo mock").
    """

    def __init__(self, responses: list[str]):
        self._responses = list(responses)
        self._calls: list[tuple[str, str]] = []

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        self._calls.append((system_prompt, user_prompt))
        if not self._responses:
            raise RuntimeError("MockBackend: respostas roteirizadas esgotadas")
        return self._responses.pop(0)


class AnthropicBackend(AgentBackend):
    """Chama a Messages API da Anthropic diretamente. Requer
    `ANTHROPIC_API_KEY` no ambiente. Ver
    https://docs.claude.com/en/api/messages para o formato da requisição.
    """

    API_URL = "https://api.anthropic.com/v1/messages"
    API_VERSION = "2023-06-01"

    def __init__(self, model: str, max_tokens: int = 4096, api_key: str | None = None):
        self.model = model
        self.max_tokens = max_tokens
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY não definida no ambiente — "
                "necessária para AnthropicBackend (ver docs/orchestration.md)."
            )
        self.last_usage: dict = {}

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        req = urllib.request.Request(
            self.API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "content-type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": self.API_VERSION,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Anthropic API HTTP {exc.code}: {detail}") from exc

        self.last_usage = body.get("usage", {})
        parts = [block.get("text", "") for block in body.get("content", []) if block.get("type") == "text"]
        return "".join(parts)


def make_backend(name: str, model: str = "") -> AgentBackend:
    if name == "mock":
        raise ValueError("MockBackend precisa de respostas roteirizadas — instancie diretamente, não via make_backend")
    if name == "anthropic":
        if not model:
            raise ValueError("--model é obrigatório para o backend 'anthropic'")
        return AnthropicBackend(model=model)
    raise ValueError(f"backend desconhecido: {name!r} (use 'anthropic', ou MockBackend diretamente para dry-run)")
