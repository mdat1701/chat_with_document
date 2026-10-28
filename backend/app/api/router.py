"""Router gốc, gắn vào `app` với tiền tố `/api/v1` (T-008 §3).

Mỗi task Sprint 1+ thêm router con của mình vào đây (T-101: auth,
T-105: config, T-108: documents, T-304: conversations, ...) — không
tạo thêm tiền tố song song khác `/api/v1`.
"""

from fastapi import APIRouter

api_router = APIRouter()

# Ví dụ khi T-101/T-105/T-108 hoàn thành:
#   from app.api.routers.auth import router as auth_router
#   api_router.include_router(auth_router)
