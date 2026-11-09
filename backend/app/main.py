"""
FastAPI app — نقطة الدخول للـbackend.

التشغيل (من فولدر backend/، والـvenv مفعّلة):
    uvicorn app.main:app --reload
"""

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, conversations, models
from app.core.config import get_settings

# session.py وsupabase_client.py وembeddings.py بيقروا الـkeys من os.environ
# مباشرة (lazy، أول request)، فلازم الـ.env يتحمّل هنا. config.py بيقرا الـ.env لوحده.
load_dotenv()
# fail fast: من غير الـkey ده /chat كان هيقع جوه الـstream بعد ما الـ200 اتبعتت
# للـclient، فيوصله رد مقطوع من غير ولا error event.
get_settings()

FRONTEND_DEV_ORIGIN = "http://localhost:3000"

app = FastAPI(title="Company AI Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_DEV_ORIGIN],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
    # من غيرها الـbrowser مش هيسمح للـfrontend يقرا الـconversation_id بتاع المحادثة الجديدة.
    expose_headers=["X-Conversation-Id"],
)

app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(models.router)
