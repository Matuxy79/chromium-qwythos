import { describe, expect, it } from 'vitest';
import {
	isChatFeatureAvailable,
	resolveChatFeatureDefault,
	resolveChatFeatureDefaults,
	type ChatFeatureContext
} from './chatFeatures';

const models = [{ id: 'venice-uncensored' }, { id: 'gpt-4o' }];

const baseContext = (overrides: ChatFeatureContext = {}): ChatFeatureContext => ({
	models,
	selectedModelIds: ['venice-uncensored'],
	featuresConfig: { enable_web_search: true, enable_code_interpreter: true },
	user: { role: 'admin', permissions: { features: {} } },
	settings: {},
	selectedTerminalId: null,
	...overrides
});

describe('chat feature defaults', () => {
	it('opens a chat with web search and code interpreter switched on', () => {
		expect(resolveChatFeatureDefaults(baseContext())).toEqual({
			webSearchEnabled: true,
			codeInterpreterEnabled: true
		});
	});

	it('treats legacy and untouched preferences as on', () => {
		for (const settings of [{}, { webSearch: null, codeInterpreter: null }, { webSearch: 'always', codeInterpreter: 'always' }]) {
			expect(resolveChatFeatureDefault('web_search', baseContext({ settings }))).toBe(true);
			expect(resolveChatFeatureDefault('code_interpreter', baseContext({ settings }))).toBe(true);
		}
	});

	it('honours an explicit "Never" as an opt-out', () => {
		expect(
			resolveChatFeatureDefault('web_search', baseContext({ settings: { webSearch: 'never' } }))
		).toBe(false);
		expect(
			resolveChatFeatureDefault(
				'code_interpreter',
				baseContext({ settings: { codeInterpreter: 'never' } })
			)
		).toBe(false);
	});

	it('counts missing model capability keys as supported', () => {
		expect(resolveChatFeatureDefaults(baseContext())).toEqual({
			webSearchEnabled: true,
			codeInterpreterEnabled: true
		});
	});

	it('stays off when the model cannot use the feature', () => {
		const limitedModels = [
			{
				id: 'venice-uncensored',
				info: { meta: { capabilities: { web_search: false, code_interpreter: false } } }
			}
		];

		expect(resolveChatFeatureDefaults(baseContext({ models: limitedModels }))).toEqual({
			webSearchEnabled: false,
			codeInterpreterEnabled: false
		});
	});

	it('stays off when the server disabled the feature', () => {
		const featuresConfig = { enable_web_search: false, enable_code_interpreter: false };
		expect(resolveChatFeatureDefaults(baseContext({ featuresConfig }))).toEqual({
			webSearchEnabled: false,
			codeInterpreterEnabled: false
		});
	});

	it('stays off without user permission', () => {
		const user = { role: 'user', permissions: { features: {} } };
		expect(resolveChatFeatureDefaults(baseContext({ user }))).toEqual({
			webSearchEnabled: false,
			codeInterpreterEnabled: false
		});
	});

	it('lets a user with permissions use both features', () => {
		const user = { role: 'user', permissions: { features: { web_search: true } } };
		expect(resolveChatFeatureDefaults(baseContext({ user }))).toEqual({
			webSearchEnabled: true,
			codeInterpreterEnabled: false
		});
	});

	it('keeps code interpreter off while a terminal is selected', () => {
		expect(
			resolveChatFeatureDefaults(baseContext({ selectedTerminalId: 'local-terminal' }))
		).toEqual({
			webSearchEnabled: true,
			codeInterpreterEnabled: false
		});
	});

	it('stays off until a model is selected', () => {
		expect(resolveChatFeatureDefaults(baseContext({ selectedModelIds: [''] }))).toEqual({
			webSearchEnabled: false,
			codeInterpreterEnabled: false
		});
		expect(resolveChatFeatureDefaults(baseContext({ selectedModelIds: [] }))).toEqual({
			webSearchEnabled: false,
			codeInterpreterEnabled: false
		});
	});

	it('requires every selected model to be capable', () => {
		const mixed = [
			{ id: 'venice-uncensored' },
			{ id: 'gpt-4o', info: { meta: { capabilities: { web_search: false } } } }
		];
		expect(
			resolveChatFeatureDefault(
				'web_search',
				baseContext({ models: mixed, selectedModelIds: ['venice-uncensored', 'gpt-4o'] })
			)
		).toBe(false);
		expect(
			resolveChatFeatureDefault(
				'code_interpreter',
				baseContext({ models: mixed, selectedModelIds: ['venice-uncensored', 'gpt-4o'] })
			)
		).toBe(true);
	});

	it('reports availability separately from the default', () => {
		expect(isChatFeatureAvailable('web_search', baseContext())).toBe(true);
		expect(
			isChatFeatureAvailable('web_search', baseContext({ settings: { webSearch: 'never' } }))
		).toBe(true);
		expect(isChatFeatureAvailable('web_search', baseContext({ selectedModelIds: [] }))).toBe(false);
	});
});
