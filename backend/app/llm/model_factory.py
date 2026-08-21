import os
from langchain_openai import ChatOpenAI
from ..config import AI_API_KEY, AI_BASE_URL, AI_MODEL, ai_is_configured


def get_chat_model(temperature: float = 0.0) -> ChatOpenAI:
    """Return an abstract LangChain Chat Model based on environment configurations.

    This returns a ChatOpenAI client, which is fully compatible with OpenAI,
    OpenRouter, Groq, or Ollama via VERICATALOG_AI_BASE_URL.
    """
    if not ai_is_configured():
        raise RuntimeError(
            "VeriCatalog LLM is not configured. "
            "Please configure VERICATALOG_AI_API_KEY, VERICATALOG_AI_BASE_URL, and VERICATALOG_AI_MODEL."
        )

    provider = os.getenv("VERICATALOG_AI_PROVIDER", "openai").lower()
    extra_headers = {}

    if provider == "openrouter":
        extra_headers = {
            "HTTP-Referer": "https://github.com/SoM1702/Vericatalogue",
            "X-Title": "VeriCatalog Workspace",
        }

    return ChatOpenAI(
        openai_api_key=AI_API_KEY,
        openai_api_base=AI_BASE_URL,
        model_name=AI_MODEL,
        temperature=temperature,
        default_headers=extra_headers if extra_headers else None,
    )
