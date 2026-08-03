"""Python streaming-proxy slice: FastAPI + aiohttp.

Mirrors the pattern qwythos actually uses in
backend/qwythos/routers/openai.py -- a pooled aiohttp session forwarding to
the upstream, wrapped in a StreamingResponse. Kept minimal so we measure the
Python runtime + framework, not qwythos's auth/DB/middleware features (a
Rust rewrite would have to reimplement those and pay most of that cost too).

Run: uvicorn py_proxy:app --host 127.0.0.1 --port 9101 --log-level warning
"""

import os
from contextlib import asynccontextmanager

import aiohttp
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

UPSTREAM = os.getenv('BENCH_UPSTREAM', 'http://127.0.0.1:9100/v1/chat/completions')

_session: aiohttp.ClientSession | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _session
    # Pooled session, matching qwythos's utils/session_pool.py approach.
    _session = aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=300),
        connector=aiohttp.TCPConnector(limit=0),
    )
    yield
    await _session.close()


app = FastAPI(lifespan=lifespan)


@app.post('/v1/chat/completions')
async def chat_completions(request: Request):
    payload = await request.json()

    r = await _session.post(UPSTREAM, json=payload)

    async def stream():
        async for chunk in r.content.iter_any():
            yield chunk
        r.release()

    return StreamingResponse(
        stream(),
        status_code=r.status,
        media_type='text/event-stream',
    )


@app.get('/health')
async def health():
    return {'status': True}
