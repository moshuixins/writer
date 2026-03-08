from __future__ import annotations

import time
from collections import defaultdict
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import accounts, auth, chat, documents, materials, preferences
from app.bootstrap import ensure_runtime_ready
from app.config import get_settings
from app.errors import AppError, logger, setup_logging
from app.services.background_executor import shutdown_background_executors
from app.services.book_import_dispatcher import book_import_dispatcher

setup_logging()
settings = get_settings()
cors_origins = [o.strip() for o in settings.cors_origins.split(',') if o.strip()]
_rate_buckets: dict[str, list[float]] = defaultdict(list)
_rate_limit = settings.rate_limit_per_minute


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_runtime_ready()
    book_import_dispatcher.resume_recoverable_tasks()
    try:
        yield
    finally:
        book_import_dispatcher.shutdown(wait=False, cancel_futures=True)
        shutdown_background_executors(wait=False, cancel_futures=True)
        await chat.ctx_bridge.close()
        await materials.ctx_bridge.close()


def create_app() -> FastAPI:
    app = FastAPI(title='公文写作系统', version='1.0.0', lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=['GET', 'POST', 'PUT', 'DELETE'],
        allow_headers=['Authorization', 'Content-Type'],
    )

    @app.middleware('http')
    async def rate_limit_middleware(request: Request, call_next):
        if request.url.path in ('/api/health',):
            return await call_next(request)

        client_ip = request.client.host if request.client else 'unknown'
        now = time.time()
        bucket = _rate_buckets[client_ip]

        _rate_buckets[client_ip] = [t for t in bucket if now - t < 60]
        bucket = _rate_buckets[client_ip]

        if len(bucket) >= _rate_limit:
            return JSONResponse(
                status_code=429,
                content={'error': '请求过于频繁，请稍后再试'},
            )

        bucket.append(now)
        return await call_next(request)

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        error_id = exc.error_id or uuid4().hex[:12]
        logger.warning(
            'AppError id=%s path=%s status=%s err=%s detail=%s',
            error_id,
            request.url.path,
            exc.status_code,
            exc.message,
            exc.detail,
        )
        content = {'error': exc.message}
        if exc.status_code >= 500:
            content['error_id'] = error_id
        return JSONResponse(status_code=exc.status_code, content=content)

    @app.exception_handler(Exception)
    async def global_error_handler(request: Request, exc: Exception):
        error_id = uuid4().hex[:12]
        logger.exception('Unhandled error id=%s path=%s err=%s', error_id, request.url.path, exc)
        return JSONResponse(
            status_code=500,
            content={'error': '服务器内部错误', 'error_id': error_id},
        )

    app.include_router(auth.router, prefix='/api/auth', tags=['用户认证'])
    app.include_router(accounts.router, prefix='/api/accounts', tags=['账户管理'])
    app.include_router(materials.router, prefix='/api/materials', tags=['素材管理'])
    app.include_router(chat.router, prefix='/api/chat', tags=['写作会话'])
    app.include_router(documents.router, prefix='/api/documents', tags=['文档管理'])
    app.include_router(preferences.router, prefix='/api/preferences', tags=['用户偏好'])

    @app.get('/api/health')
    def health_check():
        return {'status': 'ok', 'service': '公文写作系统'}

    return app


app = create_app()
