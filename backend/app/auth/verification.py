"""
التحقق من الـJWT بتاع Supabase Auth — signature + expiry + aud + iss (مش decode بس).

القرار المعتمد (Tech-Stack.md قسم 6): بنجرّب **JWKS الأول** — بنجيب المفاتيح
العامة من `https://<project-ref>.supabase.co/auth/v1/.well-known/jwks.json`
وبنكاشهم (PyJWKClient بيكاش تلقائي) — ولو الـJWKS مش متاح بنرجع للتحقق بـ**HS256**
على `SUPABASE_JWT_SECRET`. الـtoken اللي فيه `aud != "authenticated"` ميرفض
في المسارين: PyJWT بيفشل فوراً على الـaudience.

ملاحظة أمان مهمة: الـfallback مش بيريّف أي token — الـHS256 verification بيفشل
على أي token مش موقّع فعلاً بالمفتاح السري المظبوط، فالـtoken المزوّر بيرفض
في المسارين برضه.

الـkeys بتتقري من الـenv مباشرة (lazy) زي app/db/supabase_client.py — مش من
config.py عشان يفضل نطاقه زي ما هو.
"""

import os
from functools import lru_cache

import jwt
from jwt import PyJWKClient, PyJWKClientError, PyJWTError

AUDIENCE = "authenticated"

ALGORITHMS_JWKS = ["RS256", "ES256"]  # مفاتيح Supabase غير المتماثلة في الـJWKS
ALGORITHMS_HS256 = ["HS256"]

_JWT_SECRET_ENV = "SUPABASE_JWT_SECRET"


def _supabase_url() -> str:
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    if not url:
        raise RuntimeError("SUPABASE_URL مش موجود في الـ.env — مطلوب للتحقق من الـJWT")
    return url


def _issuer() -> str:
    """Supabase بيكتب الـiss في الـtoken كـ '<SUPABASE_URL>/auth/v1'."""
    return f"{_supabase_url()}/auth/v1"


@lru_cache
def _jwks_client() -> PyJWKClient:
    # PyJWKClient بيكاش الـJWKS داخلياً (lru_cache) — النداءات المتتالية مش بتعمل HTTP request كل مرة.
    return PyJWKClient(f"{_supabase_url()}/auth/v1/.well-known/jwks.json")


def verify_supabase_jwt(token: str) -> dict:
    """
    يتحقق من الـtoken ويرجّع الـclaims الموقّعة.

    Raises:
        jwt.PyJWTError: الـtoken فاسد أو موقّع بمفتاح مش معروف أو منتهي
            أو الـaud/iss مش مظبوطين.
    """
    try:
        signing_key = _jwks_client().get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=ALGORITHMS_JWKS,
            audience=AUDIENCE,
            issuer=_issuer(),
        )
    except PyJWKClientError:
        # الـJWKS مش متاح (شبكة) أو الـtoken ملوش kid مطابق (مثلاً token قديم
        # موقّع بالـsecret المتماثل) — الـfallback بيفشل برضه لو الـtoken مش موقّع
        # بالمفتاح السري المظبوط، فمفيش أي مسار مفتوح للتزوير.
        secret = os.environ.get(_JWT_SECRET_ENV, "")
        if not secret:
            raise
        return jwt.decode(
            token,
            secret,
            algorithms=ALGORITHMS_HS256,
            audience=AUDIENCE,
            issuer=_issuer(),
        )
