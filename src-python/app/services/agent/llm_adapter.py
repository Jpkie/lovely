"""LLM 适配器 - 统一模型接口"""

import asyncio
import json
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional

from .schemas import (
    LLMResponse,
    Message,
    ModelConfig,
    ModelProvider,
    ModelRole,
    RoleModelConfig,
)


class BaseLLMAdapter(ABC):
    """LLM 适配器基类"""

    def __init__(self, config: ModelConfig):
        self.config = config

    @abstractmethod
    async def chat(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        pass

    @abstractmethod
    async def stream_chat(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        pass


def _make_sync_request(
    url: str,
    headers: Dict[str, str],
    payload: Dict[str, Any],
    timeout: int,
) -> Dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_text = e.read().decode("utf-8")
        raise RuntimeError(f"HTTP error {e.code}: {error_text}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"URL error: {e.reason}")


class OpenAIAdapter(BaseLLMAdapter):
    """OpenAI 适配器"""

    async def chat(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        url = f"{self.config.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }

        payload = {
            "model": self.config.model_name,
            "messages": [
                {"role": m.role.value, "content": m.content} for m in messages
            ],
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
        }

        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None, _make_sync_request, url, headers, payload, self.config.timeout
        )

        choice = data["choices"][0]
        return LLMResponse(
            content=choice["message"]["content"],
            model=data.get("model", self.config.model_name),
            provider=ModelProvider.OPENAI,
            tokens_used=data.get("usage", {}).get("total_tokens"),
            finish_reason=choice.get("finish_reason"),
            raw_response=data,
        )

    async def stream_chat(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        url = f"{self.config.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }

        payload = {
            "model": self.config.model_name,
            "messages": [
                {"role": m.role.value, "content": m.content} for m in messages
            ],
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            "stream": True,
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(
            None, lambda: urllib.request.urlopen(req, timeout=self.config.timeout)
        )

        while True:
            line = await loop.run_in_executor(None, resp.readline)
            if not line:
                break
            line = line.decode("utf-8").strip()
            if not line:
                continue
            if line.startswith("data: "):
                if line == "data: [DONE]":
                    break
                data = json.loads(line[6:])
                delta = data["choices"][0].get("delta", {})
                if "content" in delta:
                    yield delta["content"]


class DeepSeekAdapter(BaseLLMAdapter):
    """DeepSeek 适配器"""

    async def chat(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        url = f"{self.config.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }

        payload = {
            "model": self.config.model_name,
            "messages": [
                {"role": m.role.value, "content": m.content} for m in messages
            ],
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
        }

        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None, _make_sync_request, url, headers, payload, self.config.timeout
        )

        choice = data["choices"][0]
        return LLMResponse(
            content=choice["message"]["content"],
            model=data.get("model", self.config.model_name),
            provider=ModelProvider.DEEPSEEK,
            tokens_used=data.get("usage", {}).get("total_tokens"),
            finish_reason=choice.get("finish_reason"),
            raw_response=data,
        )

    async def stream_chat(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        url = f"{self.config.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }

        payload = {
            "model": self.config.model_name,
            "messages": [
                {"role": m.role.value, "content": m.content} for m in messages
            ],
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            "stream": True,
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(
            None, lambda: urllib.request.urlopen(req, timeout=self.config.timeout)
        )

        while True:
            line = await loop.run_in_executor(None, resp.readline)
            if not line:
                break
            line = line.decode("utf-8").strip()
            if not line:
                continue
            if line.startswith("data: "):
                if line == "data: [DONE]":
                    break
                data = json.loads(line[6:])
                delta = data["choices"][0].get("delta", {})
                if "content" in delta:
                    yield delta["content"]


class ClaudeAdapter(BaseLLMAdapter):
    """Claude 适配器"""

    async def chat(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        url = f"{self.config.base_url}/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
        }

        formatted_messages = []
        for m in messages:
            if m.role == ModelRole.SYSTEM:
                formatted_messages.append(
                    {"role": "user", "content": f"System: {m.content}"}
                )
                formatted_messages.append(
                    {"role": "assistant", "content": "Understood."}
                )
            elif m.role == ModelRole.USER:
                formatted_messages.append({"role": "user", "content": m.content})
            elif m.role == ModelRole.ASSISTANT:
                formatted_messages.append({"role": "assistant", "content": m.content})

        payload = {
            "model": self.config.model_name,
            "messages": formatted_messages,
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
        }

        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None, _make_sync_request, url, headers, payload, self.config.timeout
        )

        return LLMResponse(
            content=data["content"][0]["text"],
            model=data.get("model", self.config.model_name),
            provider=ModelProvider.CLAUDE,
            tokens_used=data.get("usage", {}).get("input_tokens"),
            finish_reason=data.get("stop_reason"),
            raw_response=data,
        )

    async def stream_chat(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        url = f"{self.config.base_url}/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
        }

        formatted_messages = []
        for m in messages:
            if m.role == ModelRole.SYSTEM:
                formatted_messages.append(
                    {"role": "user", "content": f"System: {m.content}"}
                )
                formatted_messages.append(
                    {"role": "assistant", "content": "Understood."}
                )
            elif m.role == ModelRole.USER:
                formatted_messages.append({"role": "user", "content": m.content})
            elif m.role == ModelRole.ASSISTANT:
                formatted_messages.append({"role": "assistant", "content": m.content})

        payload = {
            "model": self.config.model_name,
            "messages": formatted_messages,
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            "stream": True,
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(
            None, lambda: urllib.request.urlopen(req, timeout=self.config.timeout)
        )

        while True:
            line = await loop.run_in_executor(None, resp.readline)
            if not line:
                break
            line = line.decode("utf-8").strip()
            if not line:
                continue
            if line.startswith("data: "):
                if line == "data: [DONE]":
                    break
                data = json.loads(line[6:])
                if data.get("type") == "content_block_delta":
                    yield data.get("delta", {}).get("text", "")


class CustomAdapter(BaseLLMAdapter):
    """自定义模型适配器 (OpenAI 兼容格式)"""

    async def chat(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        url = f"{self.config.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
        }

        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        payload = {
            "model": self.config.model_name,
            "messages": [
                {"role": m.role.value, "content": m.content} for m in messages
            ],
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
        }

        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None, _make_sync_request, url, headers, payload, self.config.timeout
        )

        choice = data["choices"][0]
        return LLMResponse(
            content=choice["message"]["content"],
            model=data.get("model", self.config.model_name),
            provider=ModelProvider.CUSTOM,
            tokens_used=data.get("usage", {}).get("total_tokens"),
            finish_reason=choice.get("finish_reason"),
            raw_response=data,
        )

    async def stream_chat(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        url = f"{self.config.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
        }

        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        payload = {
            "model": self.config.model_name,
            "messages": [
                {"role": m.role.value, "content": m.content} for m in messages
            ],
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            "stream": True,
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(
            None, lambda: urllib.request.urlopen(req, timeout=self.config.timeout)
        )

        while True:
            line = await loop.run_in_executor(None, resp.readline)
            if not line:
                break
            line = line.decode("utf-8").strip()
            if not line:
                continue
            if line.startswith("data: "):
                if line == "data: [DONE]":
                    break
                data = json.loads(line[6:])
                delta = data["choices"][0].get("delta", {})
                if "content" in delta:
                    yield delta["content"]


class LLMAdapterFactory:
    """LLM 适配器工厂"""

    _adapters: Dict[ModelProvider, type] = {
        ModelProvider.OPENAI: OpenAIAdapter,
        ModelProvider.DEEPSEEK: DeepSeekAdapter,
        ModelProvider.CLAUDE: ClaudeAdapter,
        ModelProvider.CUSTOM: CustomAdapter,
    }

    @classmethod
    def create(cls, config: ModelConfig) -> BaseLLMAdapter:
        adapter_class = cls._adapters.get(config.provider)
        if not adapter_class:
            raise ValueError(f"Unknown provider: {config.provider}")
        return adapter_class(config)


class UnifiedLLMAdapter:
    """统一 LLM 适配器 - 支持角色模型回退"""

    def __init__(self, role_config: RoleModelConfig):
        self.role_config = role_config
        self._adapters: Dict[str, BaseLLMAdapter] = {}

    def _get_adapter(self, role: str) -> BaseLLMAdapter:
        if role not in self._adapters:
            config = getattr(self.role_config, role, None)
            if not config:
                raise ValueError(f"Unknown role: {role}")
            self._adapters[role] = LLMAdapterFactory.create(config)
        return self._adapters[role]

    async def chat_with_role(
        self,
        role: str,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        adapter = self._get_adapter(role)
        config = getattr(self.role_config, role)

        try:
            return await adapter.chat(messages, temperature, max_tokens)
        except Exception as e:
            if config.fallback_model and config.model_name != config.fallback_model:
                fallback_config = ModelConfig(
                    provider=config.provider,
                    model_name=config.fallback_model,
                    api_key=config.api_key,
                    base_url=config.base_url,
                    temperature=config.temperature,
                    max_tokens=config.max_tokens,
                    timeout=config.timeout,
                    fallback_model=None,
                )
                fallback_adapter = LLMAdapterFactory.create(fallback_config)
                return await fallback_adapter.chat(messages, temperature, max_tokens)
            raise

    async def planner_chat(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        return await self.chat_with_role("planner", messages, temperature, max_tokens)

    async def executor_chat(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        return await self.chat_with_role("executor", messages, temperature, max_tokens)

    async def summarizer_chat(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        return await self.chat_with_role(
            "summarizer", messages, temperature, max_tokens
        )

    async def chat_as_router(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        role = "router"
        if (
            not hasattr(self.role_config, role)
            or getattr(self.role_config, role) is None
        ):
            return await self.chat_with_role(
                "planner", messages, temperature, max_tokens
            )
        return await self.chat_with_role(role, messages, temperature, max_tokens)

    async def chat_as_planner(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        role = "planner"
        if (
            not hasattr(self.role_config, role)
            or getattr(self.role_config, role) is None
        ):
            return await self.chat_with_role(
                "planner", messages, temperature, max_tokens
            )
        return await self.chat_with_role(role, messages, temperature, max_tokens)

    async def chat_as_analyst(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        role = "analyst"
        if (
            not hasattr(self.role_config, role)
            or getattr(self.role_config, role) is None
        ):
            if hasattr(self.role_config, "summarizer") and self.role_config.summarizer:
                return await self.chat_with_role(
                    "summarizer", messages, temperature, max_tokens
                )
            return await self.chat_with_role(
                "planner", messages, temperature, max_tokens
            )
        return await self.chat_with_role(role, messages, temperature, max_tokens)

    async def chat_as_judge(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        role = "judge"
        if (
            not hasattr(self.role_config, role)
            or getattr(self.role_config, role) is None
        ):
            return await self.chat_with_role(
                "planner", messages, temperature, max_tokens
            )
        return await self.chat_with_role(role, messages, temperature, max_tokens)

    async def chat(
        self,
        messages: List[Message],
        provider: Optional[ModelProvider] = None,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        if provider is None:
            provider = self.role_config.planner.provider
        if model_name is None:
            model_name = self.role_config.planner.model_name

        config = ModelConfig(
            provider=provider,
            model_name=model_name,
            api_key=self.role_config.planner.api_key,
            base_url=self.role_config.planner.base_url,
            temperature=temperature or self.role_config.planner.temperature,
            max_tokens=max_tokens or self.role_config.planner.max_tokens,
            timeout=self.role_config.planner.timeout,
        )
        adapter = LLMAdapterFactory.create(config)
        return await adapter.chat(messages, temperature, max_tokens)
