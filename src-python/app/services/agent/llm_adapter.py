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
    """统一 LLM 适配器 - 支持多角色模型回退

    多模型模式 (multi_model_enabled=True):
        router   → router_model → planner_model → primary
        planner  → planner_model → primary
        analyst  → analyst_model → summarizer_model → primary
        judge    → judge_model → analyst_model → summarizer_model → primary
        executor → executor_model → primary
        summarizer → summarizer_model → primary

    单模型模式 (multi_model_enabled=False 或 agent_settings 未提供):
        所有 chat_as_* 直接回退到 primary（从 settings.ai 读取）

    调试日志打印格式: [role] resolved to [field] (provider/model)
    不打印 API key 等敏感信息。
    """

    def __init__(
        self,
        role_config: Optional[RoleModelConfig] = None,
        agent_settings: Optional[Any] = None,
    ):
        self.role_config = role_config or RoleModelConfig()
        self.agent_settings = agent_settings
        self._adapter_cache: Dict[str, BaseLLMAdapter] = {}

    def _is_multi_model_enabled(self) -> bool:
        """检查是否启用多模型模式"""
        if self.agent_settings is None:
            return False
        return getattr(self.agent_settings, "multi_model_enabled", False)

    def _resolve_primary_model_config(self) -> ModelConfig:
        """从 settings.ai 解析主模型配置（默认模型）"""
        primary = ModelConfig(
            provider=ModelProvider.OPENAI,
            model_name="gpt-4",
            base_url="https://api.openai.com/v1",
        )
        if self.agent_settings is None:
            return primary

        ai_config = getattr(self.agent_settings, "ai", None)
        if ai_config is None:
            return primary

        if isinstance(ai_config, dict):
            primary.provider = ModelProvider(ai_config.get("provider", "openai"))
            primary.model_name = ai_config.get("model", primary.model_name)
            primary.api_key = ai_config.get("api_key")
            primary.base_url = ai_config.get("base_url", primary.base_url)
            primary.temperature = ai_config.get("temperature", primary.temperature)
            primary.max_tokens = ai_config.get("max_tokens", primary.max_tokens)
            primary.timeout = ai_config.get("timeout", primary.timeout)
        return primary

    def _get_model_config(self, role_name: str) -> Optional[ModelConfig]:
        """从 agent_settings 获取指定角色的模型配置"""
        if self.agent_settings is None:
            return getattr(self.role_config, role_name, None)

        role_field_map = {
            "router": "router_model",
            "planner": "planner_model",
            "analyst": "analyst_model",
            "judge": "judge_model",
            "executor": "executor_model",
            "summarizer": "summarizer_model",
        }
        field_name = role_field_map.get(role_name, role_name)
        raw = getattr(self.agent_settings, field_name, None)
        if raw is None:
            return getattr(self.role_config, role_name, None)

        if isinstance(raw, ModelConfig):
            return raw
        if isinstance(raw, dict):
            return ModelConfig(**raw)

        from app.services.settings import AgentModelSettings

        if isinstance(raw, AgentModelSettings):
            return ModelConfig(
                provider=ModelProvider(raw.provider),
                model_name=raw.model_name,
                api_key=raw.api_key,
                base_url=raw.base_url or "https://api.openai.com/v1",
                temperature=raw.temperature,
                max_tokens=raw.max_tokens,
                timeout=raw.timeout,
                fallback_model=raw.fallback_model,
            )
        return None

    def _resolve_role_model_config(self, role: str) -> ModelConfig:
        """解析角色对应的模型配置，统一回退入口

        角色优先用自己的模型配置，未配置时按链回退到 primary。
        multi_model_enabled=False 时直接返回 primary。
        """
        primary = self._resolve_primary_model_config()

        if not self._is_multi_model_enabled():
            print(f"[LLM] multi_model_enabled=False, role={role} → primary")
            return primary

        fallback_chains = {
            "router": ["router_model", "planner_model"],
            "planner": ["planner_model"],
            "analyst": ["analyst_model", "summarizer_model"],
            "judge": ["judge_model", "analyst_model", "summarizer_model"],
        }

        chain = fallback_chains.get(role, [])
        for field_name in chain:
            cfg = self._get_model_config(field_name)
            if cfg and cfg.model_name:
                print(
                    f"[LLM] role={role} resolved to {field_name} ({cfg.provider}/{cfg.model_name})"
                )
                return cfg

        print(
            f"[LLM] role={role} fallback to primary ({primary.provider}/{primary.model_name})"
        )
        return primary

    def _create_adapter(self, config: ModelConfig) -> BaseLLMAdapter:
        """根据配置创建 LLM adapter（不缓存，每次新建）"""
        return LLMAdapterFactory.create(config)

    # ---- 角色方法 ----

    async def chat_as_router(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """路由角色: 决定任务分发给哪个模型处理"""
        cfg = self._resolve_role_model_config("router")
        adapter = self._create_adapter(cfg)
        return await adapter.chat(messages, temperature, max_tokens)

    async def chat_as_planner(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """规划角色: 制定执行计划和任务拆解"""
        cfg = self._resolve_role_model_config("planner")
        adapter = self._create_adapter(cfg)
        return await adapter.chat(messages, temperature, max_tokens)

    async def chat_as_analyst(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """分析角色: 分析执行结果，生成结构化报告"""
        cfg = self._resolve_role_model_config("analyst")
        adapter = self._create_adapter(cfg)
        return await adapter.chat(messages, temperature, max_tokens)

    async def chat_as_judge(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """评判角色: 评估风险、决策和推荐"""
        cfg = self._resolve_role_model_config("judge")
        adapter = self._create_adapter(cfg)
        return await adapter.chat(messages, temperature, max_tokens)

    # ---- 兼容方法 ----

    async def planner_chat(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """兼容方法，等同于 chat_as_planner"""
        return await self.chat_as_planner(messages, temperature, max_tokens)

    async def executor_chat(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """执行角色: 执行具体命令和工具调用"""
        cfg = self._resolve_role_model_config("executor")
        adapter = self._create_adapter(cfg)
        return await adapter.chat(messages, temperature, max_tokens)

    async def summarizer_chat(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """总结角色: 汇总结果生成摘要"""
        cfg = self._resolve_role_model_config("summarizer")
        adapter = self._create_adapter(cfg)
        return await adapter.chat(messages, temperature, max_tokens)

    async def chat_with_role(
        self,
        role: str,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """通用角色方法，通过名字路由"""
        cfg = self._resolve_role_model_config(role)
        adapter = self._create_adapter(cfg)
        return await adapter.chat(messages, temperature, max_tokens)

    async def chat(
        self,
        messages: List[Message],
        provider: Optional[ModelProvider] = None,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """直接指定 provider/model 的通用 chat，不走角色模型解析"""
        primary = self._resolve_primary_model_config()
        if provider is None:
            provider = primary.provider
        if model_name is None:
            model_name = primary.model_name

        config = ModelConfig(
            provider=provider,
            model_name=model_name,
            api_key=primary.api_key,
            base_url=primary.base_url,
            temperature=temperature or primary.temperature,
            max_tokens=max_tokens or primary.max_tokens,
            timeout=primary.timeout,
        )
        adapter = self._create_adapter(config)
        return await adapter.chat(messages, temperature, max_tokens)
