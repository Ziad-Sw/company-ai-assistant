"""
الاتصال بـSupabase من الـbackend.

⚠️ هنا بنستخدم الـ**service_role key**، مش الـanon key:
الـservice_role بيتخطى الـRow Level Security (RLS) تماماً، وده مطلوب
لسكريبتات زي الـingestion اللي محتاجة تكتب في الداتابيز بدون قيود دور معين.

الـfrontend وأي كود بيتعامل مباشرة مع طلبات الموظفين لازم يستخدم
الـanon key (أو JWT بتاع المستخدم)، عشان الـRLS تطبّق الصلاحيات صح.
الـservice_role key يفضل في الـbackend بس، ومايترفعش على GitHub أبداً.
"""

import os
from functools import lru_cache

from supabase import Client, create_client


@lru_cache
def get_supabase() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL أو SUPABASE_SERVICE_KEY مش موجودين في الـ.env"
        )
    return create_client(url, key)
