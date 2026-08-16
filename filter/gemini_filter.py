# import asyncio
# import logging
#
# from google.genai import Client
# from google.genai import types
# from supabase import AsyncClient
#
# from db.supabase_client import get_async_supabase_client
# from project_config import GEMINI_API_KEY
# from filter.schemas import BatchFilterResponse, LLMCandidate, MatchData, Profile
# from storage.crud import get_file_url, download_file_bytes
# from project_config import SUPABASE_URL
#
# logger = logging.getLogger(__name__)
#
#
# async def get_prompt_contents(
#     a_supabase: AsyncClient, vacancies_payload: list[dict], profile_data: Profile
# ) -> list:
#     if profile_data.cv_file and profile_data.mime_type:
#         if SUPABASE_URL == "http://127.0.0.1:54321":
#             file_bytes = await download_file_bytes(
#                 a_supabase=a_supabase, full_path=profile_data.cv_file
#             )
#             return [
#                 f"""You filter IT vacancies. Analyze the list of vacancies and determine,
#                 which of them correspond to the user's request and CV.
#
#                 USER REQUEST:
#                 {profile_data.query_text}
#
#                 The user's CV is provided below.""",
#                 # 💡 Передаємо байти файлу замість віддаленого URL
#                 types.Part.from_bytes(
#                     data=file_bytes,
#                     mime_type=profile_data.mime_type,
#                 ),
#                 f"""LIST OF VACANCIES FOR EVALUATION:
#                                 {vacancies_payload}""",
#             ]
#         else:
#             # Повертаємо СПИСОК із текстових блоків та об'єкта Part
#             file_uri = await get_file_url(
#                 a_supabase=a_supabase, full_path=profile_data.cv_file
#             )
#             if file_uri:
#                 return [
#                     f"""You filter IT vacancies. Analyze the list of vacancies and determine,
#                     which of them correspond to the user's request and CV.
#
#                     USER REQUEST:
#                     {profile_data.query_text}
#
#                     The user's CV is provided by the file below.""",
#                     # We pass the Part object as the OCTH element of the list!
#                     types.Part.from_uri(
#                         file_uri=file_uri,
#                         mime_type=profile_data.mime_type,
#                     ),
#                     f"""LIST OF VACANCIES FOR EVALUATION:
#                     {vacancies_payload}""",
#                 ]
#             logger.warning(
#                 "getting file_uri failed, start create prompt content without CV file-----------"
#             )
#
#     return [
#         f"""You filter IT vacancies. Analyze the list of vacancies and determine,
#         which ones correspond to the user's request.
#
#         USER REQUEST:
#         {profile_data.query_text}
#
#         LIST OF VACANCIES FOR ASSESSMENT:
#         {vacancies_payload}"""
#     ]
#
#
#
# async def get_response(gemini_client: Client, model: str, contents):
#     return await gemini_client.models.generate_content(
#         model=model,
#         contents=contents,
#         config=types.GenerateContentConfig(
#             response_mime_type="application/json",
#             response_schema=BatchFilterResponse,
#         ),
#     )
#
#
# async def get_matches_for_profile(
#     gemini_client: Client, a_supabase: AsyncClient, data: LLMCandidate, model: str
# ) -> list[MatchData]:
#     """Один запит до Gemini для одного профілю."""
#     vacancies_payload = [
#         {"id": v["id"], "description": v["description_text"]} for v in data.vacancies
#     ]
#     semantic_scores = {v["id"]: v.get("semantic_score") for v in data.vacancies}
#
#     contents = await get_prompt_contents(
#         a_supabase=a_supabase,
#         profile_data=data.profile_data,
#         vacancies_payload=vacancies_payload,
#     )
#
#     try:
#         response = await get_response(
#             gemini_client=gemini_client, model=model, contents=contents
#         )
#
#     except Exception:
#         logger.exception("Gemini filter failed for profile_id=%s", data.profile_data.id)
#         return []
#
#     # парсимо відповідь у Pydantic-об'єкт
#     batch_result: BatchFilterResponse = response.parsed
#
#     match_list = [
#         MatchData(
#             user_id=data.profile_data.user_id,
#             profile_id=data.profile_data.id,
#             vacancy_id=eval_item.vacancy_id,
#             semantic_score=semantic_scores.get(eval_item.vacancy_id, None),
#             confidence=eval_item.confidence,
#             reason=eval_item.reason,
#         )
#         for eval_item in batch_result.evaluations
#         if eval_item.match
#     ]
#     if not match_list:
#         not_match_list = [
#             MatchData(
#                 user_id=data.profile_data.user_id,
#                 profile_id=data.profile_data.id,
#                 vacancy_id=eval_item.vacancy_id,
#                 semantic_score=semantic_scores.get(eval_item.vacancy_id, None),
#                 confidence=eval_item.confidence,
#                 reason=eval_item.reason,
#             )
#             for eval_item in batch_result.evaluations
#         ]
#         best_not_matched = sorted(
#             not_match_list, key=lambda item: item.confidence, reverse=True
#         )
#         print(best_not_matched[:5])
#     return match_list
#
#
# # async def get_matches_list_for_all_profiles(
# #     list_data: list[LLMCandidate],
# #     model: str,
# # ) -> list[MatchData]:
# #     a_supabase = await get_async_supabase_client()
# #     async with Client(api_key=GEMINI_API_KEY).aio as gemini_client:
# #         coroutines = [
# #             get_matches_for_profile(
# #                 gemini_client=gemini_client,
# #                 a_supabase=a_supabase,
# #                 data=data,
# #                 model=model,
# #             )
# #             for data in list_data
# #         ]
# #         gathered = await asyncio.gather(*coroutines, return_exceptions=False)
# #
# #     return [match for sublist in gathered for match in sublist]
#
# SEMAPHORE = asyncio.Semaphore(1) # Обмежуємо кількість одночасних запитів до Gemini
#
#
# async def get_matches_list_for_all_profiles(
#         list_data: list[LLMCandidate],
#         model: str,
# ) -> list[MatchData]:
#     a_supabase = await get_async_supabase_client()
#
#     async with Client(api_key=GEMINI_API_KEY).aio as gemini_client:
#         # Внутрішня функція-обгортка, яка застосовує семафор до кожного запиту
#         async def fetch_with_semaphore(data: LLMCandidate):
#             async with SEMAPHORE:
#                 await asyncio.sleep(0.5)  # Невелика пауза між запитами
#                 return await get_matches_for_profile(
#                     gemini_client=gemini_client,
#                     a_supabase=a_supabase,
#                     data=data,
#                     model=model,
#                 )
#
#         coroutines = [fetch_with_semaphore(data) for data in list_data]
#         gathered = await asyncio.gather(*coroutines, return_exceptions=False)
#
#     return [match for sublist in gathered for match in sublist]


import asyncio
import logging
import time

from google.genai import Client
from google.genai import types
from google.genai.errors import APIError, ClientError
from supabase import AsyncClient

from db.supabase_client import get_async_supabase_client
from filter.schemas import BatchFilterResponse, LLMCandidate, MatchData, Profile
from project_config import GEMINI_API_KEY, SUPABASE_URL
from storage.crud import download_file_bytes, get_file_url

logger = logging.getLogger(__name__)

SEMAPHORE = asyncio.Semaphore(1)


async def get_prompt_contents(
        a_supabase: AsyncClient, vacancies_payload: list[dict], profile_data: Profile
) -> list:
    has_cv = bool(profile_data.cv_file and profile_data.mime_type)
    logger.info(
        "Building prompt for profile_id=%s (CV file: %s)",
        profile_data.id,
        profile_data.cv_file if has_cv else "None",
    )

    if has_cv:
        if SUPABASE_URL == "http://127.0.0.1:54321":
            logger.info("Downloading local CV bytes for profile_id=%s", profile_data.id)
            file_bytes = await download_file_bytes(
                a_supabase=a_supabase, full_path=profile_data.cv_file
            )
            return [
                f"""You filter IT vacancies. Analyze the list of vacancies and determine,
                which of them correspond to the user's request and CV.

                USER REQUEST:
                {profile_data.query_text}

                The user's CV is provided below.""",
                types.Part.from_bytes(
                    data=file_bytes,
                    mime_type=profile_data.mime_type,
                ),
                f"""LIST OF VACANCIES FOR EVALUATION:
                {vacancies_payload}""",
            ]
        else:
            logger.info("Generating signed URL for CV for profile_id=%s", profile_data.id)
            file_uri = await get_file_url(
                a_supabase=a_supabase, full_path=profile_data.cv_file
            )
            if file_uri:
                logger.info("Signed URL generated successfully for profile_id=%s", profile_data.id)
                return [
                    f"""You filter IT vacancies. Analyze the list of vacancies and determine,
                    which of them correspond to the user's request and CV.

                    USER REQUEST:
                    {profile_data.query_text}

                    The user's CV is provided by the file below.""",
                    types.Part.from_uri(
                        file_uri=file_uri,
                        mime_type=profile_data.mime_type,
                    ),
                    f"""LIST OF VACANCIES FOR EVALUATION:
                    {vacancies_payload}""",
                ]
            logger.warning(
                "Getting file_uri failed for profile_id=%s. Fallback to prompt without CV file.",
                profile_data.id,
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
    start_time = time.monotonic()
    logger.info(">>> Sending request to Gemini API (model: %s)...", model)

    response = await gemini_client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=BatchFilterResponse,
        ),
    )

    elapsed = time.monotonic() - start_time
    logger.info("<<< Gemini response received in %.2f seconds.", elapsed)
    return response


async def get_matches_for_profile(
        gemini_client: Client, a_supabase: AsyncClient, data: LLMCandidate, model: str
) -> list[MatchData]:
    """Один запит до Gemini для одного профілю."""
    vacancies_count = len(data.vacancies)
    logger.info(
        "Processing profile_id=%s (User ID: %s) with %d vacancies",
        data.profile_data.id,
        data.profile_data.user_id,
        vacancies_count,
    )

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
    except APIError as exc:
        code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
        message = getattr(exc, "message", str(exc))
        logger.error(
            "Gemini APIError for profile_id=%s: status_code=%s, message=%s",
            data.profile_data.id,
            code if code is not None else "N/A",
            message,
        )
        # If this is a client-side quota/resource error, re-raise so upstream (e.g., matching.filter_vacancies)
        # can handle it (retry/abort). Matches errors like: google.genai.errors.ClientError: 429 RESOURCE_EXHAUSTED
        if isinstance(exc, ClientError) or str(code) == "429" or (isinstance(message, str) and "RESOURCE_EXHAUSTED" in message.upper()):
            logger.error(
                "Gemini APIError is a client quota/resource error (profile_id=%s); re-raising to be handled upstream",
                data.profile_data.id,
            )
            raise
        return []
    except Exception:
        logger.exception("Unexpected failure in Gemini filter for profile_id=%s", data.profile_data.id)
        return []

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

    logger.info(
        "Finished profile_id=%s: found %d matches out of %d evaluated",
        data.profile_data.id,
        len(match_list),
        len(batch_result.evaluations) if batch_result else 0,
    )

    if not match_list and batch_result:
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
        logger.info(
            "Top 5 highest confidence non-matches for profile_id=%s: %s",
            data.profile_data.id,
            best_not_matched[:5],
        )

    return match_list


async def get_matches_list_for_all_profiles(
        list_data: list[LLMCandidate],
        model: str,
) -> list[MatchData]:
    profiles_count = len(list_data)
    logger.info("=== Starting batch filtering for %d profile(s) ===", profiles_count)

    if profiles_count == 0:
        logger.info("No candidates to process. Exiting.")
        return []

    a_supabase = await get_async_supabase_client()

    async with Client(api_key=GEMINI_API_KEY).aio as gemini_client:
        async def fetch_with_semaphore(index: int, data: LLMCandidate):
            async with SEMAPHORE:
                logger.info(
                    "[%d/%d] Acquired semaphore for profile_id=%s",
                    index + 1,
                    profiles_count,
                    data.profile_data.id,
                )
                res = await get_matches_for_profile(
                    gemini_client=gemini_client,
                    a_supabase=a_supabase,
                    data=data,
                    model=model,
                )
                # Затримуємося на 2 секунди ПІСЛЯ запиту, щоб дотримуватися RPM
                await asyncio.sleep(2.0)
                return res

        coroutines = [
            fetch_with_semaphore(idx, data) for idx, data in enumerate(list_data)
        ]
        gathered = await asyncio.gather(*coroutines, return_exceptions=False)

    total_matches = [match for sublist in gathered for match in sublist]
    logger.info("=== Batch filtering complete. Total matches found: %d ===", len(total_matches))
    return total_matches