<script lang="ts">
	import DOMPurify from 'dompurify';
	import { marked } from 'marked';

	import { toast } from 'svelte-sonner';

	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { getBackendConfig } from '$lib/apis';
	import {
		ldapUserSignIn,
		getSessionUser,
		userSignIn,
		userSignUp,
		updateUserTimezone
	} from '$lib/apis/auths';

	import { WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, config, user, socket } from '$lib/stores';

	import { generateInitialsImage, getUserTimezone } from '$lib/utils';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import OnBoarding from '$lib/components/OnBoarding.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';

	const i18n = getContext('i18n');

	let loaded = false;

	let mode = $config?.features.enable_ldap ? 'ldap' : 'signin';

	let form = null;

	let name = '';
	let email = '';
	let password = '';
	let confirmPassword = '';
	let openrouterApiKey = '';

	let ldapUsername = '';

	let submitting = false;

	const normalizeRedirectPath = (redirectPath: string | null | undefined) => {
		if (!redirectPath || !redirectPath.startsWith('/') || redirectPath.startsWith('//')) {
			return '/';
		}

		try {
			const url = new URL(redirectPath, window.location.origin);
			if (
				url.origin !== window.location.origin ||
				url.pathname === '/auth' ||
				url.pathname === '/error'
			) {
				return '/';
			}

			return `${url.pathname}${url.search}${url.hash}`;
		} catch {
			return '/';
		}
	};

	const setSessionUser = async (sessionUser, redirectPath: string | null = null) => {
		if (sessionUser) {
			toast.success($i18n.t(`You're now logged in.`));
			if (sessionUser.token) {
				localStorage.token = sessionUser.token;
			}
			await user.set(sessionUser);

			try {
				$socket?.emit('user-join', { auth: { token: sessionUser.token } });
			} catch (error) {
				console.warn('Failed to join the authenticated socket session:', error);
			}

			try {
				await config.set(await getBackendConfig());
			} catch (error) {
				console.error('Error refreshing backend config after sign-in:', error);
			}

			// Update user timezone
			const timezone = getUserTimezone();
			if (sessionUser.token && timezone) {
				updateUserTimezone(sessionUser.token, timezone).catch((error) => {
					console.warn('Failed to update the user timezone after sign-in:', error);
				});
			}

			const destination = normalizeRedirectPath(
				redirectPath ??
					$page.url.searchParams.get('redirect') ??
					localStorage.getItem('redirectPath')
			);

			try {
				await goto(destination, { replaceState: true });
				localStorage.removeItem('redirectPath');
			} catch (error) {
				console.error('Client navigation after sign-in failed; reloading the app:', error);
				localStorage.removeItem('redirectPath');
				window.location.replace(destination);
			}
		}
	};

	const signInHandler = async () => {
		const sessionUser = await userSignIn(email, password).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		await setSessionUser(sessionUser);
	};

	const signUpHandler = async () => {
		if ($config?.features?.enable_signup_password_confirmation) {
			if (password !== confirmPassword) {
				toast.error($i18n.t('Passwords do not match.'));
				return;
			}
		}

		const sessionUser = await userSignUp(
			name,
			email,
			password,
			generateInitialsImage(name),
			($config?.onboarding ?? false) ? openrouterApiKey : ''
		).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		await setSessionUser(sessionUser);
	};

	const ldapSignInHandler = async () => {
		const sessionUser = await ldapUserSignIn(ldapUsername, password).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		await setSessionUser(sessionUser);
	};

	const submitHandler = async () => {
		if (submitting) {
			return;
		}

		submitting = true;
		try {
			if (mode === 'ldap') {
				await ldapSignInHandler();
			} else if (mode === 'signin') {
				await signInHandler();
			} else {
				await signUpHandler();
			}
		} finally {
			submitting = false;
		}
	};

	const oauthCallbackHandler = async () => {
		// Get the value of the 'token' cookie
		function getCookie(name) {
			const match = document.cookie.match(
				new RegExp('(?:^|; )' + name.replace(/([.$?*|{}()[\]\\/+^])/g, '\\$1') + '=([^;]*)')
			);
			return match ? decodeURIComponent(match[1]) : null;
		}

		const token = getCookie('token');
		if (!token) {
			return;
		}

		const sessionUser = await getSessionUser(token).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (!sessionUser) {
			return;
		}

		localStorage.token = token;
		await setSessionUser(sessionUser, localStorage.getItem('redirectPath') || null);
	};

	let onboarding = false;

	onMount(async () => {
		const requestedRedirectPath = $page.url.searchParams.get('redirect');
		const redirectPath = normalizeRedirectPath(requestedRedirectPath);
		if ($user) {
			await goto(redirectPath, { replaceState: true });
			return;
		} else if (requestedRedirectPath) {
			localStorage.setItem('redirectPath', redirectPath);
		}

		const error = $page.url.searchParams.get('error');
		if (error) {
			toast.error(error);
		}

		await oauthCallbackHandler();
		form = $page.url.searchParams.get('form');

		// Auto-redirect to SSO when OAUTH_AUTO_REDIRECT is enabled and the
		// deployment is unambiguously SSO-only (single provider, no login form,
		// no LDAP). Suppressed by ?form=, ?error=, onboarding, trusted-header
		// auth, or an existing session/token.
		if ($config?.oauth?.auto_redirect && !form && !error) {
			const providers = Object.keys($config?.oauth?.providers ?? {});
			if (
				providers.length === 1 &&
				$config?.features?.auth !== false &&
				$config?.features?.enable_login_form === false &&
				!$config?.features?.enable_ldap &&
				!$config?.features?.auth_trusted_header &&
				!$config?.onboarding &&
				!localStorage.token &&
				!document.cookie.split('; ').some((c) => c.startsWith('token='))
			) {
				window.location.href = `${WEBUI_BASE_URL}/oauth/${providers[0]}/login`;
				return;
			}
		}

		loaded = true;

		if (($config?.features?.auth_trusted_header ?? false) || $config?.features?.auth === false) {
			await signInHandler();
		} else {
			onboarding = $config?.onboarding ?? false;
		}
	});
</script>

<svelte:head>
	<title>
		{`${$WEBUI_NAME}`}
	</title>
</svelte:head>

<OnBoarding
	bind:show={onboarding}
	getStartedHandler={() => {
		onboarding = false;
		mode = $config?.features.enable_ldap ? 'ldap' : 'signup';
	}}
/>

{#if !onboarding}
	<div class="chromium-auth" id="auth-page">
		<div class="chromium-auth__backdrop"></div>

		<div class="chromium-auth__drag-region drag-region"></div>

		{#if loaded}
			<div class="chromium-auth__container" id="auth-container">
				<div class="chromium-auth__layout">
					<section class="chromium-auth__hero" aria-labelledby="chromium-wyvern-title">
						<img
							class="chromium-auth__hero-image"
							src="/assets/images/chromium-wyvern-auth.webp"
							alt="A chromium wyvern lit by electric cyan circuitry and ember-orange fire"
							draggable="false"
						/>

						<div class="chromium-auth__brand" aria-label="Qwythos">
							<svg viewBox="0 0 44 44" aria-hidden="true">
								<path d="M12 3.5h20L40.5 12v20L32 40.5H12L3.5 32V12z" />
								<path d="M14.5 11h15l4.5 4.5v13L29.5 33h-15L10 28.5v-13z" />
								<path d="m25.5 27.5 13 13" />
							</svg>
							<span>QWYTHOS</span>
						</div>

						<div class="chromium-auth__hero-copy">
							<h1 id="chromium-wyvern-title">CHROMIUM WYVERN</h1>
							<p>DESIGN YOUR ADVENTURE</p>
						</div>
					</section>

					<main
						class="chromium-auth__form-region"
						id="main-content"
						tabindex="-1"
						aria-labelledby="auth-form-title"
					>
						<div class="chromium-auth__form-frame">
							<svg
								class="chromium-auth__circuit chromium-auth__circuit--top"
								viewBox="0 0 160 72"
								aria-hidden="true"
							>
								<path d="M4 12h54l16 16h50l14 14h18" />
								<path d="M42 4v18l18 18h36l16 16h44" />
								<circle cx="4" cy="12" r="2.5" />
								<circle cx="156" cy="42" r="2.5" />
							</svg>

							<div class="chromium-auth__form-scroll">
								{#if ($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false}
									<div class="chromium-auth__signing-in">
										<div class="chromium-auth__signing-in-content">
											<div>
												{$i18n.t('Signing in to {{WEBUI_NAME}}', { WEBUI_NAME: $WEBUI_NAME })}
											</div>

											<div>
												<Spinner className="size-5" />
											</div>
										</div>
									</div>
								{:else}
									<div class="chromium-auth__form-content">
										<div
											id="auth-login-card"
											class="chromium-auth__card"
											class:chromium-auth__card--onboarding={$config?.onboarding ?? false}
										>
											{#if $config?.metadata?.auth_logo_position === 'center'}
												<div class="chromium-auth__custom-logo">
													<img
														id="logo"
														crossorigin="anonymous"
														src="{WEBUI_BASE_URL}/static/favicon.png"
														class="chromium-auth__custom-logo-image"
														alt="{$WEBUI_NAME} logo"
													/>
												</div>
											{/if}
											<form
												class="chromium-auth__form"
												on:submit={(e) => {
													e.preventDefault();
													submitHandler();
												}}
											>
												<header class="chromium-auth__heading">
													<h2 id="auth-form-title">
														{#if $config?.onboarding ?? false}
															{$i18n.t('Create Admin Account')}
														{:else if mode === 'ldap'}
															{$i18n.t(`Sign in to {{WEBUI_NAME}} with LDAP`, {
																WEBUI_NAME: $WEBUI_NAME
															})}
														{:else if mode === 'signin'}
															{$i18n.t(`Sign in to {{WEBUI_NAME}}`, { WEBUI_NAME: $WEBUI_NAME })}
														{:else}
															{$i18n.t(`Sign up to {{WEBUI_NAME}}`, { WEBUI_NAME: $WEBUI_NAME })}
														{/if}
													</h2>

													{#if $config?.onboarding ?? false}
														<p>
															{$i18n.t(
																'Paste your OpenRouter API key to connect chat, embeddings, speech, and images. You can add other providers later in Connections.'
															)}
														</p>
													{/if}
												</header>

												{#if $config?.features.enable_login_form || $config?.features.enable_ldap || form}
													<div class="chromium-auth__fields">
														{#if mode === 'signup'}
															<div class="chromium-auth__field">
																<label for="name" class="chromium-auth__label"
																	>{$i18n.t('Name')}</label
																>
																<input
																	bind:value={name}
																	type="text"
																	id="name"
																	class="chromium-auth__input"
																	autocomplete="name"
																	placeholder={$i18n.t('Enter Your Full Name')}
																	required
																/>
															</div>
														{/if}

														{#if mode === 'ldap'}
															<div class="chromium-auth__field">
																<label for="username" class="chromium-auth__label"
																	>{$i18n.t('Username')}</label
																>
																<input
																	bind:value={ldapUsername}
																	type="text"
																	class="chromium-auth__input"
																	autocomplete="username"
																	name="username"
																	id="username"
																	placeholder={$i18n.t('Enter Your Username')}
																	required
																/>
															</div>
														{:else}
															<div class="chromium-auth__field">
																<label for="email" class="chromium-auth__label"
																	>{$i18n.t('Email')}</label
																>
																<input
																	bind:value={email}
																	type="email"
																	id="email"
																	class="chromium-auth__input"
																	autocomplete="email"
																	name="email"
																	placeholder={$i18n.t('Enter Your Email')}
																	required
																/>
															</div>
														{/if}

														<div class="chromium-auth__field">
															<label for="password" class="chromium-auth__label"
																>{$i18n.t('Password')}</label
															>
															<SensitiveInput
																bind:value={password}
																type="password"
																id="password"
																outerClassName="chromium-auth__sensitive-shell"
																inputClassName="chromium-auth__sensitive-input"
																showButtonClassName="chromium-auth__sensitive-toggle"
																placeholder={$i18n.t('Enter Your Password')}
																autocomplete={mode === 'signup'
																	? 'new-password'
																	: 'current-password'}
																name="password"
																screenReader={false}
																required
																aria-required="true"
															/>
														</div>

														{#if mode === 'signup' && $config?.features?.enable_signup_password_confirmation}
															<div class="chromium-auth__field">
																<label for="confirm-password" class="chromium-auth__label"
																	>{$i18n.t('Confirm Password')}</label
																>
																<SensitiveInput
																	bind:value={confirmPassword}
																	type="password"
																	id="confirm-password"
																	outerClassName="chromium-auth__sensitive-shell"
																	inputClassName="chromium-auth__sensitive-input"
																	showButtonClassName="chromium-auth__sensitive-toggle"
																	placeholder={$i18n.t('Confirm Your Password')}
																	autocomplete="new-password"
																	name="confirm-password"
																	screenReader={false}
																	required
																/>
															</div>
														{/if}

														{#if ($config?.onboarding ?? false) && mode === 'signup'}
															<div class="chromium-auth__field">
																<label for="openrouter-api-key" class="chromium-auth__label"
																	>{$i18n.t('OpenRouter API Key')}</label
																>
																<SensitiveInput
																	bind:value={openrouterApiKey}
																	type="password"
																	id="openrouter-api-key"
																	outerClassName="chromium-auth__sensitive-shell"
																	inputClassName="chromium-auth__sensitive-input"
																	showButtonClassName="chromium-auth__sensitive-toggle"
																	placeholder="sk-or-..."
																	autocomplete="off"
																	name="openrouter-api-key"
																	screenReader={false}
																	required={false}
																/>
															</div>
														{/if}
													</div>
												{/if}
												<div class="chromium-auth__actions">
													{#if $config?.features.enable_login_form || $config?.features.enable_ldap || form}
														{#if mode === 'ldap'}
															<button
																class="chromium-auth__submit"
																type="submit"
																disabled={submitting}
															>
																<div class="self-center">{$i18n.t('Authenticate')}</div>

																{#if submitting}
																	<div class="ml-1.5 self-center">
																		<Spinner />
																	</div>
																{/if}
															</button>
														{:else}
															<button
																class="chromium-auth__submit"
																type="submit"
																disabled={submitting}
															>
																<div>
																	{mode === 'signin'
																		? $i18n.t('Sign in')
																		: ($config?.onboarding ?? false)
																			? $i18n.t('Create Admin Account')
																			: $i18n.t('Create Account')}
																</div>

																{#if submitting}
																	<div class="ml-1.5 self-center">
																		<Spinner />
																	</div>
																{/if}
															</button>

															{#if $config?.features.enable_signup && !($config?.onboarding ?? false)}
																<div class="chromium-auth__switch-mode">
																	{mode === 'signin'
																		? $i18n.t("Don't have an account?")
																		: $i18n.t('Already have an account?')}

																	<button
																		class="chromium-auth__text-button"
																		type="button"
																		on:click={() => {
																			if (mode === 'signin') {
																				mode = 'signup';
																			} else {
																				mode = 'signin';
																			}
																		}}
																	>
																		{mode === 'signin' ? $i18n.t('Sign up') : $i18n.t('Sign in')}
																	</button>
																</div>
															{/if}
														{/if}
													{/if}
												</div>
											</form>

											{#if Object.keys($config?.oauth?.providers ?? {}).length > 0}
												<div class="chromium-auth__divider">
													<hr />
													{#if $config?.features.enable_login_form || $config?.features.enable_ldap || form}
														<span class="chromium-auth__divider-label">{$i18n.t('or')}</span>
													{/if}

													<hr />
												</div>
												<div class="chromium-auth__provider-list">
													{#if $config?.oauth?.providers?.google}
														<button
															class="chromium-auth__provider-button"
															on:click={() => {
																window.location.href = `${WEBUI_BASE_URL}/oauth/google/login`;
															}}
														>
															<svg
																xmlns="http://www.w3.org/2000/svg"
																viewBox="0 0 48 48"
																class="size-6 mr-3"
																aria-hidden="true"
															>
																<path
																	fill="#EA4335"
																	d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"
																/><path
																	fill="#4285F4"
																	d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"
																/><path
																	fill="#FBBC05"
																	d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"
																/><path
																	fill="#34A853"
																	d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"
																/><path fill="none" d="M0 0h48v48H0z" />
															</svg>
															<span
																>{$i18n.t('Continue with {{provider}}', {
																	provider: 'Google'
																})}</span
															>
														</button>
													{/if}
													{#if $config?.oauth?.providers?.microsoft}
														<button
															class="chromium-auth__provider-button"
															on:click={() => {
																window.location.href = `${WEBUI_BASE_URL}/oauth/microsoft/login`;
															}}
														>
															<svg
																xmlns="http://www.w3.org/2000/svg"
																viewBox="0 0 21 21"
																class="size-6 mr-3"
																aria-hidden="true"
															>
																<rect x="1" y="1" width="9" height="9" fill="#f25022" /><rect
																	x="1"
																	y="11"
																	width="9"
																	height="9"
																	fill="#00a4ef"
																/><rect x="11" y="1" width="9" height="9" fill="#7fba00" /><rect
																	x="11"
																	y="11"
																	width="9"
																	height="9"
																	fill="#ffb900"
																/>
															</svg>
															<span
																>{$i18n.t('Continue with {{provider}}', {
																	provider: 'Microsoft'
																})}</span
															>
														</button>
													{/if}
													{#if $config?.oauth?.providers?.github}
														<button
															class="chromium-auth__provider-button"
															on:click={() => {
																window.location.href = `${WEBUI_BASE_URL}/oauth/github/login`;
															}}
														>
															<svg
																xmlns="http://www.w3.org/2000/svg"
																viewBox="0 0 24 24"
																class="size-6 mr-3"
																aria-hidden="true"
															>
																<path
																	fill="currentColor"
																	d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.92 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57C20.565 21.795 24 17.31 24 12c0-6.63-5.37-12-12-12z"
																/>
															</svg>
															<span
																>{$i18n.t('Continue with {{provider}}', {
																	provider: 'GitHub'
																})}</span
															>
														</button>
													{/if}
													{#if $config?.oauth?.providers?.oidc}
														<button
															class="chromium-auth__provider-button"
															on:click={() => {
																window.location.href = `${WEBUI_BASE_URL}/oauth/oidc/login`;
															}}
														>
															<svg
																xmlns="http://www.w3.org/2000/svg"
																fill="none"
																viewBox="0 0 24 24"
																stroke-width="1.5"
																stroke="currentColor"
																class="size-6 mr-3"
																aria-hidden="true"
															>
																<path
																	stroke-linecap="round"
																	stroke-linejoin="round"
																	d="M15.75 5.25a3 3 0 0 1 3 3m3 0a6 6 0 0 1-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1 1 21.75 8.25Z"
																/>
															</svg>

															<span
																>{$i18n.t('Continue with {{provider}}', {
																	provider: $config?.oauth?.providers?.oidc ?? 'SSO'
																})}</span
															>
														</button>
													{/if}
													{#if $config?.oauth?.providers?.feishu}
														<button
															class="chromium-auth__provider-button"
															on:click={() => {
																window.location.href = `${WEBUI_BASE_URL}/oauth/feishu/login`;
															}}
														>
															<span
																>{$i18n.t('Continue with {{provider}}', {
																	provider: 'Feishu'
																})}</span
															>
														</button>
													{/if}
												</div>
											{/if}

											{#if $config?.features.enable_ldap && $config?.features.enable_login_form}
												<div class="chromium-auth__ldap-switch">
													<button
														class="chromium-auth__text-button"
														type="button"
														on:click={() => {
															if (mode === 'ldap')
																mode = ($config?.onboarding ?? false) ? 'signup' : 'signin';
															else mode = 'ldap';
														}}
													>
														<span
															>{mode === 'ldap'
																? $i18n.t('Continue with Email')
																: $i18n.t('Continue with LDAP')}</span
														>
													</button>
												</div>
											{/if}
										</div>
										{#if $config?.metadata?.login_footer}
											<div class="chromium-auth__custom-footer">
												<div class="marked">
													<!-- DOMPurify sanitizes this configured Markdown before rendering. -->
													<!-- eslint-disable-next-line svelte/no-at-html-tags -->
													{@html DOMPurify.sanitize(marked($config?.metadata?.login_footer))}
												</div>
											</div>
										{/if}
									</div>
								{/if}

								{#if $config?.onboarding ?? false}
									<div class="chromium-auth__privacy-note">
										<span class="chromium-auth__privacy-line" aria-hidden="true"></span>
										<svg viewBox="0 0 20 20" aria-hidden="true">
											<path d="M6.5 9V6.5a3.5 3.5 0 0 1 7 0V9" />
											<rect x="4.5" y="9" width="11" height="8" rx="1.5" />
										</svg>
										<span>{$i18n.t('Private')} <b>&bull;</b> {$i18n.t('Local')}</span>
										<span class="chromium-auth__privacy-line" aria-hidden="true"></span>
									</div>
								{/if}
							</div>
						</div>
					</main>
				</div>
			</div>
		{/if}
	</div>
{/if}

<style>
	:global(html:has(#auth-page)),
	:global(body:has(#auth-page)) {
		background: #05080b;
	}

	.chromium-auth {
		--chromium-bg: #05080b;
		--chromium-panel: #10171d;
		--chromium-panel-deep: #0a1015;
		--chromium-surface: #172029;
		--chromium-border: #637481;
		--chromium-border-soft: rgba(132, 153, 170, 0.3);
		--chromium-text: #f4f7fa;
		--chromium-muted: #8b9aaa;
		--chromium-cyan: #27ddf5;
		--chromium-orange: #ff6a00;
		--chromium-orange-bright: #ff8a17;
		position: relative;
		isolation: isolate;
		width: 100%;
		height: 100dvh;
		overflow: hidden;
		background: var(--chromium-bg);
		color: var(--chromium-text);
		color-scheme: dark;
	}

	.chromium-auth__backdrop {
		position: absolute;
		inset: 0;
		z-index: -2;
		background:
			radial-gradient(circle at 75% 50%, rgba(24, 68, 80, 0.16), transparent 38%),
			var(--chromium-bg);
	}

	.chromium-auth__drag-region {
		position: absolute;
		inset: 0 0 auto;
		z-index: 20;
		height: 2rem;
		pointer-events: none;
	}

	.chromium-auth__container,
	.chromium-auth__layout {
		width: 100%;
		height: 100%;
	}

	.chromium-auth__container {
		position: relative;
		z-index: 1;
	}

	.chromium-auth__layout {
		display: grid;
		grid-template-columns: minmax(0, 1.1fr) minmax(27rem, 0.9fr);
	}

	.chromium-auth__hero {
		position: relative;
		min-width: 0;
		overflow: hidden;
		background: #070b0e;
	}

	.chromium-auth__hero::after {
		position: absolute;
		inset: 0 -1px 0 auto;
		width: 18%;
		background: linear-gradient(90deg, transparent, var(--chromium-bg));
		content: '';
		pointer-events: none;
	}

	.chromium-auth__hero-image {
		width: 100%;
		height: 100%;
		object-fit: cover;
		object-position: 56% center;
		user-select: none;
		animation: chromium-hero-breathe 16s ease-in-out infinite alternate;
	}

	.chromium-auth__brand {
		position: absolute;
		top: clamp(2.25rem, 5vh, 3.5rem);
		left: clamp(2rem, 4.25vw, 4.5rem);
		display: flex;
		align-items: center;
		gap: 0.9rem;
		z-index: 2;
		color: var(--chromium-text);
		font-size: clamp(1rem, 1.4vw, 1.35rem);
		font-weight: 650;
		letter-spacing: 0.16em;
		line-height: 1;
		text-shadow: 0 2px 18px rgba(0, 0, 0, 0.65);
	}

	.chromium-auth__brand svg {
		width: 2.7rem;
		height: 2.7rem;
		overflow: visible;
		fill: rgba(4, 8, 11, 0.72);
		stroke: var(--chromium-orange-bright);
		stroke-linecap: square;
		stroke-linejoin: bevel;
		stroke-width: 2;
		filter: drop-shadow(0 0 10px rgba(255, 106, 0, 0.2));
	}

	.chromium-auth__brand svg path:nth-child(2) {
		stroke: rgba(230, 240, 244, 0.84);
		stroke-width: 1.35;
	}

	.chromium-auth__brand svg path:nth-child(3) {
		fill: none;
		stroke-width: 2.4;
	}

	.chromium-auth__hero-copy {
		position: absolute;
		left: clamp(2rem, 4.25vw, 4.5rem);
		bottom: clamp(3.5rem, 10vh, 7rem);
		z-index: 2;
		max-width: calc(100% - 6rem);
		text-shadow: 0 3px 24px rgba(0, 0, 0, 0.86);
	}

	.chromium-auth__hero-copy h1 {
		margin: 0;
		font-size: clamp(2.25rem, 4.5vw, 4.85rem);
		font-weight: 320;
		letter-spacing: 0.055em;
		line-height: 0.98;
		white-space: nowrap;
	}

	.chromium-auth__hero-copy p {
		margin: 0.8rem 0 0;
		color: var(--chromium-orange-bright);
		font-size: clamp(0.82rem, 1.55vw, 1.35rem);
		font-weight: 500;
		letter-spacing: 0.08em;
		line-height: 1.2;
	}

	.chromium-auth__form-region {
		display: flex;
		align-items: center;
		justify-content: center;
		min-width: 0;
		padding: 1.6rem clamp(1rem, 2.2vw, 2.2rem) 1.6rem 0.6rem;
		background: var(--chromium-bg);
	}

	.chromium-auth__form-frame {
		position: relative;
		width: 100%;
		max-width: 43rem;
		height: calc(100dvh - 3.2rem);
		max-height: 59rem;
		overflow: hidden;
		clip-path: polygon(
			2.25rem 0,
			calc(100% - 1.35rem) 0,
			100% 1.35rem,
			100% calc(100% - 2.25rem),
			calc(100% - 2.25rem) 100%,
			1.35rem 100%,
			0 calc(100% - 1.35rem),
			0 2.25rem
		);
		background: linear-gradient(
			145deg,
			rgba(196, 210, 219, 0.62),
			rgba(72, 88, 101, 0.54) 40%,
			rgba(255, 106, 0, 0.86) 72%,
			rgba(91, 111, 124, 0.45)
		);
		box-shadow: 0 28px 75px rgba(0, 0, 0, 0.42);
		animation: chromium-panel-in 620ms cubic-bezier(0.2, 0.8, 0.2, 1) both;
	}

	.chromium-auth__form-frame::before {
		position: absolute;
		inset: 1px;
		z-index: 0;
		clip-path: inherit;
		background:
			linear-gradient(180deg, rgba(19, 27, 34, 0.98), rgba(8, 14, 18, 0.99)), var(--chromium-panel);
		content: '';
	}

	.chromium-auth__form-frame::after {
		position: absolute;
		top: 40%;
		right: 0;
		z-index: 2;
		width: 2px;
		height: 25%;
		background: linear-gradient(transparent, var(--chromium-orange), transparent);
		box-shadow: 0 0 12px rgba(255, 106, 0, 0.38);
		content: '';
		pointer-events: none;
	}

	.chromium-auth__circuit {
		position: absolute;
		z-index: 2;
		width: 10rem;
		height: auto;
		fill: none;
		stroke: rgba(39, 221, 245, 0.55);
		stroke-linecap: square;
		stroke-linejoin: miter;
		stroke-width: 1.2;
		pointer-events: none;
	}

	.chromium-auth__circuit circle {
		fill: var(--chromium-cyan);
		stroke: none;
	}

	.chromium-auth__circuit--top {
		top: 1.1rem;
		right: 0.7rem;
		opacity: 0.72;
	}

	.chromium-auth__form-scroll {
		position: relative;
		z-index: 1;
		display: flex;
		flex-direction: column;
		height: 100%;
		overflow: auto;
		padding: clamp(4.25rem, 9.5vh, 6.75rem) clamp(2.15rem, 3.25vw, 3.25rem) 2.35rem;
		scrollbar-color: rgba(39, 221, 245, 0.3) transparent;
		scrollbar-width: thin;
	}

	.chromium-auth__form-content,
	.chromium-auth__signing-in {
		display: flex;
		flex: 1 0 auto;
		flex-direction: column;
		justify-content: center;
		width: 100%;
	}

	.chromium-auth__signing-in-content {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.85rem;
		color: var(--chromium-text);
		font-size: clamp(1.2rem, 2vw, 1.65rem);
		font-weight: 500;
		text-align: center;
	}

	.chromium-auth__card {
		width: 100%;
		max-width: 33rem;
		margin: auto;
		color: var(--chromium-text);
		text-align: left;
	}

	.chromium-auth__card--onboarding {
		transform: translateY(-1.5rem);
	}

	.chromium-auth__custom-logo {
		display: flex;
		justify-content: center;
		margin-bottom: 1.5rem;
	}

	.chromium-auth__custom-logo-image {
		width: 4rem;
		height: 4rem;
		border: 1px solid rgba(39, 221, 245, 0.35);
		border-radius: 1rem;
		box-shadow: 0 0 30px rgba(39, 221, 245, 0.1);
	}

	.chromium-auth__form {
		display: flex;
		flex-direction: column;
	}

	.chromium-auth__heading h2 {
		margin: 0;
		color: var(--chromium-text);
		font-size: clamp(1.9rem, 2.5vw, 2.25rem);
		font-weight: 650;
		letter-spacing: -0.035em;
		line-height: 1.12;
	}

	.chromium-auth__heading p {
		margin: 0.9rem 0 0;
		color: var(--chromium-muted);
		font-size: 0.95rem;
		font-weight: 400;
		line-height: 1.55;
	}

	.chromium-auth__fields {
		display: flex;
		flex-direction: column;
		gap: 2.55rem;
		margin-top: 2.4rem;
	}

	.chromium-auth__field {
		display: flex;
		flex-direction: column;
		gap: 0.55rem;
	}

	.chromium-auth__label {
		display: block;
		color: #f2f5f7;
		font-size: 0.9rem;
		font-weight: 520;
		letter-spacing: 0.01em;
		line-height: 1.25;
	}

	.chromium-auth__input,
	:global(.chromium-auth__sensitive-shell) {
		width: 100%;
		height: 3.5rem;
		border: 1px solid var(--chromium-border);
		border-radius: 0.65rem;
		background: linear-gradient(180deg, rgba(27, 37, 46, 0.96), rgba(20, 28, 35, 0.96));
		box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.025);
		transition:
			border-color 180ms ease,
			box-shadow 180ms ease,
			background-color 180ms ease;
	}

	.chromium-auth__input {
		padding: 0 1rem;
		color: var(--chromium-text);
		font-family: inherit;
		font-size: 0.95rem;
		font-weight: 430;
		outline: none;
	}

	.chromium-auth__input::placeholder,
	:global(.chromium-auth__sensitive-input::placeholder) {
		color: #81909f;
		opacity: 1;
	}

	.chromium-auth__input:focus,
	:global(.chromium-auth__sensitive-shell:focus-within) {
		border-color: var(--chromium-cyan);
		background: #17222a;
		box-shadow:
			0 0 0 2px rgba(39, 221, 245, 0.12),
			0 0 24px rgba(39, 221, 245, 0.08),
			inset 0 1px 0 rgba(255, 255, 255, 0.03);
	}

	:global(.chromium-auth__sensitive-shell) {
		display: flex;
		align-items: center;
		padding: 0 0.9rem 0 1rem;
	}

	:global(.chromium-auth__sensitive-input) {
		min-width: 0;
		flex: 1;
		padding: 0 !important;
		color: var(--chromium-text);
		font-family: inherit;
		font-size: 0.95rem !important;
		font-weight: 430;
		outline: none;
	}

	:global(.chromium-auth__sensitive-toggle) {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 2.2rem;
		height: 2.2rem;
		padding: 0 !important;
		border-radius: 0.45rem;
		color: #c8d3da;
		outline: none;
		transition:
			color 160ms ease,
			background-color 160ms ease;
	}

	:global(.chromium-auth__sensitive-toggle:hover) {
		background: rgba(39, 221, 245, 0.08);
		color: var(--chromium-cyan);
	}

	:global(.chromium-auth__sensitive-toggle:focus-visible) {
		box-shadow: 0 0 0 2px var(--chromium-cyan);
	}

	.chromium-auth__actions {
		margin-top: 2.25rem;
	}

	.chromium-auth__submit {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 100%;
		min-height: 3.55rem;
		padding: 0.85rem 1.25rem;
		border: 1px solid var(--chromium-orange-bright);
		border-radius: 0.65rem;
		background: linear-gradient(180deg, #ff8615, #e95600);
		box-shadow:
			inset 0 1px 0 rgba(255, 255, 255, 0.3),
			0 14px 30px rgba(174, 55, 0, 0.2);
		color: white;
		font-family: inherit;
		font-size: 0.95rem;
		font-weight: 680;
		letter-spacing: 0.005em;
		line-height: 1.2;
		outline: none;
		transition:
			transform 180ms ease,
			filter 180ms ease,
			box-shadow 180ms ease;
	}

	.chromium-auth__submit:hover:not(:disabled) {
		filter: brightness(1.08) saturate(1.06);
		transform: translateY(-1px);
		box-shadow:
			inset 0 1px 0 rgba(255, 255, 255, 0.32),
			0 16px 34px rgba(255, 91, 0, 0.27);
	}

	.chromium-auth__submit:active:not(:disabled) {
		transform: translateY(0);
	}

	.chromium-auth__submit:focus-visible {
		box-shadow:
			0 0 0 2px var(--chromium-panel-deep),
			0 0 0 4px var(--chromium-cyan),
			0 16px 34px rgba(255, 91, 0, 0.24);
	}

	.chromium-auth__submit:disabled {
		cursor: wait;
		opacity: 0.58;
	}

	.chromium-auth__switch-mode,
	.chromium-auth__ldap-switch {
		margin-top: 1rem;
		color: var(--chromium-muted);
		font-size: 0.84rem;
		text-align: center;
	}

	.chromium-auth__text-button {
		padding: 0.2rem;
		color: var(--chromium-cyan);
		font-family: inherit;
		font-size: inherit;
		font-weight: 600;
		text-decoration: none;
		text-underline-offset: 0.2rem;
		outline: none;
	}

	.chromium-auth__text-button:hover {
		text-decoration: underline;
	}

	.chromium-auth__text-button:focus-visible {
		border-radius: 0.25rem;
		box-shadow: 0 0 0 2px var(--chromium-cyan);
	}

	.chromium-auth__divider {
		display: flex;
		align-items: center;
		gap: 0.9rem;
		margin: 1.35rem 0;
	}

	.chromium-auth__divider hr {
		flex: 1;
		height: 1px;
		margin: 0;
		border: 0;
		background: linear-gradient(90deg, transparent, var(--chromium-border-soft));
	}

	.chromium-auth__divider hr:last-child {
		background: linear-gradient(90deg, var(--chromium-border-soft), transparent);
	}

	.chromium-auth__divider-label {
		color: var(--chromium-muted);
		font-size: 0.78rem;
		text-transform: uppercase;
		letter-spacing: 0.12em;
	}

	.chromium-auth__provider-list {
		display: flex;
		flex-direction: column;
		gap: 0.65rem;
	}

	.chromium-auth__provider-button {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 100%;
		min-height: 3.1rem;
		padding: 0.7rem 1rem;
		border: 1px solid var(--chromium-border-soft);
		border-radius: 0.65rem;
		background: rgba(255, 255, 255, 0.025);
		color: #dce4e9;
		font-family: inherit;
		font-size: 0.88rem;
		font-weight: 560;
		outline: none;
		transition:
			border-color 160ms ease,
			background-color 160ms ease,
			color 160ms ease;
	}

	.chromium-auth__provider-button:hover {
		border-color: rgba(39, 221, 245, 0.48);
		background: rgba(39, 221, 245, 0.06);
		color: white;
	}

	.chromium-auth__provider-button:focus-visible {
		box-shadow: 0 0 0 2px var(--chromium-cyan);
	}

	.chromium-auth__privacy-note {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.65rem;
		margin-top: 2rem;
		color: #768797;
		font-size: 0.72rem;
		line-height: 1;
		white-space: nowrap;
	}

	.chromium-auth__privacy-note svg {
		width: 1rem;
		height: 1rem;
		fill: none;
		stroke: currentColor;
		stroke-width: 1.3;
	}

	.chromium-auth__privacy-note b {
		padding: 0 0.35rem;
		color: var(--chromium-cyan);
		font-weight: 700;
	}

	.chromium-auth__privacy-line {
		width: clamp(1.2rem, 3vw, 4rem);
		height: 1px;
		background: linear-gradient(90deg, transparent, rgba(39, 221, 245, 0.72));
	}

	.chromium-auth__privacy-line:last-child {
		background: linear-gradient(90deg, rgba(39, 221, 245, 0.72), transparent);
	}

	.chromium-auth__custom-footer {
		max-width: 33rem;
		margin: 1rem auto 0;
		color: var(--chromium-muted);
		font-size: 0.7rem;
		line-height: 1.45;
		text-align: center;
	}

	.chromium-auth__custom-footer :global(a) {
		color: var(--chromium-cyan);
	}

	.chromium-auth__input:-webkit-autofill,
	.chromium-auth__input:-webkit-autofill:hover,
	.chromium-auth__input:-webkit-autofill:focus,
	:global(.chromium-auth__sensitive-input:-webkit-autofill) {
		box-shadow: 0 0 0 1000px #172029 inset;
		-webkit-text-fill-color: var(--chromium-text);
		caret-color: var(--chromium-text);
	}

	@keyframes chromium-hero-breathe {
		from {
			transform: scale(1.015);
		}

		to {
			transform: scale(1.045);
		}
	}

	@keyframes chromium-panel-in {
		from {
			opacity: 0;
			transform: translateX(1.1rem);
		}

		to {
			opacity: 1;
			transform: translateX(0);
		}
	}

	@media (min-width: 981px) and (max-height: 760px) {
		.chromium-auth__form-region {
			padding-block: 0.85rem;
		}

		.chromium-auth__form-frame {
			height: calc(100dvh - 1.7rem);
		}

		.chromium-auth__form-scroll {
			padding-top: 3.4rem;
			padding-bottom: 1.4rem;
		}

		.chromium-auth__heading h2 {
			font-size: 1.8rem;
		}

		.chromium-auth__heading p {
			margin-top: 0.6rem;
		}

		.chromium-auth__fields {
			gap: 0.7rem;
			margin-top: 1.35rem;
		}

		.chromium-auth__input,
		:global(.chromium-auth__sensitive-shell) {
			height: 3rem;
		}

		.chromium-auth__actions {
			margin-top: 1.25rem;
		}

		.chromium-auth__submit {
			min-height: 3.1rem;
		}

		.chromium-auth__privacy-note {
			margin-top: 1.25rem;
		}
	}

	@media (max-width: 980px) {
		.chromium-auth {
			overflow-y: auto;
		}

		.chromium-auth__container,
		.chromium-auth__layout {
			height: auto;
			min-height: 100dvh;
		}

		.chromium-auth__layout {
			display: block;
		}

		.chromium-auth__hero {
			height: clamp(15rem, 34dvh, 21rem);
		}

		.chromium-auth__hero::after {
			inset: auto 0 -1px;
			width: 100%;
			height: 28%;
			background: linear-gradient(180deg, transparent, var(--chromium-bg));
		}

		.chromium-auth__hero-image {
			object-position: 64% 30%;
		}

		.chromium-auth__brand {
			top: 1.8rem;
			left: 2rem;
		}

		.chromium-auth__hero-copy {
			left: 2rem;
			bottom: 2rem;
		}

		.chromium-auth__hero-copy h1 {
			font-size: clamp(2rem, 7vw, 3.5rem);
		}

		.chromium-auth__form-region {
			padding: 0 1.25rem 1.25rem;
		}

		.chromium-auth__form-frame {
			max-width: 44rem;
			height: auto;
			min-height: 34rem;
		}

		.chromium-auth__form-scroll {
			height: auto;
			overflow: visible;
			padding: 4.5rem clamp(2rem, 9vw, 5rem) 2.25rem;
		}

		.chromium-auth__card--onboarding {
			transform: none;
		}

		.chromium-auth__fields {
			gap: 1.25rem;
			margin-top: 2rem;
		}

		.chromium-auth__actions {
			margin-top: 2rem;
		}
	}

	@media (max-width: 600px) {
		.chromium-auth__hero {
			height: 14.5rem;
		}

		.chromium-auth__brand {
			top: 1.4rem;
			left: 1.25rem;
			gap: 0.65rem;
			font-size: 0.85rem;
		}

		.chromium-auth__brand svg {
			width: 2.15rem;
			height: 2.15rem;
		}

		.chromium-auth__hero-copy {
			left: 1.25rem;
			bottom: 1.35rem;
			max-width: calc(100% - 2.5rem);
		}

		.chromium-auth__hero-copy h1 {
			font-size: clamp(1.5rem, 7.5vw, 2.5rem);
			letter-spacing: 0.035em;
		}

		.chromium-auth__hero-copy p {
			margin-top: 0.5rem;
			font-size: 0.72rem;
		}

		.chromium-auth__form-region {
			padding-inline: 0.65rem;
		}

		.chromium-auth__form-frame {
			clip-path: polygon(
				1.1rem 0,
				calc(100% - 0.7rem) 0,
				100% 0.7rem,
				100% calc(100% - 1.1rem),
				calc(100% - 1.1rem) 100%,
				0.7rem 100%,
				0 calc(100% - 0.7rem),
				0 1.1rem
			);
		}

		.chromium-auth__circuit--top {
			width: 7rem;
			opacity: 0.48;
		}

		.chromium-auth__form-scroll {
			padding: 3.8rem 1.35rem 1.9rem;
		}

		.chromium-auth__heading h2 {
			font-size: 1.7rem;
		}

		.chromium-auth__heading p {
			font-size: 0.88rem;
		}

		.chromium-auth__fields {
			margin-top: 1.75rem;
		}

		.chromium-auth__input,
		:global(.chromium-auth__sensitive-shell) {
			height: 3.3rem;
		}

		.chromium-auth__submit {
			min-height: 3.35rem;
		}

		.chromium-auth__privacy-note {
			gap: 0.45rem;
			font-size: 0.65rem;
		}

		.chromium-auth__privacy-line {
			width: 1rem;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.chromium-auth__hero-image,
		.chromium-auth__form-frame {
			animation: none;
		}

		.chromium-auth__submit {
			transition: none;
		}
	}
</style>
