"""GET /models — الموديلات المجانية المتاحة دلوقتي من OpenRouter (PRD 10.4)."""

import logging

import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.llm.openrouter_client import list_free_models

logger = logging.getLogger(__name__)

router = APIRouter(tags=["models"])


class FreeModel(BaseModel):
    id: str
    name: str
    context_length: int | None


async def fetch_free_models_or_502() -> list[dict]:
    """
    list_free_models() بس فشل OpenRouter بيتحوّل لـ502 برسالة واضحة.

    مستخدمة هنا وفي /chat (للتأكد إن الموديل المطلوب مجاني).
    """
    try:
        return await list_free_models()
    # ValueError/KeyError: رد 200 بس JSON بايظ أو ناقص fields — برضه فشل من OpenRouter مش من عندنا.
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        logger.warning("OpenRouter /models failed: %r", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="مش قادرين نجيب قائمة الموديلات من OpenRouter دلوقتي — جرّب تاني بعد شوية.",
        ) from exc


@router.get("/models", response_model=list[FreeModel])
async def get_free_models() -> list[dict]:
    """قائمة الموديلات المجانية (id, name, context_length)."""
    return await fetch_free_models_or_502()
