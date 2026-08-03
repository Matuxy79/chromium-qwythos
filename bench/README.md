# Rust-vs-Python spike: does rewriting the backend buy anything?

A narrow, measured answer to "should the backend be rewritten in Rust?" before
committing person-years to porting ~109k LOC.

## The question this answers

This app is an **API gateway**. Its hot path is: accept a chat request → forward
it to OpenRouter/HF/RunPod → stream SSE tokens back. A Rust rewrite can only
improve the time *the gateway itself* spends. It cannot speed up remote
inference. So the question reduces to:

> How many milliseconds does the Python gateway add, and would Rust meaningfully
> reduce that number relative to inference latency?

## Method

Three configurations, one load driver, identical payloads:

| Target | Path | Purpose |
|---|---|---|
| `direct` | client → mock | **Control.** The floor. No proxy in the path. |
| `python` | client → FastAPI+aiohttp → mock | The current stack's pattern |
| `rust` | client → Axum+reqwest → mock | The proposed stack |

**Proxy overhead = (proxy result − direct result).** Subtracting the control
cancels out both the mock's cost and the driver's cost, leaving only what the
gateway layer adds.

### Deliberate biases — all favouring Rust

This benchmark is rigged *for* Rust, so that a null result is credible:

1. **Zero inference latency.** The mock returns pre-serialised bytes instantly.
   Real upstreams take 0.5–30 s, which would bury proxy overhead entirely. Removing
   it amplifies the only signal Rust could win on.
2. **Rust gets all cores; Python gets one.** `uvicorn` runs a single worker
   (asyncio is single-threaded); Tokio defaults to a multi-threaded runtime.
   Python's standard fix (`--workers N`) is *not* applied.
3. **Max optimisation for Rust only.** `opt-level=3`, fat LTO,
   `codegen-units=1`, `panic=abort`. Python gets no equivalent tuning.
4. **Python carries framework overhead Rust doesn't.** FastAPI does Pydantic-adjacent
   request handling and JSON parsing; the Axum slice passes bytes through.

If Rust's advantage is small *under these conditions*, it will be smaller still
in production.

### Known limits (stated, not hidden)

- The Python slice is minimal, so this measures **Python-the-runtime**, not
  qwythos's full auth/DB/middleware stack. That extra cost is *features* — a
  Rust rewrite would have to reimplement them and pay most of it too.
- Single machine, loopback networking. Real deployments add network latency that
  further dilutes any proxy-level difference.
- The driver is Python/aiohttp; its overhead is systematic and cancels in the deltas.

## Running it

```bash
python bench/run_bench.py
```

Tune with `BENCH_REQUESTS`, `BENCH_CONCURRENCY`, `MOCK_CHUNKS`.

## Files

- `mock_upstream.py` — zero-latency OpenAI-compatible SSE fixture
- `py_proxy.py` — FastAPI + aiohttp streaming passthrough
- `rs_proxy/` — Axum + reqwest streaming passthrough
- `bench.py` — load driver (TTFT p50/p95/p99, throughput, RSS)
- `run_bench.py` — orchestrator; writes `results.json`

## Interpreting the result

The decisive comparison is **proxy overhead vs. real inference latency**. A
typical OpenRouter streaming call has a time-to-first-token of roughly
300–2000 ms. If the Python gateway adds single-digit milliseconds, then even
reducing that to zero changes user-perceived latency by well under 1% — and the
rewrite cost is ~109k LOC plus permanent loss of upstream rebasing.
