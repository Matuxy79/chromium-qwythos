"""Mock OpenAI-compatible streaming upstream.

Stands in for OpenRouter / HF Inference / RunPod, but with ZERO inference
latency. That is deliberate: real inference takes 0.5-30s, which would swamp
the 1-5ms of proxy overhead we're trying to measure and make every proxy look
identical. Removing it isolates -- and maximally amplifies -- the only thing a
Rust rewrite could actually improve.

Bare ASGI (no FastAPI routing) so the fixture itself is as cheap as possible.
The benchmark also measures client->here directly as a control, so any residual
fixture cost cancels out of the proxy-overhead delta.
"""

import json
import os

CHUNKS = int(os.getenv('MOCK_CHUNKS', '200'))

# Pre-serialise every byte at import time: no per-request or per-chunk work.
_TOKEN_CHUNKS = [
    b'data: '
    + json.dumps(
        {
            'id': 'chatcmpl-bench',
            'object': 'chat.completion.chunk',
            'created': 1700000000,
            'model': 'bench-model',
            'choices': [{'index': 0, 'delta': {'content': f' token{i}'}, 'finish_reason': None}],
        }
    ).encode()
    + b'\n\n'
    for i in range(CHUNKS)
]
_FINAL_CHUNK = (
    b'data: '
    + json.dumps(
        {
            'id': 'chatcmpl-bench',
            'object': 'chat.completion.chunk',
            'created': 1700000000,
            'model': 'bench-model',
            'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}],
        }
    ).encode()
    + b'\n\ndata: [DONE]\n\n'
)
_ALL_CHUNKS = _TOKEN_CHUNKS + [_FINAL_CHUNK]

_HEADERS = [
    (b'content-type', b'text/event-stream'),
    (b'cache-control', b'no-cache'),
]


async def app(scope, receive, send):
    if scope['type'] != 'http':
        return

    # Drain the request body (the proxy forwards a real JSON payload).
    while True:
        message = await receive()
        if message['type'] != 'http.request':
            break
        if not message.get('more_body', False):
            break

    await send({'type': 'http.response.start', 'status': 200, 'headers': _HEADERS})
    for chunk in _ALL_CHUNKS:
        await send({'type': 'http.response.body', 'body': chunk, 'more_body': True})
    await send({'type': 'http.response.body', 'body': b'', 'more_body': False})
