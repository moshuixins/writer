from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.database import engine, Base
from app.api import materials, chat, documents, preferences, auth
from app.errors import AppError, setup_logging, logger
from app.config import get_settings
import time
from collections import defaultdict

# 初始化日志
setup_logging()

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="公文写作助手", version="1.0.0")

settings = get_settings()
cors_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# ---------- 请求频率限制 ----------
_rate_buckets: dict[str, list[float]] = defaultdict(list)
_rate_limit = settings.rate_limit_per_minute


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # 健康检查和静态资源不限流
    if request.url.path in ("/api/health",):
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    bucket = _rate_buckets[client_ip]

    # 清理超过 60 秒的记录
    _rate_buckets[client_ip] = [t for t in bucket if now - t < 60]
    bucket = _rate_buckets[client_ip]

    if len(bucket) >= _rate_limit:
        return JSONResponse(
            status_code=429,
            content={"error": "请求过于频繁，请稍后再试"},
        )

    bucket.append(now)
    return await call_next(request)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    logger.warning("AppError: %s | detail: %s | path: %s", exc.message, exc.detail, request.url.path)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "detail": exc.detail},
    )


@app.exception_handler(Exception)
async def global_error_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"error": "服务器内部错误", "detail": str(exc)},
    )


app.include_router(auth.router, prefix="/api/auth", tags=["用户认证"])
app.include_router(materials.router, prefix="/api/materials", tags=["素材管理"])
app.include_router(chat.router, prefix="/api/chat", tags=["写作对话"])
app.include_router(documents.router, prefix="/api/documents", tags=["文档管理"])
app.include_router(preferences.router, prefix="/api/preferences", tags=["用户偏好"])


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "公文写作助手"}
