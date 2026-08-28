"""Multi-provider LLM routing: Claude primary, OpenAI fallback.

The rest of the codebase never imports a provider SDK directly — it asks
this module for a chat model. Swapping or adding providers is one change,
here.
"""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel

from . import config


def get_chat_model(temperature: float = 0.0) -> BaseChatModel:
    providers: list[BaseChatModel] = []

    if config.ANTHROPIC_API_KEY:
        from langchain_anthropic import ChatAnthropic

        providers.append(
            ChatAnthropic(
                model=config.ANTHROPIC_MODEL,
                temperature=temperature,
                max_tokens=2048,
                timeout=60,
                max_retries=2,
            )
        )

    if config.OPENAI_API_KEY:
        from langchain_openai import ChatOpenAI

        providers.append(
            ChatOpenAI(
                model=config.OPENAI_MODEL,
                temperature=temperature,
                timeout=60,
                max_retries=2,
            )
        )

    if not providers:
        raise RuntimeError(
            "No LLM provider configured. Set ANTHROPIC_API_KEY (and/or "
            "OPENAI_API_KEY) in backend/.env"
        )

    primary = providers[0]
    if len(providers) > 1:
        return primary.with_fallbacks(providers[1:])
    return primary


def provider_label() -> str:
    if config.ANTHROPIC_API_KEY:
        return f"anthropic:{config.ANTHROPIC_MODEL}"
    if config.OPENAI_API_KEY:
        return f"openai:{config.OPENAI_MODEL}"
    return "none"
