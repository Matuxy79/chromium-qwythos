"""
LLM Council: 3-stage multi-model deliberation engine.

Stage 1 — every council model answers the question independently (in parallel).
Stage 2 — every council model ranks the anonymized answers; ballots are
          aggregated into an average-position ranking.
Stage 3 — a chairman model synthesizes the final answer from the question,
          the anonymized answers, and the aggregate ranking.

Used by the ``run_llm_council`` built-in tool (qwythos/tools/builtin.py) and by
the ``/api/v1/council/run`` endpoint (qwythos/routers/council.py), both of which
call ``run_council_pipeline`` and adapt its structured result to their own
response shape.
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
from qwythos.utils.misc import (
    get_last_user_message,
    openai_chat_completion_message_template,
)

log = logging.getLogger(__name__)

MAX_COUNCIL_MODELS = 10
MAX_COUNCIL_TOOL_ITERATIONS = 8
COUNCIL_BLOCKED_TOOLS = frozenset({'run_llm_council'})

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


def _message_from_completion(response: Any) -> Optional[dict]:
    if not isinstance(response, dict):
        return None
    choices = response.get('choices') or []
    if not choices or not isinstance(choices[0], dict):
        return None
    message = choices[0].get('message')
    return message if isinstance(message, dict) else None


def _filter_tool_specs(tools: Optional[list]) -> list:
    if not tools:
        return []
    filtered = []
    for spec in tools:
        if not isinstance(spec, dict):
            continue
        name = (spec.get('function') or {}).get('name') or spec.get('name')
        if name in COUNCIL_BLOCKED_TOOLS:
            continue
        filtered.append(spec)
    return filtered


async def _execute_tool_call(tool_call: dict, tools_dict: dict, messages: list, files: list) -> str:
    """Run one OpenAI-style tool call against the already-resolved tools_dict."""
    from qwythos.utils.tools import get_updated_tool_function

    function = tool_call.get('function') or {}
    name = function.get('name') or ''
    if name in COUNCIL_BLOCKED_TOOLS:
        return f'Error: tool "{name}" is not available during council deliberation.'

    tool = tools_dict.get(name)
    if not tool:
        return f'Error: Tool "{name}" not found.'
    if tool.get('direct'):
        return f'Error: client-side tool "{name}" is not available during council deliberation.'

    raw_args = function.get('arguments') or '{}'
    try:
        params = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args or {})
    except Exception:
        return f'Error: could not parse arguments for "{name}".'

    spec = tool.get('spec') or {}
    allowed = (spec.get('parameters') or {}).get('properties') or {}
    if allowed:
        params = {key: value for key, value in params.items() if key in allowed}

    callable_fn = tool.get('callable')
    if not callable(callable_fn):
        return f'Error: tool "{name}" has no callable.'

    try:
        function_to_run = await get_updated_tool_function(
            function=callable_fn,
            extra_params={'__messages__': messages, '__files__': files},
        )
        result = await function_to_run(**params)
    except Exception as exc:
        return f'Error running {name}: {exc}'

    if isinstance(result, str):
        return result
    try:
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception:
        return str(result)


async def _council_completion(
    request: Request,
    user: UserModel,
    model_id: str,
    messages: list,
    *,
    tools: Optional[list] = None,
    tools_dict: Optional[dict] = None,
    files: Optional[list] = None,
) -> Optional[str]:
    """Run one non-streaming completion; return text or None on any failure.

    When ``tools``/``tools_dict`` are supplied (chat-path council), stage-1
    members can call the same builtins the parent chat resolved — web search,
    files, knowledge, etc. Ranking and chairman synthesis stay text-only.
    """
    from qwythos.utils.chat import generate_chat_completion

    current_messages = list(messages)
    tool_specs = _filter_tool_specs(tools)
    resolved_tools = {
        name: tool for name, tool in (tools_dict or {}).items() if name not in COUNCIL_BLOCKED_TOOLS
    }
    use_tools = bool(tool_specs and resolved_tools)
    files = files or []
    content: Optional[str] = None

    for _ in range((MAX_COUNCIL_TOOL_ITERATIONS if use_tools else 0) + 1):
        form_data: dict[str, Any] = {
            'model': model_id,
            'messages': current_messages,
            'stream': False,
            'metadata': {'task': 'llm_council'},
        }
        if use_tools:
            form_data['tools'] = tool_specs

        try:
            response = await generate_chat_completion(
                request=request,
                form_data=form_data,
                user=user,
                bypass_filter=True,
            )
        except Exception as exc:
            log.warning(f'LLM council: completion failed for model {model_id}: {exc}')
            return None

        if not isinstance(response, dict):
            log.warning(
                f'LLM council: no usable response from model {model_id}: {type(response).__name__}'
            )
            return None

        message = _message_from_completion(response)
        if message is None:
            log.warning(f'LLM council: no usable response from model {model_id}: {type(response).__name__}')
            return None

        tool_calls = message.get('tool_calls') or []
        content = _extract_content(response)
        if not tool_calls or not use_tools:
            return content

        current_messages.append(message)
        for tool_call in tool_calls:
            if not isinstance(tool_call, dict):
                continue
            result = await _execute_tool_call(tool_call, resolved_tools, current_messages, files)
            current_messages.append(
                {
                    'role': 'tool',
                    'tool_call_id': tool_call.get('id') or '',
                    'content': result,
                }
            )

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


async def run_council_pipeline(
    question: str,
    models: str = '',
    chairman_model: str = '',
    *,
    request: Request,
    user_data: dict,
    event_emitter: Optional[Callable] = None,
    messages: Optional[list] = None,
    tools: Optional[list] = None,
    tools_dict: Optional[dict] = None,
    files: Optional[list] = None,
) -> dict:
    """Run the 3-stage LLM council deliberation and return structured results.

    Always returns a dict with an ``error`` key (``None`` on success) and a
    ``text`` key holding the same flattened-string rendering the ``run_llm_council``
    tool has always returned, so callers that only need that string (the tool
    wrapper) and callers that need structured data (the council API endpoint)
    share one code path.

    ``messages``/``tools``/``tools_dict`` are used by the chat-model path so
    stage 1 sees conversation history and can call the parent chat's builtins.
    Ranking and chairman synthesis stay text-only.
    """
    if getattr(request.state, 'internal', False) is True:
        error = 'Error: the LLM council cannot be convened from a sub-agent.'
        return {'error': error, 'text': error}

    question = (question or '').strip()
    if not question and not messages:
        error = 'Error: question must not be empty.'
        return {'error': error, 'text': error}
    if not question:
        question = '(see conversation history)'

    config = await Config.get_many('council.models', 'council.chairman_model')

    raw_models = (models or '').strip() or str(config.get('council.models') or '')
    council_models = [m.strip() for m in raw_models.split(',') if m.strip()]
    # De-duplicate while preserving order
    council_models = list(dict.fromkeys(council_models))

    if not council_models:
        error = (
            'Error: no council models configured. Pass the "models" parameter '
            '(comma-separated model IDs) or set council.models in the config.'
        )
        return {'error': error, 'text': error}
    if len(council_models) > MAX_COUNCIL_MODELS:
        error = f'Error: too many council models ({len(council_models)}); maximum is {MAX_COUNCIL_MODELS}.'
        return {'error': error, 'text': error}
    if len(council_models) < 2:
        error = 'Error: the council needs at least 2 models.'
        return {'error': error, 'text': error}

    available_models = getattr(request.app.state, 'MODELS', {}) or {}
    unknown = [m for m in council_models if m not in available_models]
    if unknown:
        log.warning(f'LLM council: unknown model IDs ignored: {unknown}')
        council_models = [m for m in council_models if m in available_models]
        if len(council_models) < 2:
            error = f'Error: fewer than 2 valid council models after filtering unknown IDs: {unknown}'
            return {'error': error, 'text': error}

    # Never seat the council wrapper on itself.
    council_models = [
        model_id
        for model_id in council_models
        if not (available_models.get(model_id) or {}).get('council')
        and (available_models.get(model_id) or {}).get('owned_by') != 'council'
    ]
    if len(council_models) < 2:
        error = 'Error: fewer than 2 valid council models after excluding the council wrapper.'
        return {'error': error, 'text': error}

    chairman = (chairman_model or '').strip() or str(config.get('council.chairman_model') or '').strip()
    chairman_entry = available_models.get(chairman) or {}
    if chairman and (
        chairman not in available_models
        or chairman_entry.get('council')
        or chairman_entry.get('owned_by') == 'council'
    ):
        log.warning(f'LLM council: unknown chairman model {chairman}; falling back')
        chairman = ''
    if not chairman:
        chairman = council_models[0]

    user = UserModel(**user_data) if isinstance(user_data, dict) else user_data

    labels = list(ascii_uppercase[: len(council_models)])
    stage1_messages = messages if messages else [{'role': 'user', 'content': question}]

    # ------------------------------------------------------------------
    # Stage 1 — individual responses (parallel)
    # ------------------------------------------------------------------
    await _emit_status(
        event_emitter,
        f'LLM Council stage 1/3: collecting answers from {len(council_models)} models…',
    )
    stage1_results = await asyncio.gather(
        *(
            _council_completion(
                request,
                user,
                model_id,
                stage1_messages,
                tools=tools,
                tools_dict=tools_dict,
                files=files,
            )
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
        error = (
            'Error: the council could not proceed — fewer than 2 models produced an answer. '
            f'Failed models: {", ".join(failed_models) or "unknown"}.'
        )
        return {'error': error, 'text': error}

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
    text_parts = [
        final_answer,
        '---',
        'Council deliberation summary:',
        f'Models: {", ".join(answerers[label] for label in active_labels)}'
        + (f' (failed: {", ".join(failed_models)})' if failed_models else ''),
        f'Chairman: {chairman}',
        f'Aggregate ranking: {ranking_summary}',
        f'Anonymization key: {json.dumps(deanon, ensure_ascii=False)}',
    ]

    return {
        'error': None,
        'text': '\n\n'.join(text_parts),
        'question': question,
        'chairman': chairman,
        'final_answer': final_answer,
        'failed_models': failed_models,
        'responses': [
            {'model': answerers[label], 'answer': responses[label]} for label in active_labels
        ],
        'ranking': [
            {
                'model': answerers[label],
                'rank': i + 1,
                'avg_rank': round(position_sums[label] / ballot_count, 2) if ballot_count else None,
            }
            for i, label in enumerate(aggregate)
        ],
    }


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
    result = await run_council_pipeline(
        question,
        models,
        chairman_model,
        request=request,
        user_data=user_data,
        event_emitter=event_emitter,
    )
    return result['text']


def _format_chat_answer(result: dict) -> str:
    """Chairman synthesis plus a collapsible deliberation appendix for chat."""
    final = result.get('final_answer') or result.get('text') or ''
    ranking = result.get('ranking') or []
    responses = {item['model']: item['answer'] for item in result.get('responses') or []}
    chairman = result.get('chairman') or ''
    if not ranking:
        return final

    lines = [
        final,
        '',
        '<details>',
        '<summary>Council deliberation</summary>',
        '',
        f'Chairman: {chairman}',
        '',
    ]
    for item in ranking:
        model_id = item.get('model') or ''
        rank = item.get('rank')
        answer = responses.get(model_id, '')
        lines.append(f'### {rank}. {model_id}')
        lines.append('')
        lines.append(answer)
        lines.append('')
    failed = result.get('failed_models') or []
    if failed:
        lines.append(f'Did not respond: {", ".join(failed)}')
        lines.append('')
    lines.append('</details>')
    return '\n'.join(lines)


async def generate_council_chat_completion(request: Request, form_data: dict, user: UserModel, model: dict):
    """Chat-model entry point: run the council pipeline and return an OpenAI completion.

    Background tasks (title/tags/follow-up) resolve to the chairman instead of
    running the full 3-stage deliberation.
    """
    from qwythos.socket.main import get_event_emitter
    from qwythos.utils.chat import generate_chat_completion

    metadata = form_data.get('metadata') or {}
    task = metadata.get('task')
    meta = (model.get('info') or {}).get('meta') or {}
    chairman = meta.get('chairman_model') or ''
    if not chairman:
        roster = meta.get('model_ids') or []
        chairman = roster[0] if roster else ''

    if task and task != 'llm_council' and chairman:
        form_data = {**form_data, 'model': chairman}
        return await generate_chat_completion(
            request,
            form_data,
            user,
            bypass_filter=True,
        )

    messages = form_data.get('messages') or []
    question = (get_last_user_message(messages) or '').strip()
    event_emitter = None
    if all(k in metadata for k in ('session_id', 'chat_id', 'message_id')):
        event_emitter = await get_event_emitter(metadata)

    result = await run_council_pipeline(
        question,
        request=request,
        user_data=user,
        event_emitter=event_emitter,
        messages=messages or None,
        tools=form_data.get('tools'),
        tools_dict=metadata.get('tools'),
        files=metadata.get('files'),
    )
    if result.get('error'):
        raise Exception(result['error'])

    content = _format_chat_answer(result)
    return openai_chat_completion_message_template(form_data.get('model') or model.get('id'), content)
