# Spike results: Rust vs Python for the gateway hot path

Measured on this machine, Windows 11, Rust 1.97.1 / Python 3.12.10.
Method and deliberate pro-Rust biases: see [README.md](README.md).

## Serial (concurrency=1) — isolates true per-request cost

| target | TTFT p50 | **overhead added** | full-stream p50 | req/s | RSS |
|---|---|---|---|---|---|
| direct (control) | 0.783 ms | — | 0.79 ms | 1146 | — |
| **python** (FastAPI+aiohttp) | 1.029 ms | **+0.246 ms** | 1.18 ms | 810 | 63.6 MB |
| **rust** (Axum+reqwest, multi-thread) | 0.880 ms | **+0.097 ms** | 3.09 ms | 222 | 6.3 MB |
| rust (single-thread runtime) | 0.780 ms | ~0 ms | 2.66 ms | 355 | ~6 MB |

Across four runs Python's overhead ranged **+0.246 to +0.535 ms**, Rust's
**+0.097 to +0.162 ms**. So Rust's real advantage is roughly **0.15–0.35 ms
per request**.

## Concurrent (concurrency=32)

| target | TTFT p50 | overhead | req/s | RSS |
|---|---|---|---|---|
| direct | 10.26 ms | — | 2275 | — |
| python | 25.80 ms | +15.54 ms | 1167 | 72.9 MB |
| rust | 24.16 ms | +13.90 ms | 929 | 11.3 MB |

At saturation both are dominated by queueing, and Rust's TTFT edge shrinks to
~1.6 ms while its throughput is *lower*.

## Findings

**1. Rust wins time-to-first-token — by ~0.15–0.35 ms.**
Real, reproducible, and irrelevant in context. A streaming call to
OpenRouter/HF/RunPod has a TTFT of roughly 300–2000 ms. Saving 0.25 ms is
**under 0.1% of user-perceived latency.** You could not detect it in the UI.

**2. Rust wins memory decisively — ~10× (6 MB vs 64 MB).**
This is the one genuinely material result. It matters for cheap Railway
instances and dense multi-tenancy. It does not matter for a solo-dev deployment.

**3. The naive Rust port is *slower* at completing streams — 2.3–3.6×.**
Python: 810 req/s. Rust: 222 req/s (multi-thread), 355 req/s (single-thread).
I made three good-faith attempts to close this, having explicitly rigged the
benchmark for Rust:
- fat LTO, `opt-level=3`, `codegen-units=1`, `panic=abort` — baseline
- coalescing ready chunks to match aiohttp's `iter_any()` — **no effect**
- single-thread Tokio runtime (matching asyncio) — **+54%, still 2.3× behind**

The remaining gap would take real profiling to find. **That is the finding.**
Switching languages does not hand you performance; it hands you a new,
untuned system. `aiohttp` and `uvicorn` are fast because people spent years
tuning them.

## Verdict

For this workload the rewrite buys **~0.25 ms per request and 58 MB of RAM**,
at a cost of porting ~109k LOC, reimplementing 55 migrations, 31 routers, 15
vector-DB backends and the OAuth/LDAP/SCIM auth surface — and permanently
losing the ability to rebase on upstream qwythos.

It is not a close call. The bottleneck is the inference API, and no amount of
gateway optimisation touches it.

### What the numbers *do* justify

- **Memory-bound deployment?** Cheaper wins first: `uvicorn --workers 1`,
  trimming unused vector-DB clients from `requirements.txt`, `PYTHONOPTIMIZE`.
- **Genuinely want Rust in the project?** Put it where it's bounded and pays:
  a Tauri desktop shell (~5 MB binary vs a ~500 MB Python venv). Same UI, no
  backend port.
- **Later, if profiling finds a real CPU hotspot** — document chunking,
  tokenisation, embedding math — that's the PyO3 seam your own notes describe:
  *"push the hot 5% down into Rust behind a Python interface… where measurement
  told you it should."* Measurement here says the hot 5% is not in the gateway.
