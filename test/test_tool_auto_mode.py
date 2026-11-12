"""Tests for model_supports_native_tools and auto mode logic."""

import ast
import unittest
from pathlib import Path

# Extract model_supports_native_tools from backend/qwythos/utils/tools.py via AST
# so we can test the exact code in the codebase without booting database/FastAPI
tools_file = Path(__file__).resolve().parents[1] / 'backend' / 'qwythos' / 'utils' / 'tools.py'
with open(tools_file, 'r', encoding='utf-8') as f:
    code = f.read()

tree = ast.parse(code)
func_node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'model_supports_native_tools')
func_code = compile(ast.Module(body=[func_node], type_ignores=[]), '<string>', 'exec')
ns = {}
exec(func_code, ns)
model_supports_native_tools = ns['model_supports_native_tools']


class TestToolAutoMode(unittest.TestCase):
    def test_venice_model_disabled(self):
        # Model with venice in ID
        model = {
            'id': 'venice-uncensored',
            'name': 'Venice: Uncensored',
            'owned_by': 'venice',
        }
        self.assertFalse(model_supports_native_tools(model))

    def test_venice_openrouter_id_disabled(self):
        model = {
            'id': 'cognitivecomputations/dolphin-mistral-24b:venice-edition',
            'name': 'Venice: Uncensored',
        }
        self.assertFalse(model_supports_native_tools(model))

    def test_openrouter_missing_tools_in_supported_parameters(self):
        model = {
            'id': 'some-open-weights-model',
            'supported_parameters': ['temperature', 'top_p', 'max_tokens'],
        }
        self.assertFalse(model_supports_native_tools(model))

    def test_openrouter_with_tools_in_supported_parameters(self):
        model = {
            'id': 'anthropic/claude-3.5-sonnet',
            'supported_parameters': ['tools', 'tool_choice', 'temperature'],
        }
        self.assertTrue(model_supports_native_tools(model))

    def test_explicit_capability_disabled(self):
        model = {
            'id': 'custom-model',
            'info': {
                'meta': {
                    'capabilities': {
                        'builtin_tools': False,
                    }
                }
            }
        }
        self.assertFalse(model_supports_native_tools(model))

    def test_standard_model_default_enabled(self):
        model = {
            'id': 'openai/gpt-4o',
            'name': 'GPT-4o',
        }
        self.assertTrue(model_supports_native_tools(model))

    def test_venice_default_features_in_config(self):
        config_file = Path(__file__).resolve().parents[1] / 'backend' / 'qwythos' / 'config.py'
        with open(config_file, 'r', encoding='utf-8') as f:
            cfg_code = f.read()
        cfg_tree = ast.parse(cfg_code)
        # Find DEFAULT_MODEL_METADATA assignment
        for node in cfg_tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == 'DEFAULT_MODEL_METADATA':
                        dict_node = node.value
                        if isinstance(dict_node, ast.Dict):
                            for k, v in zip(dict_node.keys, dict_node.values):
                                if isinstance(k, ast.Constant) and k.value == 'venice-uncensored' and isinstance(v, ast.Dict):
                                    found_keys = {}
                                    for sub_k, sub_v in zip(v.keys, v.values):
                                        if isinstance(sub_k, ast.Constant):
                                            if isinstance(sub_v, ast.List):
                                                found_keys[sub_k.value] = [el.value for el in sub_v.elts if isinstance(el, ast.Constant)]
                                            elif isinstance(sub_v, ast.Constant):
                                                found_keys[sub_k.value] = sub_v.value
                                    self.assertIn('defaultFeatureIds', found_keys)
                                    self.assertIn('web_search', found_keys['defaultFeatureIds'])
                                    return
        self.fail("DEFAULT_MODEL_METADATA['venice-uncensored'] was not found or missing defaultFeatureIds")



if __name__ == '__main__':
    unittest.main()
