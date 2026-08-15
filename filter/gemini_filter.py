import asyncio
import logging

from google.genai import Client
from google.genai import types
from supabase import AsyncClient

from db.supabase_client import get_async_supabase_client
from project_config import GEMINI_API_KEY
from filter.schemas import BatchFilterResponse, LLMCandidate, MatchData, Profile
from storage.crud import get_file_url, download_file_bytes
from project_config import SUPABASE_URL

logger = logging.getLogger(__name__)


async def get_prompt_contents(
    a_supabase: AsyncClient, vacancies_payload: list[dict], profile_data: Profile
) -> list:
    if profile_data.cv_file and profile_data.mime_type:
        if SUPABASE_URL == "http://127.0.0.1:54321":
            file_bytes = await download_file_bytes(
                a_supabase=a_supabase, full_path=profile_data.cv_file
            )
            return [
                f"""You filter IT vacancies. Analyze the list of vacancies and determine,
                which of them correspond to the user's request and CV.

                USER REQUEST:
                {profile_data.query_text}

                The user's CV is provided below.""",
                # 💡 Передаємо байти файлу замість віддаленого URL
                types.Part.from_bytes(
                    data=file_bytes,
                    mime_type=profile_data.mime_type,
                ),
                f"""LIST OF VACANCIES FOR EVALUATION:
                                {vacancies_payload}""",
            ]
        else:
            # Повертаємо СПИСОК із текстових блоків та об'єкта Part
            file_uri = await get_file_url(
                a_supabase=a_supabase, full_path=profile_data.cv_file
            )
            if file_uri:
                return [
                    f"""You filter IT vacancies. Analyze the list of vacancies and determine,
                    which of them correspond to the user's request and CV.
    
                    USER REQUEST:
                    {profile_data.query_text}
    
                    The user's CV is provided by the file below.""",
                    # We pass the Part object as the OCTH element of the list!
                    types.Part.from_uri(
                        file_uri=file_uri,
                        mime_type=profile_data.mime_type,
                    ),
                    f"""LIST OF VACANCIES FOR EVALUATION:
                    {vacancies_payload}""",
                ]
            logger.warning(
                "getting file_uri failed, start create prompt content without CV file-----------"
            )

    return [
        f"""You filter IT vacancies. Analyze the list of vacancies and determine,
        which ones correspond to the user's request.
        
        USER REQUEST:
        {profile_data.query_text}
        
        LIST OF VACANCIES FOR ASSESSMENT:
        {vacancies_payload}"""
    ]


async def get_response(gemini_client: Client, model: str, contents):
    return await gemini_client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=BatchFilterResponse,
        ),
    )


async def get_matches_for_profile(
    gemini_client: Client, a_supabase: AsyncClient, data: LLMCandidate, model: str
) -> list[MatchData]:
    """Один запит до Gemini для одного профілю."""
    vacancies_payload = [
        {"id": v["id"], "description": v["description_text"]} for v in data.vacancies
    ]
    semantic_scores = {v["id"]: v.get("semantic_score") for v in data.vacancies}

    contents = await get_prompt_contents(
        a_supabase=a_supabase,
        profile_data=data.profile_data,
        vacancies_payload=vacancies_payload,
    )

    try:
        response = await get_response(
            gemini_client=gemini_client, model=model, contents=contents
        )

    except Exception:
        logger.exception("Gemini filter failed for profile_id=%s", data.profile_data.id)
        return []

    # парсимо відповідь у Pydantic-об'єкт
    batch_result: BatchFilterResponse = response.parsed

    match_list = [
        MatchData(
            user_id=data.profile_data.user_id,
            profile_id=data.profile_data.id,
            vacancy_id=eval_item.vacancy_id,
            semantic_score=semantic_scores.get(eval_item.vacancy_id, None),
            confidence=eval_item.confidence,
            reason=eval_item.reason,
        )
        for eval_item in batch_result.evaluations
        if eval_item.match
    ]
    if not match_list:
        not_match_list = [
            MatchData(
                user_id=data.profile_data.user_id,
                profile_id=data.profile_data.id,
                vacancy_id=eval_item.vacancy_id,
                semantic_score=semantic_scores.get(eval_item.vacancy_id, None),
                confidence=eval_item.confidence,
                reason=eval_item.reason,
            )
            for eval_item in batch_result.evaluations
        ]
        best_not_matched = sorted(
            not_match_list, key=lambda item: item.confidence, reverse=True
        )
        print(best_not_matched[:5])
    return match_list


# async def get_matches_list_for_all_profiles(
#     list_data: list[LLMCandidate],
#     model: str,
# ) -> list[MatchData]:
#     a_supabase = await get_async_supabase_client()
#     async with Client(api_key=GEMINI_API_KEY).aio as gemini_client:
#         coroutines = [
#             get_matches_for_profile(
#                 gemini_client=gemini_client,
#                 a_supabase=a_supabase,
#                 data=data,
#                 model=model,
#             )
#             for data in list_data
#         ]
#         gathered = await asyncio.gather(*coroutines, return_exceptions=False)
#
#     return [match for sublist in gathered for match in sublist]

SEMAPHORE = asyncio.Semaphore(5) # Обмежуємо кількість одночасних запитів до Gemini


async def get_matches_list_for_all_profiles(
        list_data: list[LLMCandidate],
        model: str,
) -> list[MatchData]:
    a_supabase = await get_async_supabase_client()

    async with Client(api_key=GEMINI_API_KEY).aio as gemini_client:
        # Внутрішня функція-обгортка, яка застосовує семафор до кожного запиту
        async def fetch_with_semaphore(data: LLMCandidate):
            async with SEMAPHORE:
                await asyncio.sleep(0.5)  # Невелика пауза між запитами
                return await get_matches_for_profile(
                    gemini_client=gemini_client,
                    a_supabase=a_supabase,
                    data=data,
                    model=model,
                )

        coroutines = [fetch_with_semaphore(data) for data in list_data]
        gathered = await asyncio.gather(*coroutines, return_exceptions=False)

    return [match for sublist in gathered for match in sublist]