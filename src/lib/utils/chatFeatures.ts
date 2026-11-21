import { DEFAULT_ENABLED_CHAT_FEATURES } from '$lib/constants';

/**
 * Chat features that the composer exposes as switches in the integrations menu
 * and that this fork seeds from `DEFAULT_ENABLED_CHAT_FEATURES` in
 * `$lib/constants`.
 */
export type ChatFeature = 'web_search' | 'code_interpreter';

type Capabilities = Record<string, boolean | undefined>;

type ModelLike = {
	id?: string;
	info?: { meta?: { capabilities?: Capabilities } };
};

/** The stores / props the feature defaults are resolved from. */
export type ChatFeatureContext = {
	models?: ModelLike[] | null;
	selectedModelIds?: string[] | null;
	/** `$config?.features` — the server's feature flags. */
	featuresConfig?: Record<string, any> | null;
	user?: {
		role?: string;
		permissions?: { features?: Record<string, any> };
	} | null;
	/** `$settings` — per-user preferences; only "Never" opts out. */
	settings?: Record<string, any> | null;
	/** `$selectedTerminalId` — mutually exclusive with the code interpreter. */
	selectedTerminalId?: string | null;
};

const FEATURE_GATES: Record<
	ChatFeature,
	{ configKey: string; permissionKey: string; settingKey: string }
> = {
	web_search: {
		configKey: 'enable_web_search',
		permissionKey: 'web_search',
		settingKey: 'webSearch'
	},
	code_interpreter: {
		configKey: 'enable_code_interpreter',
		permissionKey: 'code_interpreter',
		settingKey: 'codeInterpreter'
	}
};

/**
 * Whether `feature` can be used at all for the current model selection, server
 * config and user. Missing model capability keys count as supported, which is
 * how the message input decides whether to render the switch in the first place.
 */
export const isChatFeatureAvailable = (
	feature: ChatFeature,
	context: ChatFeatureContext = {}
): boolean => {
	const { configKey, permissionKey } = FEATURE_GATES[feature];

	if (!context.featuresConfig?.[configKey]) {
		return false;
	}

	if (!(context.user?.role === 'admin' || context.user?.permissions?.features?.[permissionKey])) {
		return false;
	}

	if (feature === 'code_interpreter' && context.selectedTerminalId) {
		return false;
	}

	const modelIds = (context.selectedModelIds ?? []).filter((id) => !!id);
	if (modelIds.length === 0) {
		return false;
	}

	return modelIds.every((id) => {
		const model = (context.models ?? []).find((candidate) => candidate?.id === id);
		return model ? (model.info?.meta?.capabilities?.[feature] ?? true) : false;
	});
};

/**
 * Whether a chat should open with `feature` switched on.
 *
 * Availability (model capability, server feature flag, permission, terminal
 * exclusivity) always wins. After that the code-level default in
 * `DEFAULT_ENABLED_CHAT_FEATURES` decides, and an explicit "Never" in
 * Settings > Interface is honoured as a per-user opt-out. Legacy or untouched
 * preference values (`undefined`, `null`, `'always'`) all read as "on".
 */
export const resolveChatFeatureDefault = (
	feature: ChatFeature,
	context: ChatFeatureContext = {}
): boolean => {
	if (!DEFAULT_ENABLED_CHAT_FEATURES[feature]) {
		return false;
	}

	if (!isChatFeatureAvailable(feature, context)) {
		return false;
	}

	return context.settings?.[FEATURE_GATES[feature].settingKey] !== 'never';
};

/** Both switch states a chat opens in. */
export const resolveChatFeatureDefaults = (context: ChatFeatureContext = {}) => ({
	webSearchEnabled: resolveChatFeatureDefault('web_search', context),
	codeInterpreterEnabled: resolveChatFeatureDefault('code_interpreter', context)
});
