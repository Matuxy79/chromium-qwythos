<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext } from 'svelte';

	import { models as modelsStore, user } from '$lib/stores';
	import { getCouncilConfig, setCouncilConfig } from '$lib/apis/configs';

	import Modal from '$lib/components/common/Modal.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ModelSelector from '$lib/components/admin/Settings/Models/ModelSelector.svelte';
	import SettingsSelect from '$lib/components/common/SettingsSelect.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n = getContext('i18n');

	export let show = false;

	const MIN_MODELS = 2;
	const MAX_MODELS = 5;

	let loading = false;
	let saving = false;

	let enabled = true;
	let modelIds: string[] = [];
	let chairmanModelId = '';

	$: isAdmin = $user?.role === 'admin';
	$: valid = modelIds.length >= MIN_MODELS && modelIds.length <= MAX_MODELS;
	$: if (chairmanModelId && !modelIds.includes(chairmanModelId)) {
		chairmanModelId = '';
	}
	$: if (modelIds.length > MAX_MODELS) {
		modelIds = modelIds.slice(0, MAX_MODELS);
	}

	const initHandler = async () => {
		if (!isAdmin) return;

		loading = true;
		try {
			const config = await getCouncilConfig(localStorage.token);
			enabled = config.ENABLE_COUNCIL ?? true;
			modelIds = (config.COUNCIL_MODELS ?? '')
				.split(',')
				.map((id: string) => id.trim())
				.filter((id: string) => id.length > 0);
			chairmanModelId = config.COUNCIL_CHAIRMAN_MODEL ?? '';
		} catch (error) {
			toast.error(`${error?.detail ?? error}`);
		}
		loading = false;
	};

	const submitHandler = async () => {
		if (!valid) {
			toast.error(
				$i18n.t('Select between {{min}} and {{max}} models for the council.', {
					min: MIN_MODELS,
					max: MAX_MODELS
				})
			);
			return;
		}

		saving = true;
		try {
			await setCouncilConfig(localStorage.token, {
				ENABLE_COUNCIL: enabled,
				COUNCIL_MODELS: modelIds.join(','),
				COUNCIL_CHAIRMAN_MODEL: chairmanModelId
			});
			toast.success($i18n.t('Council settings saved'));
		} catch (error) {
			toast.error(`${error?.detail ?? error}`);
		}
		saving = false;
	};

	$: if (show) {
		initHandler();
	}
</script>

<Modal size="sm" bind:show>
	<div>
		<div class="flex justify-between dark:text-gray-100 px-4 pt-3 pb-1">
			<div class="self-center text-sm font-medium flex items-center gap-1.5">
				<span aria-hidden="true">👑</span>
				{$i18n.t('LLM Council')}
			</div>
			<button
				class="self-center rounded-lg p-1 text-gray-500 transition hover:bg-gray-50 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200"
				type="button"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-4'} />
			</button>
		</div>

		<div class="flex flex-col w-full px-4 pb-3.5 dark:text-gray-200">
			{#if !isAdmin}
				<div class="text-sm text-gray-500 py-4 text-center">
					{$i18n.t('Only an admin can configure the council roster. Ask your admin to set this up.')}
				</div>
			{:else if loading}
				<div class="flex justify-center py-6">
					<Spinner className="size-5" />
				</div>
			{:else}
				<form
					class="flex flex-col gap-3.5"
					on:submit|preventDefault={() => {
						submitHandler();
					}}
				>
					<div class="flex items-center justify-between">
						<div class="text-sm">{$i18n.t('Enable LLM Council')}</div>
						<Switch bind:state={enabled} />
					</div>

					<div>
						<ModelSelector
							title={$i18n.t('Council roster ({{count}}/{{max}})', {
								count: modelIds.length,
								max: MAX_MODELS
							})}
							tooltip={$i18n.t(
								'Pick {{min}}-{{max}} models. Every prompt sent to the council goes to all of them in parallel.',
								{ min: MIN_MODELS, max: MAX_MODELS }
							)}
							models={modelIds.length >= MAX_MODELS ? [] : $modelsStore}
							bind:modelIds
						/>
						{#if !valid}
							<div class="text-xs text-amber-600 dark:text-amber-400 mt-1">
								{$i18n.t('Select at least {{min}} models (max {{max}}).', {
									min: MIN_MODELS,
									max: MAX_MODELS
								})}
							</div>
						{/if}
					</div>

					{#if modelIds.length >= MIN_MODELS}
						<div class="flex flex-col w-full">
							<div class="mb-1 text-xs text-gray-500">
								{$i18n.t('Chairman model')}
							</div>
							<SettingsSelect className="w-full" selectClassName="text-sm" bind:value={chairmanModelId}>
								<option value=""
									>{$i18n.t('Auto (first council model or configured default)')}</option
								>
								{#each modelIds as modelId}
									<option value={modelId} class="bg-gray-50 dark:bg-gray-700">
										{$modelsStore.find((m) => m.id === modelId)?.name ?? modelId}
									</option>
								{/each}
							</SettingsSelect>
						</div>
					{/if}

					<div class="text-xs text-gray-500">
						{$i18n.t(
							'To let a chat model call the council, enable the "LLM Council" builtin tool for it in Workspace → Models → (edit model) → Builtin Tools.'
						)}
					</div>

					<div class="flex justify-end pt-1 text-sm font-normal">
						<button
							class="px-3 py-1.5 text-sm font-normal bg-black hover:bg-gray-950 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex items-center gap-2 whitespace-nowrap {saving ||
							!valid
								? ' cursor-not-allowed opacity-50'
								: ''}"
							type="submit"
							disabled={saving || !valid}
						>
							{$i18n.t('Save')}

							{#if saving}
								<span class="shrink-0">
									<Spinner />
								</span>
							{/if}
						</button>
					</div>
				</form>
			{/if}
		</div>
	</div>
</Modal>
