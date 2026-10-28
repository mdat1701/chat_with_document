"""Router gốc, gắn vào `app` với tiền tố `/api/v1` (T-008 §3).

Mỗi task Sprint 1+ thêm router con của mình vào đây (T-101: auth,
T-105: config, T-108: documents, T-304: conversations, ...) — không
tạo thêm tiền tố song song khác `/api/v1`.
"""

from fastapi import APIRouter

from app.api.routers.config import router as config_router
from app.api.routers.conversations import router as conversations_router
from app.api.routers.documents import router as documents_router
from app.api.routers.events import router as events_router
from app.api.routers.me import router as me_router

api_router = APIRouter()

api_router.include_router(me_router)
api_router.include_router(config_router)
api_router.include_router(documents_router)
api_router.include_router(conversations_router)
api_router.include_router(events_router)

# Ví dụ khi T-101/T-105/T-108 hoàn thành:
#   from app.api.routers.auth import router as auth_router
#   api_router.include_router(auth_router)
