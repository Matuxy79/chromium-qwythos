"""Native window app -- run with the venv's own pythonw.exe (via launcher.pyw),
where pywebview and all backend dependencies are guaranteed installed.

Starts (or attaches to an already-running) Qwythos server and shows it in a
native window instead of a browser tab. Only kills the server on window close
if this process is the one that started it.
"""

import hashlib
import inspect
import json
import os
import secrets
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import webview

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / 'backend'
DATA_DIR = BACKEND_DIR / 'data'
SECRET_KEY_FILE = BACKEND_DIR / '.webui_secret_key'
ICON_PATH = REPO_ROOT / 'static' / 'static' / 'qwythos.ico'
SERVER_LOG = DATA_DIR / 'desktop-server.log'
WEBVIEW_STORAGE = DATA_DIR / 'desktop-webview'
FRONTEND_BUILD_DIR = REPO_ROOT / 'build'
BUILD_INDEX = FRONTEND_BUILD_DIR / 'index.html'
BUILD_VERSION = FRONTEND_BUILD_DIR / '_app' / 'version.json'
BUILD_IMMUTABLE_DIR = FRONTEND_BUILD_DIR / '_app' / 'immutable'
BRAND_BUILD_FILES = (
    FRONTEND_BUILD_DIR / 'favicon.ico',
    FRONTEND_BUILD_DIR / 'favicon.png',
    FRONTEND_BUILD_DIR / 'manifest.json',
    FRONTEND_BUILD_DIR / 'static' / 'apple-touch-icon.png',
    FRONTEND_BUILD_DIR / 'static' / 'favicon.ico',
    FRONTEND_BUILD_DIR / 'static' / 'favicon.png',
    FRONTEND_BUILD_DIR / 'static' / 'favicon.svg',
    FRONTEND_BUILD_DIR / 'static' / 'favicon-96x96.png',
    FRONTEND_BUILD_DIR / 'static' / 'logo.png',
    FRONTEND_BUILD_DIR / 'static' / 'qwythos.ico',
    FRONTEND_BUILD_DIR / 'static' / 'site.webmanifest',
    FRONTEND_BUILD_DIR / 'static' / 'splash.png',
    FRONTEND_BUILD_DIR / 'static' / 'splash-dark.png',
    FRONTEND_BUILD_DIR / 'static' / 'web-app-manifest-192x192.png',
    FRONTEND_BUILD_DIR / 'static' / 'web-app-manifest-512x512.png',
)

HOST = '127.0.0.1'
PREFERRED_PORT = 8080
PORT_SCAN_LIMIT = 20

CREATE_NO_WINDOW = 0x08000000


def base_url(port: int) -> str:
    return f'http://{HOST}:{port}'


def get_frontend_build_identity() -> str:
    """Return a stable identity for the completed frontend build on disk."""
    required_paths = (BUILD_INDEX, BUILD_VERSION, BUILD_IMMUTABLE_DIR, *BRAND_BUILD_FILES)
    if any(not path.exists() for path in required_paths):
        raise RuntimeError('The frontend build is incomplete. Run `npm run build` and try again.')

    try:
        version_data = json.loads(BUILD_VERSION.read_text(encoding='utf-8'))
        version = str(version_data['version'])
    except (OSError, KeyError, TypeError, ValueError) as error:
        raise RuntimeError('The frontend build version is invalid. Run `npm run build` and try again.') from error

    immutable_files = sorted(
        path for path in BUILD_IMMUTABLE_DIR.rglob('*') if path.is_file() and path.suffix in {'.css', '.js'}
    )
    if not immutable_files:
        raise RuntimeError('The frontend build has no application assets. Run `npm run build` and try again.')

    try:
        digest = hashlib.sha256()
        digest.update(BUILD_INDEX.read_bytes())
        digest.update(BUILD_VERSION.read_bytes())
        for path in BRAND_BUILD_FILES:
            relative_path = path.relative_to(FRONTEND_BUILD_DIR).as_posix()
            digest.update(relative_path.encode('utf-8'))
            digest.update(path.read_bytes())
        for path in immutable_files:
            relative_path = path.relative_to(FRONTEND_BUILD_DIR).as_posix()
            digest.update(relative_path.encode('utf-8'))
            digest.update(str(path.stat().st_size).encode('ascii'))
    except OSError as error:
        raise RuntimeError(
            'The frontend build changed while it was being inspected. Wait for `npm run build` to finish and try again.'
        ) from error

    return f'qwythos-desktop:{version}:{digest.hexdigest()[:16]}'


def is_port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind((HOST, port))
        except OSError:
            return False
    return True


def get_server_deployment_id(port: int, timeout: float = 0.75) -> str | None:
    request = urllib.request.Request(
        f'{base_url(port)}/api/version',
        headers={'Cache-Control': 'no-cache'},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                return None
            payload = json.load(response)
            deployment_id = payload.get('deployment_id')
            return deployment_id if isinstance(deployment_id, str) else None
    except (json.JSONDecodeError, urllib.error.URLError, OSError, TimeoutError, ValueError):
        return None


def select_server_port(expected_deployment_id: str) -> tuple[int, bool]:
    """Return ``(port, should_start)`` without attaching to an unknown server."""
    first_available_port = None
    for port in range(PREFERRED_PORT, PREFERRED_PORT + PORT_SCAN_LIMIT):
        if is_port_available(port):
            if first_available_port is None:
                first_available_port = port
            continue

        if get_server_deployment_id(port) == expected_deployment_id:
            return port, False

    if first_available_port is not None:
        return first_available_port, True

    raise RuntimeError(
        f'No available local port was found between {PREFERRED_PORT} and ' f'{PREFERRED_PORT + PORT_SCAN_LIMIT - 1}.'
    )


def get_or_create_secret_key() -> str:
    if SECRET_KEY_FILE.exists():
        existing = SECRET_KEY_FILE.read_text(encoding='utf-8').strip()
        if existing:
            return existing
    key = secrets.token_urlsafe(32)
    SECRET_KEY_FILE.write_text(key, encoding='utf-8')
    return key


def start_server(port: int, deployment_id: str) -> subprocess.Popen:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env['WEBUI_SECRET_KEY'] = get_or_create_secret_key()
    env['DEPLOYMENT_ID'] = deployment_id
    env['FRONTEND_BUILD_DIR'] = str(FRONTEND_BUILD_DIR)

    log_file = open(SERVER_LOG, 'a', encoding='utf-8')
    return subprocess.Popen(
        [sys.executable, '-m', 'uvicorn', 'qwythos.main:app', '--host', HOST, '--port', str(port)],
        cwd=str(BACKEND_DIR),
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        creationflags=CREATE_NO_WINDOW,
    )


def is_server_ready(port: int, expected_deployment_id: str) -> bool:
    try:
        with urllib.request.urlopen(f'{base_url(port)}/ready', timeout=1) as response:
            return response.status == 200 and get_server_deployment_id(port) == expected_deployment_id
    except (urllib.error.URLError, OSError, TimeoutError):
        return False


def wait_for_server(
    process: subprocess.Popen,
    port: int,
    expected_deployment_id: str,
    timeout: float = 90,
) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if process.poll() is not None:
            return False
        if is_server_ready(port, expected_deployment_id):
            return True
        time.sleep(0.5)
    return False


def shutdown_server(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


def show_error_window(message: str) -> None:
    webview.create_window(
        'Qwythos - Error',
        html=(
            '<body style="font-family: sans-serif; padding: 24px;">'
            '<h2>Qwythos could not start.</h2>'
            f'<p>{message}</p>'
            f'<p>Check <code>{SERVER_LOG}</code> for details.</p>'
            '</body>'
        ),
        width=560,
        height=280,
    )
    start_webview(persist_session=False)


def start_webview(persist_session: bool = True) -> None:
    options = {}
    if persist_session:
        options.update(
            {
                'private_mode': False,
                'storage_path': str(WEBVIEW_STORAGE),
            }
        )
    if ICON_PATH.exists():
        options['icon'] = str(ICON_PATH)

    try:
        signature = inspect.signature(webview.start)
        supports_arbitrary_options = any(
            parameter.kind is inspect.Parameter.VAR_KEYWORD for parameter in signature.parameters.values()
        )
        if not supports_arbitrary_options:
            options = {key: value for key, value in options.items() if key in signature.parameters}
    except (TypeError, ValueError):
        # Some wrapped callables do not expose a signature; current pywebview
        # accepts these options, so let its own argument validation decide.
        pass

    webview.start(**options)


def main() -> None:
    owns_server = False
    server_proc = None

    try:
        deployment_id = get_frontend_build_identity()
        port, should_start_server = select_server_port(deployment_id)
    except RuntimeError as error:
        show_error_window(str(error))
        return

    if should_start_server:
        server_proc = start_server(port, deployment_id)
        owns_server = True
        if not wait_for_server(server_proc, port, deployment_id):
            show_error_window('The local server did not become ready in time.')
            shutdown_server(server_proc)
            return

    # Keep the authenticated browser profile between launcher runs. Pywebview
    # defaults to private mode, which otherwise discards the token stored by
    # the frontend and sends returning users through /auth again.
    WEBVIEW_STORAGE.mkdir(parents=True, exist_ok=True)
    webview.create_window('Qwythos', f'{base_url(port)}/', width=1280, height=800, resizable=True)
    try:
        start_webview()
    finally:
        if owns_server and server_proc is not None:
            shutdown_server(server_proc)


if __name__ == '__main__':
    main()
