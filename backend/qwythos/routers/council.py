from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from qwythos.constants import ERROR_MESSAGES
from qwythos.models.config import Config
from qwythos.utils.auth import get_verified_user
from qwythos.utils.council import run_council_pipeline

router = APIRouter()


async def _check_council_access() -> None:
    if not await Config.get('council.enable'):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)


class CouncilRunForm(BaseModel):
    question: str


class CouncilResponseItem(BaseModel):
    model: str
    answer: str


class CouncilRankingItem(BaseModel):
    model: str
    rank: int
    avg_rank: float | None = None


class CouncilRunResult(BaseModel):
    question: str
    chairman: str
    final_answer: str
    council_models: list[str]
    failed_models: list[str]
    responses: list[CouncilResponseItem]
    ranking: list[CouncilRankingItem]


@router.get('/config')
async def get_council_run_config(user=Depends(get_verified_user)):
    """Whatever a chat-facing 'ask the council' surface needs to know before showing itself."""
    values = await Config.get_many('council.enable', 'council.models', 'council.chairman_model')
    model_ids = [m.strip() for m in str(values.get('council.models') or '').split(',') if m.strip()]
    return {
        'enabled': bool(values.get('council.enable')) and len(model_ids) >= 2,
        'models': model_ids,
        'chairman_model': values.get('council.chairman_model') or (model_ids[0] if model_ids else ''),
    }


@router.post('/run', response_model=CouncilRunResult)
async def run_council_endpoint(request: Request, form_data: CouncilRunForm, user=Depends(get_verified_user)):
    await _check_council_access()

    question = (form_data.question or '').strip()
    if not question:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Question must not be empty.')

    result = await run_council_pipeline(
        question,
        request=request,
        user_data=user,
    )
    if result.get('error'):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result['error'])

    return {
        'question': result['question'],
        'chairman': result['chairman'],
        'final_answer': result['final_answer'],
        'council_models': [item['model'] for item in result['responses']],
        'failed_models': result['failed_models'],
        'responses': result['responses'],
        'ranking': result['ranking'],
    }
