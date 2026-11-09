"""
Wrapper رفيع حوالين OpenRouter (Tech-Stack.md قسم 4 — الموديلات المجانية بس).

- قائمة الموديلات: httpx مباشرة على /models (metadata endpoint، مش محتاج الـSDK).
- المحادثة: openai SDK (OpenAI-compatible) على نفس الـbase URL بـOPENROUTER_API_KEY.
"""

from collections.abc import AsyncGenerator
from functools import lru_cache

import httpx
from openai import AsyncOpenAI

from app.core.config import get_settings

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
_MODELS_TIMEOUT_SECONDS = 15
# سقف لطول الرد: موديل مجاني داخل في loop مايفضلش ماسك الـconnection والـworker من غير نهاية.
# عالي بما يكفي لموديلات الـreasoning (الـreasoning tokens بتتحسب من نفس الحد).
_MAX_OUTPUT_TOKENS = 2048


@lru_cache
def _get_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=get_settings().openrouter_api_key.get_secret_value(),
    )


async def list_free_models() -> list[dict]:
    """
    يرجّع الموديلات المجانية من OpenRouter: [{"id", "name", "context_length"}].

    Raises:
        httpx.HTTPError: OpenRouter مش متاح أو رجّع status غلط.
        ValueError, KeyError: OpenRouter رجّع 200 بس بشكل مش متوقع.
    """
    async with httpx.AsyncClient(timeout=_MODELS_TIMEOUT_SECONDS) as client:
        response = await client.get(f"{OPENROUTER_BASE_URL}/models")
        response.raise_for_status()
    return [
        {"id": model["id"], "name": model["name"], "context_length": model["context_length"]}
        for model in response.json()["data"]
        if _is_free(model["pricing"])
    ]


def _is_free(pricing: dict) -> bool:
    # الـrouters (openrouter/auto وغيره) سعرها "-1" = متغير، مش مجاني.
    # "overrides" فيها أسعار tiered للـprompts الطويلة، فموديل عنده overrides
    # ممكن يتحاسب فوق عدد tokens معين حتى لو السعر الأساسي صفر.
    if pricing.get("overrides"):
        return False
    return all(float(price) == 0 for key, price in pricing.items() if key != "overrides")


async def stream_chat_completion(model: str, messages: list[dict]) -> AsyncGenerator[str, None]:
    """
    يبعت المحادثة لـOpenRouter بـstream=True ويرجّع النص قطعة قطعة أول ما توصل.

    Raises:
        openai.APIError: أي فشل من OpenRouter (rate limit، موديل مش موجود، network).
    """
    stream = await _get_client().chat.completions.create(
        model=model, messages=messages, stream=True, max_tokens=_MAX_OUTPUT_TOKENS
    )
    # async with: لو العميل قفل الاتصال في النص، الـstream لـOpenRouter يتقفل هو كمان.
    async with stream:
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
