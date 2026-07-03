from app.core.config import settings
from app.core.llm.base import LLMProvider
from app.core.llm.openai import OpenAILLMProvider


def get_llm_provider() -> LLMProvider:
    if settings.llm_provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER is openai")
            
        return OpenAILLMProvider(
            api_key=settings.openai_api_key,
            model=settings.llm_model,
        )

    raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")
