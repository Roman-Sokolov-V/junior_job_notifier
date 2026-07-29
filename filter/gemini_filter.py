import asyncio
import logging
from google.genai import Client
from google.genai import types


from common_settings import GEMINI_API_KEY
from filter.schemas import BatchFilterResponse, LLMCandidate, MatchData

logger = logging.getLogger(__name__)


async def get_matches_for_profile(
    aclient: Client, data: LLMCandidate, model: str
) -> list[MatchData]:
    """Один запит до Gemini для одного профілю."""
    vacancies_payload = [
        {"id": v["id"], "description": v["description_text"]} for v in data.vacancies
    ]
    semantic_scores = {v["id"]: v.get("semantic_score") for v in data.vacancies}

    prompt = f"""You are a filter of IT vacancies. Analyze the list of vacancies and determine
                    which ones correspond to the user's request.
                    USER REQUEST:
                    {data.profile.query_text}            
                    LIST OF VACANCIES FOR EVALUATION:
                    {vacancies_payload}
                    """

    try:
        response = await aclient.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=BatchFilterResponse,
            ),
        )

    except Exception:
        logger.exception("Gemini filter failed for profile_id=%s", data.profile.id)
        return []

    # парсимо відповідь у Pydantic-об'єкт
    batch_result: BatchFilterResponse = response.parsed

    match_list = [
        MatchData(
            user_id=data.profile.user_id,
            profile_id=data.profile.id,
            vacancy_id=eval_item.vacancy_id,
            semantic_score=semantic_scores[eval_item.vacancy_id],
            confidence=eval_item.confidence,
            reason=eval_item.reason,
        )
        for eval_item in batch_result.evaluations
        if eval_item.match
    ]
    return match_list


async def get_matches_list_for_all_profiles(
    list_data: list[LLMCandidate],
    model: str,
) -> list[MatchData]:
    async with Client(api_key=GEMINI_API_KEY).aio as aclient:
        coroutines = [
            get_matches_for_profile(aclient=aclient, data=data, model=model)
            for data in list_data
        ]
        gathered = await asyncio.gather(*coroutines, return_exceptions=False)

    return [match for sublist in gathered for match in sublist]
