"""Orchestrates the full three-way benchmark and prints a comparison table.

Run from the repo root with the project venv active:
    python bench/run_bench.py
"""

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

BENCH_DIR = Path(__file__).resolve().parent
REPO_ROOT = BENCH_DIR.parent
VENV_PY = REPO_ROOT / '.venv' / 'Scripts' / 'python.exe'
PYTHON = str(VENV_PY) if VENV_PY.exists() else sys.executable

MOCK_PORT = 9100
PY_PORT = 9101
RS_PORT = 9102

REQUESTS = int(os.getenv('BENCH_REQUESTS', '500'))
CONCURRENCY = int(os.getenv('BENCH_CONCURRENCY', '32'))


def wait_for_port(port: int, timeout: float = 60) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=1):
                return True
        except OSError:
            time.sleep(0.25)
    return False


def start(cmd: list[str], cwd: Path, port: int, name: str) -> subprocess.Popen:
    print(f'  starting {name} on :{port} ...', flush=True)
    proc = subprocess.Popen(cmd, cwd=str(cwd), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not wait_for_port(port):
        proc.terminate()
        raise RuntimeError(f'{name} failed to bind :{port}')
    time.sleep(0.5)  # let the event loop settle
    return proc


def stop(proc: subprocess.Popen) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


def run_bench(url: str, label: str, pid: int | None) -> dict:
    cmd = [
        PYTHON, str(BENCH_DIR / 'bench.py'),
        '--url', url,
        '--label', label,
        '--requests', str(REQUESTS),
        '--concurrency', str(CONCURRENCY),
    ]
    if pid:
        cmd += ['--pid', str(pid)]
    out = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))
    if out.returncode != 0:
        raise RuntimeError(f'bench failed for {label}:\n{out.stderr}')
    return json.loads(out.stdout)


def main() -> None:
    results = {}
    mock = None
    print(f'Config: {REQUESTS} requests @ concurrency {CONCURRENCY}\n')

    try:
        mock = start(
            [PYTHON, '-m', 'uvicorn', 'mock_upstream:app',
             '--host', '127.0.0.1', '--port', str(MOCK_PORT), '--log-level', 'warning'],
            BENCH_DIR, MOCK_PORT, 'mock upstream',
        )

        # Control: no proxy in the path at all. This is the floor.
        print('  [1/3] direct -> mock (control)', flush=True)
        results['direct'] = run_bench(f'http://127.0.0.1:{MOCK_PORT}/v1/chat/completions', 'direct', None)

        print('  [2/3] python proxy (FastAPI + aiohttp)', flush=True)
        py = start(
            [PYTHON, '-m', 'uvicorn', 'py_proxy:app',
             '--host', '127.0.0.1', '--port', str(PY_PORT), '--log-level', 'warning'],
            BENCH_DIR, PY_PORT, 'python proxy',
        )
        try:
            results['python'] = run_bench(f'http://127.0.0.1:{PY_PORT}/v1/chat/completions', 'python', py.pid)
        finally:
            stop(py)

        rs_bin = BENCH_DIR / 'rs_proxy' / 'target' / 'release' / 'rs_proxy.exe'
        if rs_bin.exists():
            print('  [3/3] rust proxy (Axum + reqwest)', flush=True)
            rs = start([str(rs_bin)], BENCH_DIR, RS_PORT, 'rust proxy')
            try:
                results['rust'] = run_bench(f'http://127.0.0.1:{RS_PORT}/v1/chat/completions', 'rust', rs.pid)
            finally:
                stop(rs)
        else:
            print(f'  [3/3] SKIPPED - {rs_bin} not built', flush=True)
    finally:
        if mock:
            stop(mock)

    print('\n' + '=' * 78)
    print(f'{"target":<10} {"req/s":>9} {"TTFT p50":>10} {"TTFT p95":>10} {"TTFT p99":>10} {"RSS MB":>9}')
    print('-' * 78)
    for label in ('direct', 'python', 'rust'):
        r = results.get(label)
        if not r:
            continue
        rss = r.get('rss_mb_loaded')
        print(
            f'{label:<10} {r["throughput_rps"]:>9} '
            f'{r["ttft_ms"]["p50"]:>10} {r["ttft_ms"]["p95"]:>10} {r["ttft_ms"]["p99"]:>10} '
            f'{(rss if rss else "-"):>9}'
        )
    print('=' * 78)

    # The number that actually answers the question: overhead ADDED by each proxy.
    base = results['direct']['ttft_ms']['p50']
    print('\nProxy overhead added vs. direct (TTFT p50):')
    for label in ('python', 'rust'):
        if label in results:
            print(f'  {label:<8} +{results[label]["ttft_ms"]["p50"] - base:.3f} ms')

    (BENCH_DIR / 'results.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    print(f'\nRaw results -> {BENCH_DIR / "results.json"}')


if __name__ == '__main__':
    main()
