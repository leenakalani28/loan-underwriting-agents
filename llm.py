"""One place that decides which LLM every agent uses.

Set LLM_PROVIDER in .env:
    groq       (default)  model from GROQ_MODEL (e.g. openai/gpt-oss-120b), key GROQ_API_KEY
    fireworks             model from FIREWORKS_MODEL (default accounts/fireworks/models/gpt-oss-120b),
                          key FIREWORKS_API_KEY
    cerebras              model from CEREBRAS_MODEL (default gpt-oss-120b), key CEREBRAS_API_KEY

All three host the same open-weight model, gpt-oss-120b; only the hosting company changes.
"""
import os

from dotenv import load_dotenv

load_dotenv()

# Providers that speak the OpenAI API format: (base URL, model setting, default model, key setting)
OPENAI_COMPATIBLE = {
    "fireworks": ("https://api.fireworks.ai/inference/v1", "FIREWORKS_MODEL",
                  "accounts/fireworks/models/gpt-oss-120b", "FIREWORKS_API_KEY"),
    "cerebras": ("https://api.cerebras.ai/v1", "CEREBRAS_MODEL", "gpt-oss-120b", "CEREBRAS_API_KEY"),
}


def get_llm():
    provider = os.getenv("LLM_PROVIDER", "groq").lower()

    if provider in OPENAI_COMPATIBLE:
        from langchain_openai import ChatOpenAI

        class OpenAICompatibleChat(ChatOpenAI):
            """Structured answers use tool calling, the same way the agents work on Groq."""
            def with_structured_output(self, schema, **kwargs):
                kwargs.setdefault("method", "function_calling")
                return super().with_structured_output(schema, **kwargs)

        base_url, model_setting, default_model, key_setting = OPENAI_COMPATIBLE[provider]
        return OpenAICompatibleChat(
            model=os.getenv(model_setting, default_model),
            api_key=os.getenv(key_setting),
            base_url=base_url,
            temperature=0,
            max_retries=6,  # waits and tries again if the provider is briefly busy or rate-limits
        )

    from langchain_groq import ChatGroq
    return ChatGroq(model=os.getenv("GROQ_MODEL"), temperature=0, max_retries=5)