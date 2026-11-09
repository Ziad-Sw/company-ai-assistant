"""
تحويل النص لـvectors باستخدام Gemini embedding API.

مهم: فيه نوعين من الـembedding مختلفين (asymmetric retrieval):
  - RETRIEVAL_DOCUMENT: لما نخزّن chunks في الداتابيز (ingestion)
  - RETRIEVAL_QUERY: لما نحوّل سؤال الموظف وقت البحث

استخدام النوع الغلط بيقلل دقة البحث، فحرص نستخدم الدالة الصح
في كل حالة (embed_document للتخزين، embed_query للبحث).

الأبعاد: مستخدمين 768 (بدل الـdefault 3072) عشان التخزين والبحث
أسرع وأرخص، وده كفاية لحجم knowledge base صغير زي مشروعنا.
محتاج GEMINI_API_KEY في الـ.env.
"""

import os

from google import genai
from google.genai import types

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIM = 768

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY مش موجود في الـ.env — راجع Tech-Stack.md قسم Environment & Secrets"
            )
        _client = genai.Client(api_key=api_key)
    return _client


def _embed(text: str, task_type: str) -> list[float]:
    client = _get_client()
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(
            task_type=task_type,
            output_dimensionality=EMBEDDING_DIM,
        ),
    )
    return result.embeddings[0].values


def embed_document(text: str) -> list[float]:
    """يُستخدم وقت تخزين chunk جديد في الداتابيز."""
    return _embed(text, task_type="RETRIEVAL_DOCUMENT")


def embed_query(text: str) -> list[float]:
    """يُستخدم وقت تحويل سؤال الموظف للبحث."""
    return _embed(text, task_type="RETRIEVAL_QUERY")
