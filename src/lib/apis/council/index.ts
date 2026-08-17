import { WEBUI_API_BASE_URL } from '$lib/constants';

export type CouncilRunConfig = {
	enabled: boolean;
	models: string[];
	chairman_model: string;
};

export type CouncilResponseItem = {
	model: string;
	answer: string;
};

export type CouncilRankingItem = {
	model: string;
	rank: number;
	avg_rank: number | null;
};

export type CouncilRunResult = {
	question: string;
	chairman: string;
	final_answer: string;
	council_models: string[];
	failed_models: string[];
	responses: CouncilResponseItem[];
	ranking: CouncilRankingItem[];
};

export const getCouncilRunConfig = async (token: string): Promise<CouncilRunConfig> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/council/config`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});
	if (!res.ok) throw await res.json();
	return res.json();
};

export const runCouncil = async (token: string, question: string): Promise<CouncilRunResult> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/council/run`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ question })
	});
	if (!res.ok) throw await res.json();
	return res.json();
};
