"""
Wrapper رفيع حوالين OpenRouter (Tech-Stack.md قسم 4 — الموديلات المجانية بس).

- قائمة الموديلات: httpx مباشرة على /models (metadata endpoint، مش محتاج الـSDK).
- المحادثة: openai SDK (OpenAI-compatible) على نفس الـbase URL بـOPENROUTER_API_KEY.
"""

import time
from collections.abc import AsyncGenerator
from functools import lru_cache

import httpx
from openai import AsyncOpenAI

from app.core.config import get_settings

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
_MODELS_TIMEOUT_SECONDS = 15
_MODELS_CACHE_TTL_SECONDS = 300
_models_cache: tuple[float, list[dict]] | None = None
# سقف لطول الرد: موديل مجاني داخل في loop مايفضلش ماسك الـconnection والـworker من غير نهاية.
# عالي بما يكفي لموديلات الـreasoning (الـreasoning tokens بتتحسب من نفس الحد).
_MAX_OUTPUT_TOKENS = 2048
# رد الـcategory decision قصير (token واحد)، بس الـreasoning بتاع الموديلات
# المجانية بيتحسب من نفس الحد — 512 كانت بتتنافس والـcontent بييجي فاضي مع
# finish_reason=stop (اتقاست فعلياً على nemotron في اختبارات الـrouting)،
# فالحد بقى بنفس سقف الرد العادي.
_DECISION_MAX_TOKENS = 2048


@lru_cache
def _get_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=get_settings().openrouter_api_key.get_secret_value(),
    )


async def list_free_models(force_refresh: bool = False) -> list[dict]:
    """
    يرجّع الموديلات المجانية النصية من OpenRouter: [{"id", "name", "context_length"}].

    النتيجة متخزنة in-memory بـTTL خمس دقايق — /chat بيحقق منها في كل request،
    والـcache بيمنع إن كل رسالة تصرف request لـOpenRouter. `force_refresh=True`
    بيتخطّى الـcache لو محتاجين قائمة حديثة.

    Raises:
        httpx.HTTPError: OpenRouter مش متاح أو رجّع status غلط.
        ValueError, KeyError: OpenRouter رجّع 200 بس بشكل مش متوقع.
    """
    global _models_cache
    now = time.monotonic()
    if (
        not force_refresh
        and _models_cache is not None
        and now - _models_cache[0] < _MODELS_CACHE_TTL_SECONDS
    ):
        return list(_models_cache[1])
    async with httpx.AsyncClient(timeout=_MODELS_TIMEOUT_SECONDS) as client:
        response = await client.get(f"{OPENROUTER_BASE_URL}/models")
        response.raise_for_status()
    models = [
        {"id": model["id"], "name": model["name"], "context_length": model["context_length"]}
        for model in response.json()["data"]
        if _is_free(model["pricing"]) and _is_text_chat(model.get("architecture") or {})
    ]
    _models_cache = (now, models)
    return list(models)


def _is_free(pricing: dict) -> bool:
    # الـrouters (openrouter/auto وغيره) سعرها "-1" = متغير، مش مجاني.
    # "overrides" فيها أسعار tiered للـprompts الطويلة، فموديل عنده overrides
    # ممكن يتحاسب فوق عدد tokens معين حتى لو السعر الأساسي صفر.
    if pricing.get("overrides"):
        return False
    return all(float(price) == 0 for key, price in pricing.items() if key != "overrides")


def _is_text_chat(architecture: dict) -> bool:
    # موديلات النص بس: الـoutput لازم يكون نصي بالكامل (بيستبعد موديلات الـaudio
    # زي Lyria)، والـinput لازم يقبل text (موديلات الـvision النصية عادية —
    # إحنا بنبعت text بس).
    inputs = architecture.get("input_modalities") or []
    outputs = architecture.get("output_modalities") or []
    return "text" in inputs and outputs == ["text"]


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


async def complete_chat(model: str, messages: list[dict]) -> str:
    """
    رد كامل من غير streaming — لنداءات الـagent القصيرة زي تحديد الـcategory
    (الـwrapper التاني فوق streaming-only، وده مش بديل له).

    فيه محاولة واحدة إضافية لو الرد فاضي: موديلات مجانية بترجع ساعات content
    فاضي ومعاه reasoning كامل وfinish_reason=stop (مشكلة موثّقة من اختبارات
    Phase 1) — إعادة المحاولة الواحدة بتقلل تذبذب قرار التوجيه من غير loop
    مفتوح، وبعد كده الـcaller بيعمل fallback الآمن بتاعه.

    Raises:
        openai.APIError: أي فشل من OpenRouter (rate limit، موديل مش موجود، network).
    """
    for _ in range(2):
        response = await _get_client().chat.completions.create(
            model=model, messages=messages, max_tokens=_DECISION_MAX_TOKENS
        )
        if response.choices and response.choices[0].message.content:
            return response.choices[0].message.content
    return ""
