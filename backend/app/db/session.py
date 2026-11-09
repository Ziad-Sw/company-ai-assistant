"""
اتصال SQLAlchemy مباشر بـPostgres بتاع Supabase (driver: psycopg 3).

ليه مش الـsupabase client؟ الـREST API (PostgREST) مايقدرش يعمل query
بـpgvector operators زي `<=>` من غير RPC function في الداتابيز، فالـretrieval
محتاج اتصال SQL مباشر.

محتاج DATABASE_URL في الـ.env — الـconnection string من Supabase Dashboard
→ Connect → "Session pooler" (بيشتغل على IPv4، عكس الـdirect connection).

⚠️ الـconnection string ده بيدخل بيوزر `postgres` اللي بيتخطى الـRLS، زي
الـservice_role key بالظبط — يفضل في الـbackend بس، ومايترفعش على GitHub أبداً.
"""

import os
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker


@lru_cache
def get_engine() -> Engine:
    """يرجّع engine واحد مشترك (lazy) — مش بيتعمل غير أول مرة حد يطلبه."""
    raw_url = os.environ.get("DATABASE_URL")
    if not raw_url:
        raise RuntimeError("DATABASE_URL مش موجود في الـ.env — راجع .env.example")

    # Supabase بيدّي الـURL بصيغة postgresql:// — بنثبّت الـdriver على psycopg 3
    # بدل ما SQLAlchemy يدوّر على psycopg2 (مش متسطب).
    url = make_url(raw_url).set(drivername="postgresql+psycopg")
    return create_engine(
        url,
        # مشروع Supabase الـfree بيتعمله pause، والـpooler بيقفل الاتصالات الخاملة —
        # pre_ping بيكتشف الاتصال الميت قبل ما الـquery يقع.
        pool_pre_ping=True,
        connect_args={
            "sslmode": "require",
            # الـtransaction pooler (port 6543) مابيدعمش prepared statements،
            # وpsycopg 3 بيعملها تلقائي بعد 5 تنفيذات — بنقفلها عشان الاتصال
            # يشتغل صح على أي نوع pooler.
            "prepare_threshold": None,
        },
    )


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    """يرجّع الـsessionmaker المربوط بالـengine المشترك."""
    return sessionmaker(bind=get_engine(), expire_on_commit=False)
