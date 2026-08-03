"""Load driver: measures time-to-first-token and full-stream latency.

Same driver against all three targets, so any driver overhead is systematic and
cancels out of the comparisons. The DIRECT target (client -> mock, no proxy) is
the control: proxy overhead is (proxy result - direct result), which also
cancels out the mock's own cost.

Usage:
  python bench.py --url http://127.0.0.1:9100/v1/chat/completions --label direct
  python bench.py --url http://127.0.0.1:9101/v1/chat/completions --label python --pid 1234
"""

import argparse
import asyncio
import json
import statistics
import time

import aiohttp

PAYLOAD = {
    'model': 'bench-model',
    'stream': True,
    'messages': [{'role': 'user', 'content': 'Benchmark request. Please stream a response.'}],
}


async def one_request(session: aiohttp.ClientSession, url: str) -> tuple[float, float, int]:
    """Return (ttft_ms, total_ms, bytes_received)."""
    start = time.perf_counter()
    ttft = None
    total_bytes = 0

    async with session.post(url, json=PAYLOAD) as r:
        async for chunk in r.content.iter_any():
            if ttft is None:
                ttft = (time.perf_counter() - start) * 1000
            total_bytes += len(chunk)

    total = (time.perf_counter() - start) * 1000
    return (ttft if ttft is not None else total, total, total_bytes)


async def run_phase(url: str, requests: int, concurrency: int) -> list[tuple[float, float, int]]:
    results: list[tuple[float, float, int]] = []
    sem = asyncio.Semaphore(concurrency)

    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=300),
        connector=aiohttp.TCPConnector(limit=0),
    ) as session:

        async def worker() -> None:
            async with sem:
                results.append(await one_request(session, url))

        await asyncio.gather(*[worker() for _ in range(requests)])

    return results


def pct(values: list[float], p: float) -> float:
    ordered = sorted(values)
    idx = min(int(len(ordered) * p / 100), len(ordered) - 1)
    return ordered[idx]


def tree_rss_mb(pid: int) -> float | None:
    """RSS of the whole process tree.

    `python -m uvicorn` forks a supervisor + worker, so measuring only the
    parent PID undercounts the server by an order of magnitude.
    """
    try:
        import psutil

        proc = psutil.Process(pid)
        total = proc.memory_info().rss
        for child in proc.children(recursive=True):
            try:
                total += child.memory_info().rss
            except Exception:
                pass
        return total / 1024 / 1024
    except Exception:
        return None


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--url', required=True)
    ap.add_argument('--label', required=True)
    ap.add_argument('--requests', type=int, default=500)
    ap.add_argument('--concurrency', type=int, default=32)
    ap.add_argument('--warmup', type=int, default=50)
    ap.add_argument('--pid', type=int, default=None, help='sample RSS of this process')
    args = ap.parse_args()

    rss_before = tree_rss_mb(args.pid) if args.pid else None

    # Warmup: let JIT/connection pools/allocators settle before measuring.
    await run_phase(args.url, args.warmup, args.concurrency)

    wall_start = time.perf_counter()
    results = await run_phase(args.url, args.requests, args.concurrency)
    wall = time.perf_counter() - wall_start

    rss_after = tree_rss_mb(args.pid) if args.pid else None

    ttfts = [r[0] for r in results]
    totals = [r[1] for r in results]

    report = {
        'label': args.label,
        'requests': args.requests,
        'concurrency': args.concurrency,
        'throughput_rps': round(args.requests / wall, 1),
        'ttft_ms': {
            'p50': round(pct(ttfts, 50), 3),
            'p95': round(pct(ttfts, 95), 3),
            'p99': round(pct(ttfts, 99), 3),
            'mean': round(statistics.mean(ttfts), 3),
        },
        'total_ms': {
            'p50': round(pct(totals, 50), 3),
            'p95': round(pct(totals, 95), 3),
            'mean': round(statistics.mean(totals), 3),
        },
        'bytes_per_response': results[0][2],
        'rss_mb_idle': round(rss_before, 1) if rss_before else None,
        'rss_mb_loaded': round(rss_after, 1) if rss_after else None,
    }

    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
