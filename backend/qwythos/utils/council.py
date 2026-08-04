"""
LLM Council: 3-stage multi-model deliberation engine.

Stage 1 — every council model answers the question independently (in parallel).
Stage 2 — every council model ranks the anonymized answers; ballots are
          aggregated into an average-position ranking.
Stage 3 — a chairman model synthesizes the final answer from the question,
          the anonymized answers, and the aggregate ranking.

Used by the ``run_llm_council`` built-in tool (qwythos/tools/builtin.py).
"""

import asyncio
import json
import logging
import re
from string import ascii_uppercase
from typing import Any, Callable, Optional

from fastapi import Request

from qwythos.models.config import Config
from qwythos.models.users import UserModel

log = logging.getLogger(__name__)

MAX_COUNCIL_MODELS = 10

STAGE2_RANKING_PROMPT = """You are one judge on an LLM council evaluating anonymized responses to a question.

Question:
{question}

Responses:
{responses}

Rank the responses from best to worst based on accuracy, completeness, and clarity.
Respond ONLY with the ranking, one response per line, best first, in this exact format:
Response A
Response B
...
Do not add any commentary."""

STAGE3_CHAIRMAN_PROMPT = """You are the chairman of an LLM council. Multiple council members answered the \
question below independently, then peer-ranked each other's anonymized answers.

Question:
{question}

Council responses (anonymized):
{responses}

Aggregate peer ranking (best first, by average rank across all judges):
{ranking}

Synthesize a single, comprehensive final answer to the question. Use the ranking \
and the responses' content to resolve disagreements: prefer what the higher-ranked \
responses agree on, but exercise your own judgment. Present the answer directly, \
without mentioning the council process."""


def _extract_content(response: Any) -> Optional[str]:
    """Pull assistant text out of a generate_chat_completion response."""
    if not isinstance(response, dict):
        return None
    choices = response.get('choices') or []
    if not choices or not isinstance(choices[0], dict):
        return None
    message = choices[0].get('message') or {}
    content = message.get('content')
    if isinstance(content, list):
        content = ''.join(
            str(part.get('text', ''))
            for part in content
            if isinstance(part, dict) and part.get('type') == 'text'
        )
    if not isinstance(content, str) or not content.strip():
        return None
    return content.strip()


async def _council_completion(request: Request, user: UserModel, model_id: str, messages: list) -> Optional[str]:
    """Run one non-streaming completion; return text or None on any failure."""
    from qwythos.utils.chat import generate_chat_completion

    try:
        response = await generate_chat_completion(
            request=request,
            form_data={
                'model': model_id,
                'messages': messages,
                'stream': False,
                'metadata': {'task': 'llm_council'},
            },
            user=user,
            bypass_filter=True,
        )
    except Exception as exc:
        log.warning(f'LLM council: completion failed for model {model_id}: {exc}')
        return None
    content = _extract_content(response)
    if content is None:
        log.warning(f'LLM council: no usable response from model {model_id}: {type(response).__name__}')
    return content


async def _emit_status(event_emitter: Optional[Callable], description: str, done: bool = False) -> None:
    if not callable(event_emitter):
        return
    try:
        await event_emitter({'type': 'status', 'data': {'description': description, 'done': done}})
    except Exception as exc:
        log.debug(f'LLM council: error emitting status: {exc}')


def _parse_ranking(text: str, labels: list[str]) -> Optional[list[str]]:
    """Parse a stage-2 ballot into an ordered list of labels, best first.

    Returns None when the ballot is unusable (no valid labels found).
    Missing labels are appended at the end in canonical order so every
    response still gets a position.
    """
    found: list[str] = []
    for match in re.finditer(r'Response\s+([A-Z])\b', text or ''):
        label = match.group(1)
        if label in labels and label not in found:
            found.append(label)
    if not found:
        return None
    return found + [label for label in labels if label not in found]


async def run_council(
    question: str,
    models: str = '',
    chairman_model: str = '',
    *,
    request: Request,
    user_data: dict,
    event_emitter: Optional[Callable] = None,
) -> str:
    """Run the 3-stage LLM council deliberation and return the chairman's answer."""
    if getattr(request.state, 'internal', False) is True:
        return 'Error: the LLM council cannot be convened from a sub-agent.'

    question = (question or '').strip()
    if not question:
        return 'Error: question must not be empty.'

    config = await Config.get_many('council.models', 'council.chairman_model')

    raw_models = (models or '').strip() or str(config.get('council.models') or '')
    council_models = [m.strip() for m in raw_models.split(',') if m.strip()]
    # De-duplicate while preserving order
    council_models = list(dict.fromkeys(council_models))

    if not council_models:
        return (
            'Error: no council models configured. Pass the "models" parameter '
            '(comma-separated model IDs) or set council.models in the config.'
        )
    if len(council_models) > MAX_COUNCIL_MODELS:
        return f'Error: too many council models ({len(council_models)}); maximum is {MAX_COUNCIL_MODELS}.'
    if len(council_models) < 2:
        return 'Error: the council needs at least 2 models.'

    available_models = getattr(request.app.state, 'MODELS', {}) or {}
    unknown = [m for m in council_models if m not in available_models]
    if unknown:
        log.warning(f'LLM council: unknown model IDs ignored: {unknown}')
        council_models = [m for m in council_models if m in available_models]
        if len(council_models) < 2:
            return f'Error: fewer than 2 valid council models after filtering unknown IDs: {unknown}'

    chairman = (chairman_model or '').strip() or str(config.get('council.chairman_model') or '').strip()
    if chairman and chairman not in available_models:
        log.warning(f'LLM council: unknown chairman model {chairman}; falling back')
        chairman = ''
    if not chairman:
        chairman = council_models[0]

    user = UserModel(**user_data) if isinstance(user_data, dict) else user_data

    labels = list(ascii_uppercase[: len(council_models)])

    # ------------------------------------------------------------------
    # Stage 1 — individual responses (parallel)
    # ------------------------------------------------------------------
    await _emit_status(
        event_emitter,
        f'LLM Council stage 1/3: collecting answers from {len(council_models)} models…',
    )
    stage1_results = await asyncio.gather(
        *(
            _council_completion(request, user, model_id, [{'role': 'user', 'content': question}])
            for model_id in council_models
        )
    )

    responses: dict[str, str] = {}  # label -> answer text
    answerers: dict[str, str] = {}  # label -> model_id
    failed_models: list[str] = []
    for label, model_id, text in zip(labels, council_models, stage1_results):
        if text:
            responses[label] = text
            answerers[label] = model_id
        else:
            failed_models.append(model_id)

    if len(responses) < 2:
        return (
            'Error: the council could not proceed — fewer than 2 models produced an answer. '
            f'Failed models: {", ".join(failed_models) or "unknown"}.'
        )

    active_labels = [label for label in labels if label in responses]
    anonymized = '\n\n'.join(f'Response {label}:\n{responses[label]}' for label in active_labels)

    # ------------------------------------------------------------------
    # Stage 2 — peer ranking (parallel, anonymized)
    # ------------------------------------------------------------------
    await _emit_status(event_emitter, 'LLM Council stage 2/3: peer ranking of anonymized answers…')
    ranking_prompt = STAGE2_RANKING_PROMPT.format(question=question, responses=anonymized)
    ballots = await asyncio.gather(
        *(
            _council_completion(request, user, model_id, [{'role': 'user', 'content': ranking_prompt}])
            for model_id in council_models
        )
    )

    # Aggregate: average position across valid ballots (lower = better)
    position_sums = {label: 0.0 for label in active_labels}
    ballot_count = 0
    for ballot_text in ballots:
        if not ballot_text:
            continue
        ranking = _parse_ranking(ballot_text, active_labels)
        if ranking is None:
            continue
        ballot_count += 1
        for position, label in enumerate(ranking):
            position_sums[label] += position

    if ballot_count:
        aggregate = sorted(active_labels, key=lambda label: position_sums[label] / ballot_count)
    else:
        log.warning('LLM council: no parseable stage-2 ballots; ranking falls back to council order')
        aggregate = list(active_labels)

    ranking_lines = [
        f'{i + 1}. Response {label} (avg rank {position_sums[label] / ballot_count:.2f})'
        if ballot_count
        else f'{i + 1}. Response {label}'
        for i, label in enumerate(aggregate)
    ]
    ranking_summary = '\n'.join(ranking_lines)

    # ------------------------------------------------------------------
    # Stage 3 — chairman synthesis
    # ------------------------------------------------------------------
    await _emit_status(event_emitter, f'LLM Council stage 3/3: chairman synthesis ({chairman})…')
    chairman_prompt = STAGE3_CHAIRMAN_PROMPT.format(
        question=question,
        responses=anonymized,
        ranking=ranking_summary,
    )
    final_answer = await _council_completion(request, user, chairman, [{'role': 'user', 'content': chairman_prompt}])

    if not final_answer:
        # Fall back to the best-ranked council answer rather than failing outright
        final_answer = responses[aggregate[0]]
        log.warning('LLM council: chairman synthesis failed; returning top-ranked response')

    await _emit_status(event_emitter, 'LLM Council: deliberation complete', done=True)

    deanon = {f'Response {label}': answerers[label] for label in active_labels}
    parts = [
        final_answer,
        '---',
        'Council deliberation summary:',
        f'Models: {", ".join(answerers[label] for label in active_labels)}'
        + (f' (failed: {", ".join(failed_models)})' if failed_models else ''),
        f'Chairman: {chairman}',
        f'Aggregate ranking: {ranking_summary}',
        f'Anonymization key: {json.dumps(deanon, ensure_ascii=False)}',
    ]
    return '\n\n'.join(parts)
