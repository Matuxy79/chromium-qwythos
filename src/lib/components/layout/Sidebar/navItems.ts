export const MENU_ITEM_META: Record<string, { label: string; href: string; iconType: string }> = {
	notes: { label: 'Notes', href: '/notes', iconType: 'note' },
	workspace: { label: 'Workspace', href: '/workspace', iconType: 'workspace' },
	automations: { label: 'Automations', href: '/automations', iconType: 'automations' },
	calendar: { label: 'Calendar', href: '/calendar', iconType: 'calendar' },
	playground: { label: 'Playground', href: '/playground', iconType: 'playground' }
};

export const getMenuItemMeta = (id: string) => MENU_ITEM_META[id];

export const isMenuItemVisible = (id: string, user: any, config: any): boolean => {
	switch (id) {
		case 'notes':
			return (
				(config?.features?.enable_notes ?? false) &&
				(user?.role === 'admin' || (user?.permissions?.features?.notes ?? true))
			);
		case 'workspace':
			return (
				user?.role === 'admin' ||
				user?.permissions?.workspace?.models ||
				user?.permissions?.workspace?.knowledge ||
				user?.permissions?.workspace?.prompts ||
				user?.permissions?.workspace?.tools ||
				user?.permissions?.workspace?.skills
			);
		case 'automations':
			return (
				config?.features?.enable_automations &&
				(user?.role === 'admin' || user?.permissions?.features?.automations)
			);
		case 'calendar':
			return (
				config?.features?.enable_calendar &&
				(user?.role === 'admin' || user?.permissions?.features?.calendar)
			);
		case 'playground':
			return user?.role === 'admin';
		default:
			return false;
	}
};

const MENU_ITEM_PATH_PREFIXES: Record<string, string> = {
	notes: '/notes',
	workspace: '/workspace',
	calendar: '/calendar',
	automations: '/automations',
	playground: '/playground'
};

export const getActiveMenuItemId = (pathname: string): string | null => {
	for (const [id, pathPrefix] of Object.entries(MENU_ITEM_PATH_PREFIXES)) {
		if (pathname === pathPrefix || pathname.startsWith(`${pathPrefix}/`)) {
			return id;
		}
	}

	return null;
};
