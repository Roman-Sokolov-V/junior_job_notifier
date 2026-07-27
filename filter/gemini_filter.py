from google.genai import Client
from sqlalchemy import RowMapping
from pydantic import BaseModel, Field

from common_settings import GEMINI_API_KEY


# Схема для однієї вакансії в результаті
class VacancyMatch(BaseModel):
    vacancy_id: int
    match: bool = Field(description="Does the job match the user's request")
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence in the answer from 0.0 to 1.0"
    )
    reason: str = Field(
        description="Explanation in Ukrainian why the vacancy matches or not"
    )


# Обгортка для списку результатів (Batch-схема)
class BatchFilterResponse(BaseModel):
    evaluations: list[VacancyMatch] = Field(
        description="List of ratings for each given job"
    )


def filter_vacancies_batch(
    vacancies: list[RowMapping], model: str, user_query: str | None
) -> list[dict]:
    """Фільтрує вакансії пачкою за один запит до Gemini API."""
    vacancies_list = [dict(v) for v in vacancies]
    if not user_query:
        # Якщо запиту немає, вважаємо, що всі вакансії проходять без оцінки
        return [{**v, "confidence": None, "reason": None} for v in vacancies_list]
    # 2. Відділяємо вакансії з текстом від тих, де опису немає
    valid_vacancies = []
    passed_vacancies = []
    not_passed_vacancies = []

    for v in vacancies_list:
        if v.get("description_text"):
            valid_vacancies.append(v)
        else:
            # Вакансії без опису пропускаємо
            v["confidence"] = None
            v["reason"] = "Відсутній текст опису"
            passed_vacancies.append(v)

    if not valid_vacancies:
        return passed_vacancies

    # 3. Формуємо компактний список вакансій для промпта (передаємо тільки необхідні поля)
    vacancies_payload = [
        {"id": v["id"], "description": v["description_text"]} for v in valid_vacancies
    ]

    prompt = f"""You are a filter of IT vacancies. Analyze the list of vacancies and determine
                which ones correspond to the user's request.
                USER REQUEST:
                {user_query}            
                LIST OF VACANCIES FOR EVALUATION:
                {vacancies_payload}
                """

    # 4. Виклики Gemini API (1 запит на всі вакансії)
    with Client(api_key=GEMINI_API_KEY) as client:
        interaction = client.interactions.create(
            model=model,
            input=prompt,
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": BatchFilterResponse.model_json_schema(),
            },
        )

        # 5. Автоматично парсимо відповідь у Pydantic-об'єкт
        batch_result = BatchFilterResponse.model_validate_json(interaction.output_text)

    # 6. Зводжуємо результати оцінки з вихідними вакансіями
    # Створюємо словник для швидкого пошуку оцінки за ID вакансії: {id: VacancyEvaluation}
    evaluations_by_id = {
        eval_item.vacancy_id: eval_item for eval_item in batch_result.evaluations
    }

    for v in valid_vacancies:
        eval_data = evaluations_by_id.get(v["id"])
        if eval_data:
            v["confidence"] = eval_data.confidence
            v["reason"] = eval_data.reason
            if eval_data.match:
                passed_vacancies.append(v)
            else:
                not_passed_vacancies.append(v)
    return passed_vacancies


def llm_filter_vacancies(
    vacancies: list[RowMapping], model: str, user_query: str | None
) -> list[dict]:
    """Filter vacancies based on user query."""
    if not user_query:
        # Якщо немає запиту, повертаємо всі вакансії як dict з порожнім confidence
        return [
            {**dict(v), "confidence": None, "reason": "Відсутній user_query"}
            for v in vacancies
        ]
    passed_vacancies = []
    with Client(api_key=GEMINI_API_KEY) as client:
        for raw_vacancy in vacancies:
            vacancy = dict(
                raw_vacancy
            )  # перетворюємо RowMapping в словник щоб додавати нові ключи
            description = vacancy.get("description_text")
            if not description:
                vacancy["confidence"] = None
                vacancy["reason"] = "Відсутній текст опису"
                passed_vacancies.append(vacancy)
                continue

            if not vacancy.get("description_text") or not user_query:
                # так як нема що аналізувати
                vacancy["confidence"] = None
                passed_vacancies.append(vacancy)
                continue
            input = f"""Ти — фільтр IT-вакансій. Оціни відповідність вакансії запиту користувача.
                    ЗАПИТ КОРИСТУВАЧА:
                    {user_query} 
                    ВАКАНСІЯ:
                    {description}
                    """
            interaction = client.interactions.create(
                model=model,
                input=input,
                response_format={
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": VacancyMatch.model_json_schema(),
                },
            )
            answer = VacancyMatch.model_validate_json(interaction.output_text)

            if answer.match is True:
                vacancy["confidence"] = answer.confidence
                passed_vacancies.append(vacancy)

    return passed_vacancies
