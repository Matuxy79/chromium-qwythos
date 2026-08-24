"""OpenRouter as the default OpenAI-compatible provider.

Chat, embeddings, speech, and images all resolve through one API key instead of
each feature asking for its own URL+key pair. Per-feature credentials remain as
optional overrides.

This module keeps credential math import-light so it can be unit-tested without
booting FastAPI.
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)

OPENROUTER_DEFAULT_BASE_URL = 'https://openrouter.ai/api/v1'
OPENAI_OFFICIAL_BASE_URL = 'https://api.openai.com/v1'
OPENROUTER_APP_REFERER = 'https://qwythos.com/'
OPENROUTER_APP_TITLE = 'Qwythos'
OPENROUTER_KEY_PREFIX = 'sk-or-'


def normalize_base_url(url: str | None) -> str:
    return (url or '').strip().rstrip('/')


def is_openrouter_url(url: str | None) -> bool:
    return 'openrouter.ai' in normalize_base_url(url)


def is_openrouter_key(key: str | None) -> bool:
    return (key or '').strip().startswith(OPENROUTER_KEY_PREFIX)


def openrouter_attribution_headers(url: str | None) -> dict[str, str]:
    if not is_openrouter_url(url):
        return {}
    return {
        'HTTP-Referer': OPENROUTER_APP_REFERER,
        'X-Title': OPENROUTER_APP_TITLE,
    }


def with_openrouter_headers(headers: dict | None, url: str | None) -> dict:
    merged = dict(headers or {})
    merged.update(openrouter_attribution_headers(url))
    return merged


def is_placeholder_openai_credentials(url: str | None, key: str | None) -> bool:
    """True when the pair is the inherited api.openai.com + empty-key default."""
    if (key or '').strip():
        return False
    normalized = normalize_base_url(url)
    return normalized in ('', OPENAI_OFFICIAL_BASE_URL)


def display_feature_credentials(url: str | None, key: str | None) -> tuple[str, str]:
    """Blank out placeholder openai.com credentials so admin forms inherit OpenRouter."""
    if is_placeholder_openai_credentials(url, key):
        return '', ''
    return normalize_base_url(url), (key or '')


def resolve_openai_compatible_credentials(
    *,
    feature_url: str | None = None,
    feature_key: str | None = None,
    openrouter_url: str | None = None,
    openrouter_key: str | None = None,
    openai_urls: list[str] | None = None,
    openai_keys: list[str] | None = None,
) -> tuple[str, str]:
    """Return (base_url, api_key) for an OpenAI-compatible feature.

    Explicit feature credentials win. Otherwise OpenRouter, then the first
    matching chat connection (OpenRouter preferred), then the first connection.
    """
    if not is_placeholder_openai_credentials(feature_url, feature_key):
        url = normalize_base_url(feature_url)
        key = (feature_key or '').strip()
        if not url:
            url = normalize_base_url(openrouter_url) or OPENROUTER_DEFAULT_BASE_URL
        return url, key

    or_key = (openrouter_key or '').strip()
    or_url = normalize_base_url(openrouter_url) or OPENROUTER_DEFAULT_BASE_URL
    if or_key:
        return or_url, or_key

    urls = [normalize_base_url(url) for url in (openai_urls or []) if normalize_base_url(url)]
    keys = list(openai_keys or [])
    if urls:
        idx = 0
        for i, url in enumerate(urls):
            if is_openrouter_url(url):
                idx = i
                break
        return urls[idx], keys[idx] if idx < len(keys) else ''

    return or_url, ''


def openai_compatible_connection_index(
    api_base_urls: list[str],
    preferred_url: str | None = None,
) -> int:
    """Index to use for /openai/audio/speech and similar single-connection paths."""
    urls = [normalize_base_url(url) for url in api_base_urls]
    candidates: list[str] = []
    if preferred_url:
        candidates.append(normalize_base_url(preferred_url))
    candidates.extend([OPENROUTER_DEFAULT_BASE_URL, OPENAI_OFFICIAL_BASE_URL])
    for candidate in candidates:
        if candidate and candidate in urls:
            return urls.index(candidate)
    if urls:
        return 0
    raise ValueError('no openai-compatible connection')


def _shift_numeric_api_configs(api_configs: dict, delta: int) -> dict:
    shifted: dict[str, Any] = {}
    for key, value in (api_configs or {}).items():
        if str(key).isdigit():
            shifted[str(int(key) + delta)] = value
        else:
            shifted[key] = value
    return shifted


def merge_openrouter_into_openai_connections(
    *,
    openrouter_url: str,
    openrouter_key: str,
    api_base_urls: list[str] | None,
    api_keys: list[str] | None,
    api_configs: dict | None,
) -> tuple[list[str], list[str], dict, bool]:
    """Keep openai.* arrays aligned with the OpenRouter key.

    Returns (urls, keys, configs, changed).
    """
    url = normalize_base_url(openrouter_url) or OPENROUTER_DEFAULT_BASE_URL
    key = (openrouter_key or '').strip()
    urls = [normalize_base_url(item) or OPENAI_OFFICIAL_BASE_URL for item in (api_base_urls or [])]
    keys = list(api_keys or [])
    configs = dict(api_configs or {})

    if len(keys) < len(urls):
        keys = [*keys, *([''] * (len(urls) - len(keys)))]
    elif len(keys) > len(urls):
        keys = keys[: len(urls)]

    if not key:
        return urls, keys, configs, False

    for idx, existing in enumerate(urls):
        if is_openrouter_url(existing) or existing == url:
            changed = keys[idx] != key or existing != url
            if existing != url:
                urls[idx] = url
            if keys[idx] != key:
                keys[idx] = key
            return urls, keys, configs, changed

    placeholder_only = (not urls) or (
        len(urls) == 1
        and urls[0] == OPENAI_OFFICIAL_BASE_URL
        and not (keys[0] if keys else '')
    )
    if placeholder_only:
        legacy = configs.get('0', configs.get(OPENAI_OFFICIAL_BASE_URL, {}))
        return [url], [key], {'0': legacy if isinstance(legacy, dict) else {}}, True

    return [url, *urls], [key, *keys], {'0': {}, **_shift_numeric_api_configs(configs, 1)}, True


async def get_resolved_openai_compatible(
    feature_url: str | None = None,
    feature_key: str | None = None,
) -> tuple[str, str]:
    from qwythos.models.config import Config

    values = await Config.get_many(
        'openrouter.api_key',
        'openrouter.base_url',
        'openai.api_base_urls',
        'openai.api_keys',
    )
    return resolve_openai_compatible_credentials(
        feature_url=feature_url,
        feature_key=feature_key,
        openrouter_url=values.get('openrouter.base_url'),
        openrouter_key=values.get('openrouter.api_key'),
        openai_urls=values.get('openai.api_base_urls') or [],
        openai_keys=values.get('openai.api_keys') or [],
    )


async def is_openrouter_configured() -> bool:
    from qwythos.models.config import Config

    key = await Config.get('openrouter.api_key', '')
    return bool((key or '').strip())


async def _hydrate_openrouter_key_from_connections() -> None:
    """Copy an existing OpenRouter chat connection into openrouter.* on upgrade."""
    from qwythos.models.config import Config

    current_key = (await Config.get('openrouter.api_key', '') or '').strip()
    if current_key:
        return

    values = await Config.get_many('openai.api_base_urls', 'openai.api_keys', 'openrouter.base_url')
    urls = values.get('openai.api_base_urls') or []
    keys = values.get('openai.api_keys') or []
    for idx, existing in enumerate(urls):
        candidate = keys[idx] if idx < len(keys) else ''
        if not (candidate or '').strip():
            continue
        if is_openrouter_url(existing) or is_openrouter_key(candidate):
            await Config.upsert(
                {
                    'openrouter.api_key': candidate.strip(),
                    'openrouter.base_url': (
                        normalize_base_url(existing)
                        if is_openrouter_url(existing)
                        else (values.get('openrouter.base_url') or OPENROUTER_DEFAULT_BASE_URL)
                    ),
                }
            )
            log.info('Hydrated openrouter.api_key from existing openai connection %s', idx)
            return


async def get_openrouter_runtime() -> tuple[str, str]:
    from qwythos.models.config import Config

    values = await Config.get_many('openrouter.api_key', 'openrouter.base_url')
    url = normalize_base_url(values.get('openrouter.base_url')) or OPENROUTER_DEFAULT_BASE_URL
    return url, (values.get('openrouter.api_key') or '').strip()


async def ensure_openrouter_openai_connection(*, hydrate: bool = False) -> bool:
    """Seed or sync openai.* chat connections from openrouter.api_key.

    Returns True when persisted openai.* values changed.
    Set hydrate=True on startup so 0.11 OpenRouter chat connections fill
    openrouter.api_key. Do not hydrate after an explicit admin save, or a
    cleared key would be copied back from the connection list.
    """
    from qwythos.models.config import Config

    if hydrate:
        await _hydrate_openrouter_key_from_connections()
    url, key = await get_openrouter_runtime()

    values = await Config.get_many(
        'openai.api_base_urls',
        'openai.api_keys',
        'openai.api_configs',
    )
    urls = values.get('openai.api_base_urls') or []
    keys = values.get('openai.api_keys') or []
    configs = values.get('openai.api_configs') or {}

    if not key:
        if len(keys) < len(urls):
            keys = [*keys, *([''] * (len(urls) - len(keys)))]
        changed = False
        for idx, existing in enumerate(urls):
            if is_openrouter_url(existing) or normalize_base_url(existing) == url:
                if keys[idx]:
                    keys[idx] = ''
                    changed = True
        if changed:
            await Config.upsert({'openai.api_keys': keys})
        return changed

    urls, keys, configs, changed = merge_openrouter_into_openai_connections(
        openrouter_url=url,
        openrouter_key=key,
        api_base_urls=urls,
        api_keys=keys,
        api_configs=configs,
    )
    updates = {}
    if changed:
        updates.update(
            {
                'openai.api_base_urls': urls,
                'openai.api_keys': keys,
                'openai.api_configs': configs,
            }
        )
        await Config.upsert(updates)
        log.info('Synchronized OpenRouter into openai chat connections')
    return changed


async def set_openrouter_api_key(api_key: str, base_url: str | None = None) -> None:
    from qwythos.models.config import Config

    updates = {'openrouter.api_key': (api_key or '').strip()}
    if base_url is not None:
        updates['openrouter.base_url'] = normalize_base_url(base_url) or OPENROUTER_DEFAULT_BASE_URL
    await Config.upsert(updates)
    await ensure_openrouter_openai_connection()
