"""Pure-function tests for OpenRouter credential consolidation."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parents[1] / 'backend' / 'qwythos' / 'utils' / 'openrouter.py'
_SPEC = importlib.util.spec_from_file_location('qwythos_openrouter', _MODULE_PATH)
openrouter = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(openrouter)

OPENAI_OFFICIAL_BASE_URL = openrouter.OPENAI_OFFICIAL_BASE_URL
OPENROUTER_DEFAULT_BASE_URL = openrouter.OPENROUTER_DEFAULT_BASE_URL
display_feature_credentials = openrouter.display_feature_credentials
is_placeholder_openai_credentials = openrouter.is_placeholder_openai_credentials
merge_openrouter_into_openai_connections = openrouter.merge_openrouter_into_openai_connections
openai_compatible_connection_index = openrouter.openai_compatible_connection_index
openrouter_attribution_headers = openrouter.openrouter_attribution_headers
resolve_openai_compatible_credentials = openrouter.resolve_openai_compatible_credentials


class ResolveCredentialsTests(unittest.TestCase):
    def test_placeholder_openai_com_is_detected(self):
        self.assertTrue(is_placeholder_openai_credentials(OPENAI_OFFICIAL_BASE_URL, ''))
        self.assertTrue(is_placeholder_openai_credentials('', None))
        self.assertFalse(is_placeholder_openai_credentials(OPENAI_OFFICIAL_BASE_URL, 'sk-real'))
        self.assertFalse(is_placeholder_openai_credentials('http://localhost:1234/v1', ''))

    def test_feature_override_wins(self):
        url, key = resolve_openai_compatible_credentials(
            feature_url='https://api.openai.com/v1',
            feature_key='sk-openai',
            openrouter_url=OPENROUTER_DEFAULT_BASE_URL,
            openrouter_key='sk-or-abc',
        )
        self.assertEqual(url, OPENAI_OFFICIAL_BASE_URL)
        self.assertEqual(key, 'sk-openai')

    def test_empty_feature_falls_back_to_openrouter(self):
        url, key = resolve_openai_compatible_credentials(
            feature_url=OPENAI_OFFICIAL_BASE_URL,
            feature_key='',
            openrouter_url=OPENROUTER_DEFAULT_BASE_URL,
            openrouter_key='sk-or-abc',
            openai_urls=[OPENAI_OFFICIAL_BASE_URL],
            openai_keys=[''],
        )
        self.assertEqual(url, OPENROUTER_DEFAULT_BASE_URL)
        self.assertEqual(key, 'sk-or-abc')

    def test_existing_openrouter_chat_connection_used_without_namespace(self):
        url, key = resolve_openai_compatible_credentials(
            feature_url='',
            feature_key='',
            openrouter_url=OPENROUTER_DEFAULT_BASE_URL,
            openrouter_key='',
            openai_urls=['https://openrouter.ai/api/v1', OPENAI_OFFICIAL_BASE_URL],
            openai_keys=['sk-or-from-chat', 'sk-openai'],
        )
        self.assertEqual(url, OPENROUTER_DEFAULT_BASE_URL)
        self.assertEqual(key, 'sk-or-from-chat')

    def test_display_blanks_placeholders(self):
        self.assertEqual(display_feature_credentials(OPENAI_OFFICIAL_BASE_URL, ''), ('', ''))
        self.assertEqual(
            display_feature_credentials('https://proxy.example/v1', 'sk-x'),
            ('https://proxy.example/v1', 'sk-x'),
        )


class MergeConnectionTests(unittest.TestCase):
    def test_replaces_placeholder_openai_com(self):
        urls, keys, configs, changed = merge_openrouter_into_openai_connections(
            openrouter_url=OPENROUTER_DEFAULT_BASE_URL,
            openrouter_key='sk-or-abc',
            api_base_urls=[OPENAI_OFFICIAL_BASE_URL],
            api_keys=[''],
            api_configs={'0': {'enable': True}},
        )
        self.assertTrue(changed)
        self.assertEqual(urls, [OPENROUTER_DEFAULT_BASE_URL])
        self.assertEqual(keys, ['sk-or-abc'])
        self.assertEqual(configs['0']['enable'], True)

    def test_syncs_existing_openrouter_index(self):
        urls, keys, configs, changed = merge_openrouter_into_openai_connections(
            openrouter_url=OPENROUTER_DEFAULT_BASE_URL,
            openrouter_key='sk-or-new',
            api_base_urls=[OPENROUTER_DEFAULT_BASE_URL, 'https://router.huggingface.co/v1'],
            api_keys=['sk-or-old', 'hf_x'],
            api_configs={'0': {}, '1': {'prefix_id': 'hf'}},
        )
        self.assertTrue(changed)
        self.assertEqual(keys[0], 'sk-or-new')
        self.assertEqual(urls[1], 'https://router.huggingface.co/v1')
        self.assertEqual(configs['1']['prefix_id'], 'hf')

    def test_prepends_and_shifts_configs(self):
        urls, keys, configs, changed = merge_openrouter_into_openai_connections(
            openrouter_url=OPENROUTER_DEFAULT_BASE_URL,
            openrouter_key='sk-or-abc',
            api_base_urls=['https://router.huggingface.co/v1'],
            api_keys=['hf_x'],
            api_configs={'0': {'prefix_id': 'hf'}},
        )
        self.assertTrue(changed)
        self.assertEqual(urls[0], OPENROUTER_DEFAULT_BASE_URL)
        self.assertEqual(keys, ['sk-or-abc', 'hf_x'])
        self.assertEqual(configs['1']['prefix_id'], 'hf')

    def test_empty_key_is_noop(self):
        urls, keys, configs, changed = merge_openrouter_into_openai_connections(
            openrouter_url=OPENROUTER_DEFAULT_BASE_URL,
            openrouter_key='',
            api_base_urls=[OPENAI_OFFICIAL_BASE_URL],
            api_keys=[''],
            api_configs={},
        )
        self.assertFalse(changed)
        self.assertEqual(urls, [OPENAI_OFFICIAL_BASE_URL])


class SpeechIndexTests(unittest.TestCase):
    def test_prefers_openrouter_over_openai_com(self):
        idx = openai_compatible_connection_index(
            [OPENAI_OFFICIAL_BASE_URL, OPENROUTER_DEFAULT_BASE_URL],
            OPENROUTER_DEFAULT_BASE_URL,
        )
        self.assertEqual(idx, 1)

    def test_falls_back_to_first_url(self):
        idx = openai_compatible_connection_index(['https://router.huggingface.co/v1'])
        self.assertEqual(idx, 0)

    def test_raises_when_empty(self):
        with self.assertRaises(ValueError):
            openai_compatible_connection_index([])

    def test_openrouter_headers_only_for_openrouter_urls(self):
        self.assertIn('HTTP-Referer', openrouter_attribution_headers(OPENROUTER_DEFAULT_BASE_URL))
        self.assertEqual(openrouter_attribution_headers(OPENAI_OFFICIAL_BASE_URL), {})


if __name__ == '__main__':
    unittest.main()
