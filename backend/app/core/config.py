"""
إعدادات الـbackend من الـ.env بـpydantic-settings.

فيه بس الـkeys اللي مفيش موديول بيقراها لحد دلوقتي. الباقيين ليهم مكانهم فعلاً
وبيتقروا من os.environ (و main.py بيعمل load_dotenv() عشانهم):
  - DATABASE_URL → app/db/session.py
  - SUPABASE_URL, SUPABASE_SERVICE_KEY → app/db/supabase_client.py
  - GEMINI_API_KEY → app/rag/embeddings.py
تجميعهم كلهم هنا refactor منفصل (الملفات دي برا نطاق المهمة اللي اتعمل فيها الملف ده).
"""

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# مسار مطلق لـbackend/.env عشان القراية ماتعتمدش على الفولدر اللي uvicorn اتشغّل منه.
_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE, env_file_encoding="utf-8", extra="ignore"
    )

    # SecretStr: الـkey مايظهرش لو الـsettings اتطبعت أو اتسجلت في log بالغلط.
    # min_length=1: سطر "OPENROUTER_API_KEY=" فاضي في الـ.env يفشل هنا برسالة واضحة
    # بدل ما يعدي ويطلع بعدين كـ"Missing credentials" مضللة من الـopenai SDK.
    openrouter_api_key: Annotated[SecretStr, Field(min_length=1)]


@lru_cache
def get_settings() -> Settings:
    """الـsettings بتتقري مرة واحدة أول ما حد يحتاجها (مش وقت الـimport)."""
    return Settings()
